"""Top-tier conference (ICLR/NeurIPS) reviewer panel with rubric scoring and hard floor gates."""
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal

from research.artifacts import save_json


@dataclass
class ReviewerReport:
    reviewer_id: str
    persona: str  # 'theorist' | 'empiricist' | 'practitioner'
    soundness: float           # 1.0 - 10.0
    novelty: float             # 1.0 - 10.0
    significance: float        # 1.0 - 10.0
    empirical: float           # 1.0 - 10.0
    overall: float             # 1.0 - 10.0
    confidence: int            # 1 - 5
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    questions: List[str]
    flags: List[str] = field(default_factory=list)


@dataclass
class MetaReviewDecision:
    decision: Literal['accept', 'revise', 'stop']
    recommendation: str  # 'Strong Accept' | 'Weak Accept' | 'Borderline' | 'Weak Reject' | 'Strong Reject'
    overall_score: float
    scores: Dict[str, float]
    hard_floors_triggered: List[str]
    issues: List[str]
    meta_review: str
    panel_reports: List[Dict]
    target: Optional[str] = None


# Hard thresholds calibrated to top-tier machine learning conferences (ICLR / NeurIPS)
HARD_FLOORS = {
    'novelty': 5.0,
    'significance': 5.0,
    'soundness': 5.0,
    'overall': 6.0,
}


class ConferenceReviewPanel:
    """Simulates an ICLR/NeurIPS peer review panel with Area Chair adjudication."""

    @staticmethod
    def adjudicate(reports: List[ReviewerReport]) -> MetaReviewDecision:
        if not reports:
            raise ValueError("Review panel requires at least one reviewer report")

        n = len(reports)
        mean_soundness = sum(r.soundness for r in reports) / n
        mean_novelty = sum(r.novelty for r in reports) / n
        mean_significance = sum(r.significance for r in reports) / n
        mean_empirical = sum(r.empirical for r in reports) / n
        mean_overall = sum(r.overall for r in reports) / n

        scores = {
            'soundness': round(mean_soundness, 2),
            'novelty': round(mean_novelty, 2),
            'significance': round(mean_significance, 2),
            'empirical': round(mean_empirical, 2),
            'overall': round(mean_overall, 2),
        }

        # Check hard floor gates
        hard_floors = []
        if mean_novelty < HARD_FLOORS['novelty']:
            hard_floors.append(
                f"Hard Floor: Novelty {mean_novelty:.2f} < {HARD_FLOORS['novelty']} "
                "(Incremental adaptation or reuse of known algebra without conceptual leap)"
            )
        if mean_significance < HARD_FLOORS['significance']:
            hard_floors.append(
                f"Hard Floor: Significance {mean_significance:.2f} < {HARD_FLOORS['significance']} "
                "(Marginal practical gains or easily superseded by simple out-of-pool models)"
            )
        if mean_soundness < HARD_FLOORS['soundness']:
            hard_floors.append(
                f"Hard Floor: Soundness {mean_soundness:.2f} < {HARD_FLOORS['soundness']} "
                "(Critical methodological flaw or lack of supporting evidence)"
            )
        if mean_overall < HARD_FLOORS['overall']:
            hard_floors.append(
                f"Hard Floor: Overall Score {mean_overall:.2f} < {HARD_FLOORS['overall']} "
                "(Below acceptance bar for top-tier conference)"
            )

        # Aggregate issues from all weaknesses and flags
        all_issues = []
        for r in reports:
            for w in r.weaknesses:
                if w not in all_issues:
                    all_issues.append(f"[{r.reviewer_id}]: {w}")
            for fl in r.flags:
                if fl not in all_issues:
                    all_issues.append(f"[FLAG {r.reviewer_id}]: {fl}")

        # Determine decision & recommendation
        if hard_floors:
            decision = 'stop'
            if mean_overall < 4.5 or mean_novelty < 4.0:
                recommendation = 'Strong Reject'
            else:
                recommendation = 'Weak Reject'
            target = None
        elif mean_overall >= 7.0:
            decision = 'accept'
            recommendation = 'Strong Accept' if mean_overall >= 8.0 else 'Accept'
            target = None
        elif mean_overall >= 6.0:
            if all_issues:
                decision = 'revise'
                recommendation = 'Weak Accept (Minor Revision)'
                target = 'writing'
            else:
                decision = 'accept'
                recommendation = 'Weak Accept'
                target = None
        else:
            decision = 'stop'
            recommendation = 'Reject'
            target = None

        meta_summary = (
            f"Meta-Review Decision: {recommendation} (Score: {mean_overall:.2f}/10.0). "
            f"Breakdown -> Soundness: {mean_soundness:.2f}, Novelty: {mean_novelty:.2f}, "
            f"Significance: {mean_significance:.2f}, Empirical: {mean_empirical:.2f}. "
        )
        if hard_floors:
            meta_summary += "Violated Hard Floors: " + "; ".join(hard_floors)
        else:
            meta_summary += "Meets or exceeds all conference minimum thresholds."

        return MetaReviewDecision(
            decision=decision,
            recommendation=recommendation,
            overall_score=round(mean_overall, 2),
            scores=scores,
            hard_floors_triggered=hard_floors,
            issues=all_issues,
            meta_review=meta_summary,
            panel_reports=[
                {
                    'reviewer_id': r.reviewer_id,
                    'persona': r.persona,
                    'overall': r.overall,
                    'novelty': r.novelty,
                    'significance': r.significance,
                    'soundness': r.soundness,
                    'empirical': r.empirical,
                    'summary': r.summary,
                    'weaknesses': r.weaknesses,
                    'strengths': r.strengths,
                    'flags': r.flags
                }
                for r in reports
            ],
            target=target
        )


