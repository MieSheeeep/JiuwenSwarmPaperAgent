import unittest
from research.workflow.deep_revision import DeepRevisionManager, RevisionPlan


class TestDeepRevision(unittest.TestCase):

    def test_textual_issues_route_to_writing(self):
        issues = [
            "Section 2 related work misses citations to Zhou et al. (2023)",
            "The tone in Introduction overclaims general robustness"
        ]
        plan = DeepRevisionManager.plan_revision(issues, {'empirical': 7.0, 'soundness': 7.0})
        self.assertEqual(plan.target_stage, 'writing')
        self.assertFalse(plan.requires_new_experiment)
        self.assertEqual(len(plan.textual_repairs), 2)

    def test_experimental_gaps_route_to_experiment(self):
        issues = [
            "Why fix train missingness rate at 0.1? Need evaluation across rates [0.3, 0.5]",
            "Missing non-linear baseline comparison; HistGradientBoosting must be included",
            "Typo in abstract"
        ]
        plan = DeepRevisionManager.plan_revision(issues, {'empirical': 4.5, 'soundness': 6.0})
        self.assertEqual(plan.target_stage, 'experiment')
        self.assertTrue(plan.requires_new_experiment)
        self.assertGreaterEqual(len(plan.experimental_repairs), 2)

    def test_apply_experiment_extension_merges_rows(self):
        existing = [
            {'dataset': 'yacht', 'split_seed': 101, 'condition': 'clean', 'method': 'affine', 'mse': 0.35},
            {'dataset': 'yacht', 'split_seed': 101, 'condition': 'mcar_0.1', 'method': 'affine', 'mse': 0.38}
        ]
        supplementary = [
            # Update/override existing
            {'dataset': 'yacht', 'split_seed': 101, 'condition': 'mcar_0.1', 'method': 'affine', 'mse': 0.375},
            # Add new condition (rate 0.3)
            {'dataset': 'yacht', 'split_seed': 101, 'condition': 'mcar_0.3', 'method': 'affine', 'mse': 0.42},
            # Add new baseline (HistGradientBoosting)
            {'dataset': 'yacht', 'split_seed': 101, 'condition': 'clean', 'method': 'native_hist', 'mse': 0.05}
        ]

        merged = DeepRevisionManager.apply_experiment_extension(existing, supplementary)
        self.assertEqual(len(merged), 4)

        # Check that existing was updated
        mcar1 = next(r for r in merged if r['condition'] == 'mcar_0.1' and r['method'] == 'affine')
        self.assertEqual(mcar1['mse'], 0.375)

        # Check new rows added
        methods = {r['method'] for r in merged}
        self.assertIn('native_hist', methods)


if __name__ == '__main__':
    unittest.main()
