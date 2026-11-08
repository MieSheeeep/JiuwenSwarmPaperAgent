"""External review client (paperreview.ai) and automated feedback sync to negative priors."""
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .priors import NegativePriors, NegativePrior


@dataclass
class ExternalReviewResult:
    token: str
    venue: str
    score: Optional[float]
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    questions: List[str]
    raw_markdown: str


class ExternalReviewClient:
    """Manages paper submission to paperreview.ai and integrates feedback into NegativePriors."""

    def __init__(self, token_file: Optional[Path] = None):
        self.token_file = Path(token_file) if token_file else None

    @staticmethod
    def parse_review_markdown(text: str, token: str = "", venue: str = "ICLR") -> ExternalReviewResult:
        """Parses raw text from paperreview.ai / Stanford Agentic Reviewer into structured fields."""
        score = None
        score_match = re.search(r'(?:预计得分|score|overall score|rating)[:：\s]*([0-9]+(?:\.[0-9]+)?)\s*/\s*10', text, re.IGNORECASE)
        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                score = None

        strengths = []
        weaknesses = []
        questions = []
        summary = ""

        # Extract sections if present
        summary_match = re.search(r'(?:摘要|summary)[:：\s]*(.*?)(?=(?:优势|strengths|弱点|weaknesses|实验评估|$))', text, re.IGNORECASE | re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()

        weaknesses_match = re.search(r'(?:弱点|weaknesses|局限|limitations|不足)[:：\s]*(.*?)(?=(?:作者提问|questions|总体评估|overall|$))', text, re.IGNORECASE | re.DOTALL)
        if weaknesses_match:
            lines = [l.strip('- *#') for l in weaknesses_match.group(1).splitlines() if l.strip()]
            weaknesses = [l for l in lines if len(l) > 10][:5]

        questions_match = re.search(r'(?:作者提问|questions|issues)[:：\s]*(.*?)(?=(?:总体评估|overall|$))', text, re.IGNORECASE | re.DOTALL)
        if questions_match:
            lines = [l.strip('- *#') for l in questions_match.group(1).splitlines() if l.strip()]
            questions = [l for l in lines if len(l) > 10][:5]

        return ExternalReviewResult(
            token=token,
            venue=venue,
            score=score,
            summary=summary[:600],
            strengths=strengths,
            weaknesses=weaknesses,
            questions=questions,
            raw_markdown=text
        )

    @staticmethod
    def sync_to_priors(review: ExternalReviewResult, priors: NegativePriors, topic_title: str) -> Optional[NegativePrior]:
        """If review score is below top-tier bar (< 6.0), extract failure features into NegativePriors."""
        if review.score is not None and review.score >= 6.0:
            # Paper met conference standard, not a negative prior
            return None

        failure_text = "; ".join(review.weaknesses) if review.weaknesses else (review.summary or "Sub-threshold score")
        prior_id = f"prior_external_{re.sub(r'[^a-zA-Z0-9]', '_', topic_title)[:30].lower()}"

        avoidance = (
            f"External review rejected with score {review.score or 'low'}/10. "
            f"Avoid: {failure_text[:200]}"
        )

        priors.record_failure(
            prior_id=prior_id,
            pattern=f"{topic_title}",
            source=f"paperreview.ai ({review.venue} score: {review.score or 'N/A'}/10)",
            failure_mode=failure_text[:300],
            avoidance_rule=avoidance,
            keywords=[w for w in re.split(r'\W+', topic_title.lower()) if len(w) > 4][:5]
        )
        return priors.priors[-1]
