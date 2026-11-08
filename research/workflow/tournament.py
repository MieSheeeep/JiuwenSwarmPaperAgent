"""Topic candidate generation, tournament evaluation, and auto-fallback orchestration."""
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

from .gates import TopicGate, TopicCandidate, TopicAdmissionResult, PilotGate, PilotDecision
from .engine import Workflow, StageResult


@dataclass
class TournamentResult:
    admitted: bool
    winner: Optional[TopicCandidate]
    alternatives: List[TopicCandidate]
    rejected: List[TopicCandidate]
    admission: TopicAdmissionResult
    summary: str


class TopicTournament:
    """Orchestrates candidate generation and multi-candidate selection tournament."""

    @staticmethod
    def evaluate_pool(candidates: List[TopicCandidate],
                      *,
                      min_novelty: float = 3.5,
                      min_significance: float = 3.0) -> TournamentResult:
        admission = TopicGate.evaluate(
            candidates,
            min_novelty=min_novelty,
            min_significance=min_significance
        )

        if not admission.admitted or not admission.selected_candidate:
            return TournamentResult(
                admitted=False,
                winner=None,
                alternatives=[],
                rejected=candidates,
                admission=admission,
                summary="All candidates rejected by TopicGate."
            )

        winner = admission.selected_candidate
        alternatives = [
            c for c in candidates
            if c.id != winner.id and c.id not in admission.rejection_reasons
        ]
        # Sort alternatives by composite score
        rank_dict = {r['candidate_id']: r['composite_score'] for r in admission.rankings}
        alternatives.sort(key=lambda c: rank_dict.get(c.id, 0), reverse=True)

        rejected = [c for c in candidates if c.id in admission.rejection_reasons]

        return TournamentResult(
            admitted=True,
            winner=winner,
            alternatives=alternatives,
            rejected=rejected,
            admission=admission,
            summary=f"Tournament selected '{winner.title}' with {len(alternatives)} qualified alternatives in reserve."
        )

    @staticmethod
    async def generate_candidates(topic_prompt: str,
                                  ask: Callable,
                                  *,
                                  count: int = 3) -> List[TopicCandidate]:
        """Uses LLM to brainstorm `count` distinct research angles with explicit theoretical deltas."""
        prompt = (
            f"You are a Senior Principal Research Scientist. Brainstorm {count} distinct, competitive research proposals "
            f"for the following theme:\n{topic_prompt}\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Each candidate must have a concrete, substantive theoretical_delta beyond standard textbook identities.\n"
            "2. Assess baseline_risk honestly: could a simple off-the-shelf model (like GBDT/KNN) beat it easily?\n"
            "3. Return ONLY a valid JSON list of objects, each with fields: "
            "id (str), title (str), hypothesis (str), theoretical_delta (str), "
            "prior_work_comparison (list of {reference: str, difference: str}), "
            "baseline_risk (str), feasibility_score (float 1-5), novelty_score (float 1-5), significance_score (float 1-5)."
        )
        response = await ask(prompt, {'theme': topic_prompt}, 'topic/tournament/generate')
        raw_list = response if isinstance(response, list) else response.get('candidates', [])

        candidates = []
        for i, item in enumerate(raw_list):
            cand = TopicCandidate(
                id=item.get('id', f'cand_{i+1}'),
                title=item.get('title', f'Proposal {i+1}'),
                hypothesis=item.get('hypothesis', ''),
                theoretical_delta=item.get('theoretical_delta', ''),
                prior_work_comparison=item.get('prior_work_comparison', []),
                baseline_risk=item.get('baseline_risk', ''),
                feasibility_score=float(item.get('feasibility_score', 3.5)),
                novelty_score=float(item.get('novelty_score', 3.5)),
                significance_score=float(item.get('significance_score', 3.5)),
                falsification_condition=item.get('falsification_condition', '')
            )
            candidates.append(cand)
        return candidates


class AutonomousResearchOrchestrator:
    """Manages the lifecycle of a research project with automatic fallback upon Pilot NO-GO pruning."""

    def __init__(self,
                 base_directory: Path,
                 candidates: List[TopicCandidate],
                 registry_factory: Callable[[Path, TopicCandidate], Any],
                 *,
                 max_fallbacks: int = 2):
        self.base_directory = Path(base_directory).resolve()
        self.candidates = list(candidates)
        self.registry_factory = registry_factory
        self.max_fallbacks = max_fallbacks
        self.history: List[Dict] = []

    async def run(self, *, until: Optional[str] = None) -> Dict:
        """Runs the research pipeline with automated fallback if PilotGate triggers pruning."""
        # 1. Run Tournament to rank candidates
        tournament = TopicTournament.evaluate_pool(self.candidates)
        if not tournament.admitted or not tournament.winner:
            return {
                'status': 'tournament_failed',
                'summary': tournament.summary,
                'rejected_reasons': tournament.admission.rejection_reasons
            }

        queue = [tournament.winner] + tournament.alternatives
        attempts = 0

        while queue and attempts <= self.max_fallbacks:
            active_candidate = queue.pop(0)
            attempts += 1
            project_dir = self.base_directory / f"attempt_{attempts}_{active_candidate.id}"
            project_dir.mkdir(parents=True, exist_ok=True)

            # Create workflow
            constraints = {
                'candidate_id': active_candidate.id,
                'theoretical_delta': active_candidate.theoretical_delta,
                'baseline_risk': active_candidate.baseline_risk
            }
            w = Workflow.create(project_dir, active_candidate.title, constraints=constraints)

            # Build registry for active candidate
            registry = self.registry_factory(project_dir, active_candidate)

            # Run workflow
            status = await w.run(registry, until=until)

            record = {
                'attempt': attempts,
                'candidate_id': active_candidate.id,
                'candidate_title': active_candidate.title,
                'status': status['status'],
                'next_stage': status.get('next_stage'),
                'project_dir': str(project_dir)
            }

            if status['status'] == 'pruned':
                # PilotGate triggered NO-GO!
                pilot_art = w.artifact('pilot')['payload']
                reason = pilot_art.get('reason', 'Pilot NO-GO')
                record['pruning_reason'] = reason
                self.history.append(record)

                if queue and attempts <= self.max_fallbacks:
                    # Fallback to next candidate in queue!
                    continue
                else:
                    return {
                        'status': 'all_candidates_pruned',
                        'attempts': attempts,
                        'history': self.history,
                        'last_pruning_reason': reason
                    }

            # If not pruned, workflow succeeded through requested stages
            self.history.append(record)
            return {
                'status': 'success',
                'active_candidate': active_candidate.id,
                'workflow_status': status,
                'attempts': attempts,
                'history': self.history
            }

        return {'status': 'exhausted', 'attempts': attempts, 'history': self.history}
