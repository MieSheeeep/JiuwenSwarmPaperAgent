import unittest
from research.workflow.acceptance import StructuredAcceptance


class TestAcceptance(unittest.TestCase):

    def test_default_values_and_dict_conversion(self):
        acc = StructuredAcceptance()
        self.assertEqual(acc.target_metric, "mse")
        self.assertEqual(acc.metric_direction, "lower_is_better")
        self.assertEqual(acc.min_delta, 0.01)

        d = acc.to_dict()
        self.assertIn("min_delta", d)
        self.assertIn("strong_baseline_reference", d)

        restored = StructuredAcceptance.from_dict(d)
        self.assertEqual(restored.min_delta, 0.01)
        self.assertEqual(restored.baseline_method, "clean")

    def test_from_text_fallback(self):
        text_note = "Report all metrics honestly without fabricated claims"
        acc = StructuredAcceptance.from_dict(text_note)
        self.assertEqual(acc.notes, text_note)
        self.assertEqual(acc.min_delta, 0.01)

    def test_validation_errors(self):
        acc = StructuredAcceptance(min_delta=-0.05, out_of_pool_domination_margin=-0.1)
        errors = acc.validate()
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("min_delta" in e for e in errors))


if __name__ == '__main__':
    unittest.main()
