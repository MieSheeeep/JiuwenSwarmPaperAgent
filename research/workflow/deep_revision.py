"""Deep revision loop: handles reviewer-mandated experiment repairs, ablation additions, and figure updates."""
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal

from .engine import Workflow


@dataclass
class RevisionPlan:
    target_stage: Literal['writing', 'analysis', 'experiment', 'design']
    requires_new_experiment: bool
    textual_repairs: List[Dict[str, str]]
    experimental_repairs: List[Dict]
    summary: str


class DeepRevisionManager:
    """Analyzes review issues to determine whether a lightweight manuscript patch suffices
    or if reviewer critiques demand augmenting experiments, ablations, or baselines."""

    @staticmethod
    def plan_revision(issues: List[str], review_scores: Optional[Dict[str, float]] = None) -> RevisionPlan:
        textual = []
        experimental = []

        experiment_triggers = [
            ("baseline", "add_baseline", "Missing strong baselines or out-of-pool comparison"),
            ("dataset", "expand_datasets", "Limited empirical breadth; review demands additional datasets"),
            ("ablation", "add_ablation", "Review requires ablation study on hyperparameters or mechanisms"),
            ("rate", "expand_parameter_sweep", "Review asks for evaluation across wider parameter ranges"),
            ("variance", "add_seeds", "Review notes high variance or demands multi-seed uncertainty bars"),
            ("out-of-pool", "add_out_of_pool_model", "Review demands explicit head-to-head with non-linear models")
        ]

        for issue in issues:
            issue_lower = issue.lower()
            matched_exp = False
            for trigger_word, action_type, desc in experiment_triggers:
                if trigger_word in issue_lower:
                    experimental.append({
                        'action': action_type,
                        'description': desc,
                        'source_issue': issue
                    })
                    matched_exp = True
                    break
            if not matched_exp:
                textual.append({'issue': issue})

        scores = review_scores or {}
        empirical_score = scores.get('empirical', 6.0)
        soundness_score = scores.get('soundness', 6.0)

        # If empirical score is low and experimental repairs identified, route to experiment
        if experimental and (empirical_score < 6.0 or soundness_score < 6.0):
            target = 'experiment'
            requires_exp = True
            summary = f"Review demands experimental repairs ({len(experimental)} items identified). Routing to 'experiment'."
        elif experimental and not textual:
            target = 'experiment'
            requires_exp = True
            summary = f"Experimental augmentation requested: {len(experimental)} actions. Routing to 'experiment'."
        else:
            target = 'writing'
            requires_exp = False
            summary = f"Textual and framing revision sufficient ({len(textual)} issues). Routing to 'writing'."

        return RevisionPlan(
            target_stage=target,
            requires_new_experiment=requires_exp,
            textual_repairs=textual,
            experimental_repairs=experimental,
            summary=summary
        )

    @staticmethod
    def apply_experiment_extension(existing_results: List[Dict],
                                   new_rows: List[Dict],
                                   key_fields: Tuple[str, ...] = ('dataset', 'split_seed', 'condition', 'method')) -> List[Dict]:
        """Merges new experimental rows (e.g. from supplementary baselines or rates) with existing results."""
        merged = list(existing_results)
        seen_keys = {
            tuple(r.get(k) for k in key_fields): i
            for i, r in enumerate(merged)
        }

        for row in new_rows:
            k = tuple(row.get(k) for k in key_fields)
            if k in seen_keys:
                merged[seen_keys[k]] = row
            else:
                merged.append(row)
                seen_keys[k] = len(merged) - 1

        return merged
