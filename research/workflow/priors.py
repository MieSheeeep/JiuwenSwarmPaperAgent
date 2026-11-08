"""Negative prior knowledge base: records failure patterns and prunes duplicate dead-ends."""
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class NegativePrior:
    id: str
    pattern: str
    rejection_source: str
    failure_mode: str
    avoidance_rule: str
    keywords: List[str] = field(default_factory=list)


DEFAULT_PRIORS = [
    NegativePrior(
        id="prior_dropout_mcar_linear_selection",
        pattern="Applying known dropout / expected loss identities to select linear predictors under scalar MCAR missingness.",
        rejection_source="paperreview.ai external ICLR calibration (Score: 4.4/10)",
        failure_mode="Core identity is standard (Wager et al., 2013); in-pool linear model gains are marginal and completely superseded by simple out-of-pool models (GBDT/KNN); toy UCI benchmark (4 datasets) lacks empirical scale.",
        avoidance_rule="Do not propose linear model selection under scalar MCAR without methodological extensions (e.g., heterogeneous rates, dependent mask covariances) and without benchmarking against strong non-linear baselines.",
        keywords=["expected loss algebra", "dropout identity", "mcar linear predictor", "mask-integrated validation", "uci yacht housing"]
    )
]


class NegativePriors:
    """Manages negative research priors to prevent workflows from repeating flawed topics."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = Path(file_path) if file_path else None
        self.priors: List[NegativePrior] = list(DEFAULT_PRIORS)
        if self.file_path and self.file_path.exists():
            self.load()

    def load(self):
        try:
            data = json.loads(self.file_path.read_text(encoding='utf-8'))
            loaded = [NegativePrior(**item) for item in data]
            # Merge without duplicates
            existing_ids = {p.id for p in self.priors}
            for item in loaded:
                if item.id not in existing_ids:
                    self.priors.append(item)
                    existing_ids.add(item.id)
        except Exception:
            pass

    def save(self):
        if not self.file_path:
            return
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                'id': p.id,
                'pattern': p.pattern,
                'rejection_source': p.rejection_source,
                'failure_mode': p.failure_mode,
                'avoidance_rule': p.avoidance_rule,
                'keywords': p.keywords
            }
            for p in self.priors
        ]
        self.file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def record_failure(self, prior_id: str, pattern: str, source: str, failure_mode: str, avoidance_rule: str, keywords: Optional[List[str]] = None):
        prior = NegativePrior(
            id=prior_id,
            pattern=pattern,
            rejection_source=source,
            failure_mode=failure_mode,
            avoidance_rule=avoidance_rule,
            keywords=keywords or []
        )
        self.priors = [p for p in self.priors if p.id != prior_id] + [prior]
        self.save()

    def check_candidate(self, candidate_text: str) -> List[NegativePrior]:
        """Returns matching negative priors if candidate text hits multiple key patterns."""
        text = candidate_text.lower()
        matched = []
        for p in self.priors:
            hits = sum(1 for kw in p.keywords if kw.lower() in text)
            if hits >= 2 or any(len(kw) > 18 and kw.lower() in text for kw in p.keywords):
                matched.append(p)
        return matched

    def prompt_guidance(self) -> str:
        """Compact instruction text to inject into Topic and Literature prompts."""
        if not self.priors:
            return ""
        lines = ["Negative Research Priors (Known dead-ends to avoid):"]
        for p in self.priors:
            lines.append(f"- Avoid: {p.pattern} -> Reason: {p.failure_mode}. Rule: {p.avoidance_rule}")
        return "\n".join(lines)
