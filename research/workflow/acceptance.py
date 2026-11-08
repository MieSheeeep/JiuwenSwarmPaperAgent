"""Structured research acceptance criteria: pre-registers quantitative thresholds before experiments."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Literal


@dataclass
class StructuredAcceptance:
    target_metric: str = "mse"
    metric_direction: Literal["higher_is_better", "lower_is_better"] = "lower_is_better"
    min_delta: float = 0.01
    min_relative_gain: float = 0.02
    baseline_method: str = "clean"
    strong_baseline_reference: Optional[str] = "HistGradientBoosting"
    out_of_pool_domination_margin: float = 0.05
    require_ci_positive: bool = True
    allow_pivot: bool = True
    pivot_target: str = "design"
    statistical_power_min: float = 0.80
    notes: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data) -> "StructuredAcceptance":
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            # If string or non-dict passed, construct default with text notes
            return cls(notes=str(data or ""))
        known_keys = {
            "target_metric", "metric_direction", "min_delta", "min_relative_gain",
            "baseline_method", "strong_baseline_reference", "out_of_pool_domination_margin",
            "require_ci_positive", "allow_pivot", "pivot_target", "statistical_power_min", "notes"
        }
        filtered = {k: v for k, v in data.items() if k in known_keys}
        if "min_delta" in filtered:
            filtered["min_delta"] = float(filtered["min_delta"])
        if "out_of_pool_domination_margin" in filtered:
            filtered["out_of_pool_domination_margin"] = float(filtered["out_of_pool_domination_margin"])
        if "metric_direction" in filtered and filtered["metric_direction"] not in ("higher_is_better", "lower_is_better"):
            filtered["metric_direction"] = "lower_is_better"
        return cls(**filtered)

    def validate(self) -> List[str]:
        errors = []
        if self.min_delta <= 0:
            errors.append(f"min_delta must be positive, got {self.min_delta}")
        if self.out_of_pool_domination_margin <= 0:
            errors.append(f"out_of_pool_domination_margin must be positive, got {self.out_of_pool_domination_margin}")
        if self.metric_direction not in ("higher_is_better", "lower_is_better"):
            errors.append(f"Invalid metric_direction: {self.metric_direction}")
        return errors
