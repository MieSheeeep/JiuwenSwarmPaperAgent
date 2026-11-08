import unittest
from research.workflow.conference_review import (
    ConferenceReviewPanel, ReviewerReport, HARD_FLOORS
)


class TestConferenceReview(unittest.TestCase):

    def test_strong_accept_on_high_scoring_panel(self):
        reports = [
            ReviewerReport(
                reviewer_id="rev1", persona="theorist",
                soundness=8.5, novelty=8.0, significance=8.0, empirical=8.0, overall=8.2,
                confidence=4, summary="Solid theoretical derivation.",
                strengths=["Novel bound"], weaknesses=[], questions=[]
            ),
            ReviewerReport(
                reviewer_id="rev2", persona="empiricist",
                soundness=8.0, novelty=7.5, significance=8.0, empirical=8.5, overall=8.0,
                confidence=5, summary="Extensive benchmarks across 12 datasets.",
                strengths=["Strong baselines"], weaknesses=[], questions=[]
            ),
            ReviewerReport(
                reviewer_id="rev3", persona="practitioner",
                soundness=8.0, novelty=7.5, significance=7.5, empirical=8.0, overall=7.8,
                confidence=4, summary="Practical utility demonstrated in production setting.",
                strengths=["Clear application"], weaknesses=[], questions=[]
            )
        ]
        meta = ConferenceReviewPanel.adjudicate(reports)
        self.assertEqual(meta.decision, 'accept')
        self.assertIn("Accept", meta.recommendation)
        self.assertGreaterEqual(meta.overall_score, 8.0)
        self.assertEqual(len(meta.hard_floors_triggered), 0)

    def test_hard_floor_reject_on_insufficient_novelty(self):
        # Even if soundness is 9.5 (flawless execution and zero bugs), low novelty triggers hard floor
        reports = [
            ReviewerReport(
                reviewer_id="rev1", persona="theorist",
                soundness=9.5, novelty=3.5, significance=4.5, empirical=7.0, overall=4.5,
                confidence=5, summary="Re-derives standard dropout loss without new insights.",
                strengths=["Technically correct", "Reproducible"],
                weaknesses=["Trivial application of standard textbook formula"],
                questions=[]
            ),
            ReviewerReport(
                reviewer_id="rev2", persona="empiricist",
                soundness=9.0, novelty=4.0, significance=4.0, empirical=6.5, overall=4.8,
                confidence=4, summary="Small gains over naive baseline, none over non-linear models.",
                strengths=["Fair comparisons"],
                weaknesses=["Limited novelty"],
                questions=[]
            )
        ]
        meta = ConferenceReviewPanel.adjudicate(reports)
        self.assertEqual(meta.decision, 'stop')
        self.assertIn("Reject", meta.recommendation)
        self.assertTrue(any("Novelty" in hf for hf in meta.hard_floors_triggered))

    def test_regression_benchmark_against_missingness_4_4_review(self):
        """Regression test verifying that the 4.4 Missingness paper profile triggers
        rejection on both Novelty and Significance hard floors, exactly mirroring paperreview.ai."""
        reports = [
            ReviewerReport(
                reviewer_id="rev_theorist", persona="theorist",
                soundness=8.0, novelty=4.0, significance=4.2, empirical=4.5, overall=4.4,
                confidence=4, summary="Expected loss algebra re-purposed for model selection; standard identities.",
                strengths=["Mathematically sound", "Transparent assumptions"],
                weaknesses=["Identity is known from Wager et al. (2013)", "Narrow linear predictor class"],
                questions=["Can this be generalized to heterogeneous missingness?"]
            ),
            ReviewerReport(
                reviewer_id="rev_empiricist", persona="empiricist",
                soundness=7.8, novelty=4.2, significance=4.0, empirical=4.2, overall=4.3,
                confidence=5, summary="Four small UCI datasets, small gains, out-of-pool models dominate.",
                strengths=["Paired testing controls", "Honest negative results"],
                weaknesses=["Out-of-pool non-linear models crush candidate pool", "Fixed training missingness rate"],
                questions=["Why fix train rate to 0.1?"]
            ),
            ReviewerReport(
                reviewer_id="rev_practitioner", persona="practitioner",
                soundness=7.5, novelty=4.0, significance=4.2, empirical=4.5, overall=4.5,
                confidence=4, summary="Only applicable under strict MCAR; gains vanish under realistic shift.",
                strengths=["Low computational cost"],
                weaknesses=["Strict MCAR assumption rarely holds", "Requires fully observed validation rows"],
                questions=[]
            )
        ]
        meta = ConferenceReviewPanel.adjudicate(reports)

        self.assertEqual(meta.decision, 'stop')
        self.assertIn("Reject", meta.recommendation)
        self.assertAlmostEqual(meta.overall_score, 4.4, delta=0.1)

        # Both novelty and significance must be flagged as hard floor violations
        floors = " ".join(meta.hard_floors_triggered)
        self.assertIn("Novelty", floors)
        self.assertIn("Significance", floors)

    def test_borderline_paper_routes_to_revision(self):
        reports = [
            ReviewerReport(
                reviewer_id="rev1", persona="theorist",
                soundness=6.5, novelty=6.2, significance=6.0, empirical=6.0, overall=6.2,
                confidence=3, summary="Promising idea but explanation in Section 3 is unclear.",
                strengths=["Solid initial results"], weaknesses=["Section 3 needs rewrite"], questions=[]
            ),
            ReviewerReport(
                reviewer_id="rev2", persona="empiricist",
                soundness=6.5, novelty=6.0, significance=6.2, empirical=6.5, overall=6.3,
                confidence=4, summary="Acceptable baselines, need clearer error bars in Figure 2.",
                strengths=["Clear setup"], weaknesses=["Figure 2 error bars missing"], questions=[]
            )
        ]
        meta = ConferenceReviewPanel.adjudicate(reports)
        self.assertEqual(meta.decision, 'revise')
        self.assertEqual(meta.target, 'writing')
        self.assertIn("Section 3 needs rewrite", " ".join(meta.issues))


if __name__ == '__main__':
    unittest.main()
