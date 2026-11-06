import unittest


class MemoryPaperTests(unittest.TestCase):
    def test_unmeasured_numbers_and_unknown_citations_reject_model_prose(self):
        from research.memory_paper import check_prose, SECTIONS
        prose = {section: 'This controlled study tests structured source selection under fixed conditions.' for section in SECTIONS}
        self.assertEqual(check_prose(prose), [])
        prose['abstract'] += ' We achieve 99.9% accuracy.'
        self.assertTrue(check_prose(prose))
        prose['abstract'] = 'The approach is inspired by [invented_paper].'
        self.assertTrue(check_prose(prose))

    def test_results_table_comes_from_test_split_not_dev(self):
        from research.memory_paper import measured_rows
        summary = {'methods': [dict(split='dev',policy='versioned',budget=256,tasks=6,exact_correct=6),
                                dict(split='test',policy='versioned',budget=256,tasks=24,exact_correct=20)]}
        rows = measured_rows(summary, 256)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['exact_correct'], 20)

    def test_method_names_and_grouped_verified_citations_are_not_results(self):
        from research.memory_paper import check_prose, SECTIONS
        prose = {section:'BM25 and Mem0 are named methods [memzero, amem]. We make no state-of-the-art claim.' for section in SECTIONS}
        self.assertEqual(check_prose(prose), [])


if __name__ == '__main__':
    unittest.main()
