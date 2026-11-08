import unittest
import tempfile
from pathlib import Path

from research.workflow import (
    TopicCandidate, TopicTournament, AutonomousResearchOrchestrator,
    Registry, StageResult
)
from research.workflow.priors import NegativePriors


class TestTournamentAndOrchestrator(unittest.TestCase):

    def test_tournament_evaluates_pool_and_orders_alternatives(self):
        c1 = TopicCandidate(
            id="c1_trivial",
            title="Trivial dropout paper",
            hypothesis="Existing dropout algebra works on 3 small datasets",
            theoretical_delta="none, re-apply only",
            prior_work_comparison=[],
            baseline_risk="GBDT beats it",
            feasibility_score=4.5,
            novelty_score=2.0,
            significance_score=2.0
        )
        c2 = TopicCandidate(
            id="c2_strong",
            title="Covariance-Bounded Selection under Dependent Mask Shift",
            hypothesis="Bounding pairwise mask covariances produces non-vacuous risk curves",
            theoretical_delta="Derives generalized covariance bounds beyond scalar MCAR",
            prior_work_comparison=[{"reference": "Wager2013", "difference": "Dependent mask bounds"}],
            baseline_risk="Competitive with non-linear models under correlated shift",
            feasibility_score=4.0,
            novelty_score=4.5,
            significance_score=4.2
        )
        c3 = TopicCandidate(
            id="c3_moderate",
            title="Heterogeneous Rate Multivariance Risk Estimation",
            hypothesis="Feature-wise rates yield solvable multivariate quadratic envelopes",
            theoretical_delta="Extends scalar p to feature vector p_j with unconstrained bounds",
            prior_work_comparison=[{"reference": "Zhou2023", "difference": "Multivariate rate bounds"}],
            baseline_risk="Moderate risk vs neural nets",
            feasibility_score=4.2,
            novelty_score=3.8,
            significance_score=3.6
        )

        tournament = TopicTournament.evaluate_pool([c1, c2, c3])
        self.assertTrue(tournament.admitted)
        self.assertEqual(tournament.winner.id, "c2_strong")
        self.assertEqual(len(tournament.alternatives), 1)
        self.assertEqual(tournament.alternatives[0].id, "c3_moderate")
        self.assertEqual(len(tournament.rejected), 1)
        self.assertEqual(tournament.rejected[0].id, "c1_trivial")

    def test_orchestrator_auto_fallback_upon_pilot_pruned(self):
        with tempfile.TemporaryDirectory() as d:
            base_dir = Path(d)

            # Candidate 1 will win tournament on paper, but fail pilot (pruned)
            # Candidate 2 will be the alternative, and pass pilot (success)
            c1_flawed = TopicCandidate(
                id="c1_flawed",
                title="Linear Selection under MCAR",
                hypothesis="MCAR affine predictor selection",
                theoretical_delta="Applies existing formulas to select linear models",
                prior_work_comparison=[{"reference": "Wager2013", "difference": "Applies to linear model"}],
                baseline_risk="GBDT is tested",
                feasibility_score=4.5,
                novelty_score=4.8,
                significance_score=4.8
            )
            c2_sound = TopicCandidate(
                id="c2_sound",
                title="Covariance-Bounded Selection under Correlated Masks",
                hypothesis="Pairwise covariance bounds maintain positive gain under shift",
                theoretical_delta="Novel closed-form bound for correlated dropout masks",
                prior_work_comparison=[{"reference": "Wager2013", "difference": "Dependent covariance matrix"}],
                baseline_risk="Robust vs GBDT under shift",
                feasibility_score=4.0,
                novelty_score=4.5,
                significance_score=4.2
            )

            priors = NegativePriors(base_dir / "priors.json")

            def make_registry(project_dir, candidate):
                r = Registry()
                r.stage('literature', lambda c: StageResult({
                    'sources': [{'id': 's1', 'title': 'P1', 'url': 'http://example.org', 'reading_scope': 'all'}],
                    'comparison': 'comp', 'limitations': []
                }))
                r.stage('question', lambda c: StageResult({
                    'question': 'Q?', 'hypothesis': candidate.hypothesis, 'source_ids': ['s1'], 'falsification': 'F'
                }))
                r.stage('design', lambda c: StageResult({
                    'dataset': 'D', 'split': {'train': 1}, 'methods': ['m1'], 'metrics': ['mse'],
                    'budget': {}, 'acceptance': 'mse < 0.5'
                }))
                r.stage('implementation', lambda c: StageResult({
                    'adapter': 'a1', 'version': '1', 'capabilities': ['test']
                }))

                if candidate.id == "c1_flawed":
                    # Pilot fails and triggers NO-GO
                    r.stage('pilot', lambda c: StageResult({
                        'passed': False,
                        'decision': 'no_go',
                        'reason': 'Dominated by HistGradientBoosting',
                        'diagnostics': {'scope': 'flawed_probe'}
                    }))
                else:
                    # Pilot passes with GO
                    r.stage('pilot', lambda c: StageResult({
                        'passed': True,
                        'decision': 'go',
                        'reason': 'Gain meets threshold; beats baselines',
                        'diagnostics': {'scope': 'sound_probe'}
                    }))
                return r

            orch = AutonomousResearchOrchestrator(
                base_dir,
                candidates=[c2_sound, c1_flawed],
                registry_factory=make_registry,
                priors=priors,
                max_fallbacks=2
            )

            # Let's artificially force c1_flawed as first candidate to test fallback
            orch.candidates = [c1_flawed, c2_sound]

            import asyncio
            result = asyncio.run(orch.run(until='pilot'))

            # Must have executed 2 attempts: first pruned, second succeeded!
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['active_candidate'], 'c2_sound')
            self.assertEqual(result['attempts'], 2)
            self.assertEqual(result['history'][0]['status'], 'pruned')
            self.assertEqual(result['history'][1]['status'], 'ready')

            # Verify that candidate 1's failure was recorded into negative priors automatically
            prior_ids = [p.id for p in priors.priors]
            self.assertIn("prior_pruned_c1_flawed", prior_ids)


if __name__ == '__main__':
    unittest.main()
