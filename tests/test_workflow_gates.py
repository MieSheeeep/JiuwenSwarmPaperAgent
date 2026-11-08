import unittest
import tempfile
from pathlib import Path

from research.workflow import Workflow, Registry, StageResult, STAGES
from research.workflow.gates import TopicGate, TopicCandidate, PilotGate, PilotDecision


class TestWorkflowGates(unittest.TestCase):

    def test_topic_gate_admission_and_ranking(self):
        c1 = TopicCandidate(
            id="c1_trivial",
            title="Apply standard dropout formula to 3 UCI datasets",
            hypothesis="Existing dropout algebra works on 3 small datasets",
            theoretical_delta="none, re-apply only",
            prior_work_comparison=[{"reference": "Wager2013", "difference": "None"}],
            baseline_risk="Outperformed by default GBDT",
            feasibility_score=4.5,
            novelty_score=2.0,
            significance_score=2.5,
        )
        c2 = TopicCandidate(
            id="c2_novel",
            title="Distributionally Robust Selection under Correlated Missingness Shift",
            hypothesis="Bounding pair-wise mask covariances provides non-vacuous risk bounds",
            theoretical_delta="Derives generalized covariance bounds beyond scalar MCAR",
            prior_work_comparison=[{"reference": "Wager2013", "difference": "Extends to non-scalar dependent masks"}],
            baseline_risk="Competitive with non-linear models under high covariance shift",
            feasibility_score=3.8,
            novelty_score=4.2,
            significance_score=4.0,
        )

        result = TopicGate.evaluate([c1, c2], min_novelty=3.5, min_significance=3.0)
        self.assertTrue(result.admitted)
        self.assertEqual(result.selected_candidate.id, "c2_novel")
        self.assertIn("c1_trivial", result.rejection_reasons)
        self.assertTrue(any("novelty" in r.lower() for r in result.rejection_reasons["c1_trivial"]))

    def test_topic_gate_all_rejected(self):
        c1 = TopicCandidate(
            id="c1_weak",
            title="Trivial paper",
            hypothesis="Hypothesis",
            theoretical_delta="none",
            prior_work_comparison=[],
            baseline_risk="dominates",
            feasibility_score=4.0,
            novelty_score=2.0,
            significance_score=2.0,
        )
        result = TopicGate.evaluate([c1], min_novelty=3.5, min_significance=3.0)
        self.assertFalse(result.admitted)
        self.assertIsNone(result.selected_candidate)
        self.assertIn("c1_weak", result.rejection_reasons)

    def test_pilot_gate_go_decision(self):
        probe = {
            'candidate_metric': 0.85,
            'baseline_metric': 0.78,
            'execution_health': True,
            'confidence_interval': [0.03, 0.11]
        }
        acceptance = {'min_delta': 0.05, 'metric_direction': 'higher_is_better', 'require_ci_positive': True}
        decision = PilotGate.evaluate(probe, acceptance)
        self.assertEqual(decision.decision, 'go')
        self.assertTrue(decision.passed)
        self.assertGreaterEqual(decision.metrics['delta'], 0.05)

    def test_pilot_gate_out_of_pool_dominance_triggers_nogo(self):
        # Candidate beats in-pool linear baseline slightly, but GBDT crushes both
        probe = {
            'candidate_metric': 0.71,
            'baseline_metric': 0.70,  # +0.01 in-pool gain
            'out_of_pool_metric': 0.88,  # +0.17 out-of-pool lead
            'out_of_pool_name': 'HistGradientBoosting',
            'execution_health': True,
        }
        acceptance = {
            'min_delta': 0.005,
            'metric_direction': 'higher_is_better',
            'out_of_pool_domination_margin': 0.05
        }
        decision = PilotGate.evaluate(probe, acceptance)
        self.assertEqual(decision.decision, 'no_go')
        self.assertFalse(decision.passed)
        self.assertIn("dominated by HistGradientBoosting", decision.reason)

    def test_pilot_gate_pivot_on_subgroup_signal(self):
        probe = {
            'candidate_metric': 0.702,
            'baseline_metric': 0.700,  # gain = 0.002 < min_delta (0.01)
            'subgroup_signals': {'high_missingness_slice': {'gain': 0.045}},
            'execution_health': True,
        }
        acceptance = {'min_delta': 0.01, 'metric_direction': 'higher_is_better'}
        decision = PilotGate.evaluate(probe, acceptance, allow_pivot=True)
        self.assertEqual(decision.decision, 'pivot')
        self.assertFalse(decision.passed)
        self.assertEqual(decision.pivot_target, 'design')

    def test_pilot_gate_failed_execution_health(self):
        probe = {
            'candidate_metric': float('nan'),
            'baseline_metric': 0.70,
            'execution_health': False
        }
        acceptance = {'min_delta': 0.01}
        decision = PilotGate.evaluate(probe, acceptance)
        self.assertEqual(decision.decision, 'failed')
        self.assertFalse(decision.passed)

    def test_workflow_engine_integrates_pilot_nogo_and_prunes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            w = Workflow.create(root, 'Test research topic')
            r = Registry()

            # Mock stages up to pilot
            r.stage('literature', lambda c: StageResult({
                'sources': [{'id': 's1', 'title': 'P1', 'url': 'http://example.org', 'reading_scope': 'all'}],
                'comparison': 'comp', 'limitations': []
            }))
            r.stage('question', lambda c: StageResult({
                'question': 'Q?', 'hypothesis': 'H', 'source_ids': ['s1'], 'falsification': 'F'
            }))
            r.stage('design', lambda c: StageResult({
                'dataset': 'D', 'split': {'train': 1}, 'methods': ['m1'], 'metrics': ['acc'],
                'budget': {}, 'acceptance': 'acc > 0.8'
            }))
            r.stage('implementation', lambda c: StageResult({
                'adapter': 'a1', 'version': '1', 'capabilities': ['test']
            }))

            # Pilot handler returns NO-GO
            def pilot_handler(c):
                decision = PilotDecision(
                    decision='no_go',
                    passed=False,
                    reason="Weak in-pool gains; out-of-pool GBDT dominates",
                    metrics={'delta': 0.001},
                    diagnostics={'scope': 'toy_eval'}
                )
                return StageResult({
                    'passed': decision.passed,
                    'decision': decision.decision,
                    'reason': decision.reason,
                    'diagnostics': decision.diagnostics,
                    'metrics': decision.metrics
                })

            r.stage('pilot', pilot_handler)

            import asyncio
            status = asyncio.run(w.run(r))

            # The workflow must be pruned, status is 'pruned', next stage halted
            self.assertEqual(status['status'], 'pruned')
            self.assertEqual(status['next_stage'], 'experiment')

            # Attempting to resume without invalidation must fail
            with self.assertRaises(ValueError):
                w.resume()

            # Event log contains pilot_pruned
            events = [e['event'] for e in w.state['events']]
            self.assertIn('pilot_pruned', events)


if __name__ == '__main__':
    unittest.main()