async def run_conference_panel(directory: Path, material: Dict, ask) -> Dict:
    """Async orchestration of 3 specialized conference reviewers + AC metareview."""
    personas = [
        ('rev_theorist', 'theorist',
         'You are an ICLR Senior Reviewer specializing in Theoretical Depth and Novelty. '
         'Critically inspect whether the mathematical identity is truly novel or re-applied from prior literature. '
         'Score 1-10 on soundness, novelty, significance, empirical, and overall. Be uncompromising on novelty.'),
        ('rev_empiricist', 'empiricist',
         'You are a NeurIPS Senior Reviewer specializing in Baselines and Empirical Rigor. '
         'Check if the benchmark datasets are tiny toy sets (e.g. 4 small UCI sets), if out-of-pool models '
         '(e.g. GBDT/KNN/imputation) dominate in-pool selections, and if effect sizes exceed noise. Score 1-10.'),
        ('rev_practitioner', 'practitioner',
         'You are an Applied ML Conference Reviewer. '
         'Examine the realism of assumptions (e.g. MCAR vs MNAR, full validation observation). '
         'Evaluate if practical practitioners would use this method or if gains are negligible. Score 1-10.')
    ]

    reports = []
    for rev_id, role, prompt_prefix in personas:
        prompt = (
            f"{prompt_prefix}\n"
            "Analyze the provided manuscript and evidence. Return ONLY valid JSON with keys: "
            "soundness (float 1-10), novelty (float 1-10), significance (float 1-10), empirical (float 1-10), "
            "overall (float 1-10), confidence (int 1-5), summary (str), strengths (list[str]), weaknesses (list[str]), "
            "questions (list[str]), flags (list[str]). Under 1200 tokens."
        )
        response = await ask(prompt, material, f'review/conference/{rev_id}')
        report = ReviewerReport(
            reviewer_id=rev_id,
            persona=role,
            soundness=float(response.get('soundness', 5.0)),
            novelty=float(response.get('novelty', 5.0)),
            significance=float(response.get('significance', 5.0)),
            empirical=float(response.get('empirical', 5.0)),
            overall=float(response.get('overall', 5.0)),
            confidence=int(response.get('confidence', 3)),
            summary=str(response.get('summary', '')),
            strengths=list(response.get('strengths', [])),
            weaknesses=list(response.get('weaknesses', [])),
            questions=list(response.get('questions', [])),
            flags=list(response.get('flags', []))
        )
        reports.append(report)

    meta = ConferenceReviewPanel.adjudicate(reports)

    output = {
        'decision': meta.decision,
        'recommendation': meta.recommendation,
        'overall_score': meta.overall_score,
        'scores': meta.scores,
        'hard_floors_triggered': meta.hard_floors_triggered,
        'issues': meta.issues,
        'meta_review': meta.meta_review,
        'panel_reports': meta.panel_reports,
        'target': meta.target
    }

    save_path = directory / 'conference_review.json'
    save_json(save_path, output)
    return output
