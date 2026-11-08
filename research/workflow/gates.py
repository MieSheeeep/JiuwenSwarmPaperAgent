"""Topic admission gates and Pilot tri-state early pruning gates."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Literal


@dataclass
class TopicCandidate:
    id: str
    title: str
    hypothesis: str
    theoretical_delta: str
    prior_work_comparison: List[Dict[str, str]]
    baseline_risk: str
    feasibility_score: float  # 1.0 - 5.0
    novelty_score: float      # 1.0 - 5.0
    significance_score: float # 1.0 - 5.0
    falsification_condition: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class TopicAdmissionResult:
    admitted: bool
    selected_candidate: Optional[TopicCandidate]
    rankings: List[Dict]
    rejection_reasons: Dict[str, List[str]]
    admission_summary: str


class TopicGate:
    """Pre-implementation admission filter to prune trivial and incremental topics."""

    @staticmethod
    def evaluate(candidates: List[TopicCandidate],
                 *,
                 min_novelty: float = 3.5,
                 min_significance: float = 3.0,
                 min_feasibility: float = 3.0) -> TopicAdmissionResult:
        if not candidates:
            return TopicAdmissionResult(
                admitted=False,
                selected_candidate=None,
                rankings=[],
                rejection_reasons={},
                admission_summary="No topic candidates provided."
            )

        rankings = []
        rejection_reasons = {}

        for c in candidates:
            reasons = []
            # Check delta declaration
            delta_text = (c.theoretical_delta or "").strip().lower()
            if len(delta_text) < 15 or any(w in delta_text for w in ["none", "trivial", "n/a", "no change", "re-apply only"]):
                reasons.append("Insufficient theoretical delta: fails to declare substantive methodological extension.")

            # Novelty floor
            if c.novelty_score < min_novelty:
                reasons.append(f"Novelty score {c.novelty_score:.1f} < threshold {min_novelty:.1f} (trivial adaptation).")

            # Significance floor
            if c.significance_score < min_significance:
                reasons.append(f"Significance score {c.significance_score:.1f} < threshold {min_significance:.1f}.")

            # Feasibility floor
            if c.feasibility_score < min_feasibility:
                reasons.append(f"Feasibility score {c.feasibility_score:.1f} < threshold {min_feasibility:.1f}.")

            # Baseline dominance check
            baseline_risk_text = (c.baseline_risk or "").strip().lower()
            if "dominates" in baseline_risk_text or "outperformed by default" in baseline_risk_text:
                reasons.append("High baseline dominance risk: strong standard model suspected to supersede entire candidate pool.")

            composite_score = (
                0.40 * c.novelty_score +
                0.35 * c.significance_score +
                0.25 * c.feasibility_score
            )

            is_valid = (len(reasons) == 0)
            if not is_valid:
                rejection_reasons[c.id] = reasons

            rankings.append({
                'candidate_id': c.id,
                'title': c.title,
                'composite_score': round(composite_score, 3),
                'novelty': c.novelty_score,
                'significance': c.significance_score,
                'feasibility': c.feasibility_score,
                'admissible': is_valid,
                'reasons': reasons
            })

        rankings.sort(key=lambda r: (r['admissible'], r['composite_score']), reverse=True)

        admissible_candidates = [r for r in rankings if r['admissible']]
        if not admissible_candidates:
            return TopicAdmissionResult(
                admitted=False,
                selected_candidate=None,
                rankings=rankings,
                rejection_reasons=rejection_reasons,
                admission_summary="All candidates rejected by Topic Gate (did not pass novelty/significance floors)."
            )

        top_id = admissible_candidates[0]['candidate_id']
        selected = next(c for c in candidates if c.id == top_id)
        return TopicAdmissionResult(
            admitted=True,
            selected_candidate=selected,
            rankings=rankings,
            rejection_reasons=rejection_reasons,
            admission_summary=f"Selected candidate '{selected.title}' (composite score: {admissible_candidates[0]['composite_score']})."
        )


@dataclass
class PilotDecision:
    decision: Literal['go', 'pivot', 'no_go', 'failed']
    passed: bool
    reason: str
    metrics: Dict
    diagnostics: Dict
    pivot_target: Optional[str] = None


class PilotGate:
    """Evaluates pilot exploration to determine whether to GO (proceed to full experiments),
    PIVOT (adjust hypothesis scope), or NO-GO (prune project immediately to save budget)."""

    @staticmethod
    def evaluate(probe_data: Dict, acceptance: Dict, *, allow_pivot: bool = True) -> PilotDecision:
        diagnostics = dict(probe_data.get('diagnostics', {}))
        metrics = dict(probe_data.get('metrics', {}))

        # 1. Execution health check
        execution_health = probe_data.get('execution_health', True)
        if not execution_health:
            return PilotDecision(
                decision='failed',
                passed=False,
                reason="Pilot execution failed health check (NaN, infinite parameters, or runtime error).",
                metrics=metrics,
                diagnostics={'scope': 'execution_health', 'status': 'unhealthy', **diagnostics}
            )

        # 2. Metric extraction
        candidate_metric = probe_data.get('candidate_metric')
        baseline_metric = probe_data.get('baseline_metric')

        if candidate_metric is None or baseline_metric is None:
            # Fallback if metrics are missing but passed boolean is given
            passed = bool(probe_data.get('passed', False))
            return PilotDecision(
                decision='go' if passed else 'no_go',
                passed=passed,
                reason="Direct boolean pilot judgment without numeric metrics.",
                metrics=metrics,
                diagnostics=diagnostics
            )

        direction = acceptance.get('metric_direction', 'higher_is_better')
        min_delta = acceptance.get('min_delta', 0.01)

        if direction == 'higher_is_better':
            gain = candidate_metric - baseline_metric
        else:
            gain = baseline_metric - candidate_metric

        metrics.update({
            'candidate_metric': candidate_metric,
            'baseline_metric': baseline_metric,
            'delta': round(gain, 6),
            'min_delta_required': min_delta
        })

        # 3. Out-of-pool strong baseline dominance check
        out_of_pool_metric = probe_data.get('out_of_pool_metric')
        if out_of_pool_metric is not None:
            oop_name = probe_data.get('out_of_pool_name', 'out_of_pool_baseline')
            if direction == 'higher_is_better':
                oop_gap = out_of_pool_metric - candidate_metric
            else:
                oop_gap = candidate_metric - out_of_pool_metric

            metrics['out_of_pool_metric'] = out_of_pool_metric
            metrics['out_of_pool_gap'] = round(oop_gap, 6)

            # If out-of-pool easily dominates, in-pool selection is superseded
            oop_domination_margin = acceptance.get('out_of_pool_domination_margin', 0.05)
            if oop_gap >= oop_domination_margin:
                return PilotDecision(
                    decision='no_go',
                    passed=False,
                    reason=f"Candidate dominated by {oop_name} (gap: {oop_gap:.4f} >= threshold {oop_domination_margin:.4f}). Selecting inside weak pool provides negligible utility.",
                    metrics=metrics,
                    diagnostics={'scope': 'out_of_pool_check', 'dominated_by': oop_name, **diagnostics}
                )

        # 4. Confidence Interval check
        ci = probe_data.get('confidence_interval')
        if ci is not None:
            ci_low, ci_high = ci
            metrics['confidence_interval'] = [ci_low, ci_high]
            if acceptance.get('require_ci_positive', False) and ci_low <= 0:
                if allow_pivot:
                    return PilotDecision(
                        decision='pivot',
                        passed=False,
                        reason=f"Effect CI [{ci_low:.4f}, {ci_high:.4f}] crosses zero; signal indistinguishable from noise.",
                        metrics=metrics,
                        diagnostics={'scope': 'uncertainty', 'status': 'ci_crosses_zero', **diagnostics},
                        pivot_target=acceptance.get('pivot_target', 'design')
                    )
                else:
                    return PilotDecision(
                        decision='no_go',
                        passed=False,
                        reason=f"Effect CI [{ci_low:.4f}, {ci_high:.4f}] crosses zero; no statistically meaningful gain.",
                        metrics=metrics,
                        diagnostics={'scope': 'uncertainty', 'status': 'ci_crosses_zero', **diagnostics}
                    )

        # 5. Delta threshold comparison
        if gain >= min_delta:
            return PilotDecision(
                decision='go',
                passed=True,
                reason=f"Pilot passed: gain {gain:.4f} meets or exceeds required delta {min_delta:.4f}.",
                metrics=metrics,
                diagnostics={'scope': 'acceptance_check', 'status': 'passed', **diagnostics}
            )

        # 6. Below delta: Pivot vs No-Go
        subgroup_signals = probe_data.get('subgroup_signals')
        if allow_pivot and (subgroup_signals or (0 < gain < min_delta)):
            return PilotDecision(
                decision='pivot',
                passed=False,
                reason=f"Pilot overall gain {gain:.4f} below threshold {min_delta:.4f}, but positive signal/subgroup detected. Pivot recommended.",
                metrics=metrics,
                diagnostics={'scope': 'acceptance_check', 'status': 'pivot_eligible', 'subgroups': subgroup_signals, **diagnostics},
                pivot_target=acceptance.get('pivot_target', 'design')
            )

        return PilotDecision(
            decision='no_go',
            passed=False,
            reason=f"Pilot rejected (NO-GO): gain {gain:.4f} fails threshold {min_delta:.4f}. Early termination to prevent wasteful study.",
            metrics=metrics,
            diagnostics={'scope': 'acceptance_check', 'status': 'no_go', **diagnostics}
        )
