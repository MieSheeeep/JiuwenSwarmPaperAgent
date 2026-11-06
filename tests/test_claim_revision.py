import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest


class ClaimRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        self.summary = {'methods': [{'split': 'test', 'policy': 'versioned', 'budget': 256,
                                    'tasks': 24, 'exact_correct': 20, 'exact_accuracy': 20/24}]}
        self.path = self.run / 'summary.json'
        self.path.write_text(json.dumps(self.summary), encoding='utf-8')

    def metric(self):
        from research.claim_revision import make_evidence_ref
        return {'id': 'accuracy', 'type': 'measured', 'text': 'Held-out exact accuracy.',
                'condition': {'kind': 'synthetic', 'split': 'test'},
                'scope': 'Only this controlled run.',
                'value': 20/24, 'operation': 'ratio',
                'evidence_refs': [make_evidence_ref(self.path, '/methods/0/exact_correct'),
                                  make_evidence_ref(self.path, '/methods/0/tasks')]}

    def test_tampered_number_and_source_are_rejected(self):
        from research.claim_revision import validate_claim
        claim = self.metric()
        self.assertEqual(validate_claim(claim, {}), [])
        claim['value'] = .99
        self.assertTrue(any('numeric' in x for x in validate_claim(claim, {})))
        claim['value'] = 20/24
        self.path.write_text('{}', encoding='utf-8')
        self.assertTrue(any('hash' in x for x in validate_claim(claim, {})))

    def test_unverified_citation_and_unsupported_novelty(self):
        from research.claim_revision import validate_claim
        self.assertTrue(validate_claim({'type': 'qualitative', 'text': 'See [EvidentialRAG].'}, {}))
        self.assertTrue(validate_claim({'type': 'qualitative', 'text': 'We introduce a novel method.'}, {}))
        self.assertEqual(validate_claim({'type': 'qualitative', 'text': 'Established prior work [temporal].'}, {}), [])
        self.assertTrue(validate_claim({'type': 'qualitative', 'text': 'Accuracy is 99%.'}, {}))

    def test_ledger_never_inherits_review_score_or_certifies_gaps(self):
        from research.claim_revision import build_claim_ledger
        ledger = build_claim_ledger(self.run, {'abstract': 'We introduce a novel method.'})
        self.assertIsNone(ledger['review_score'])
        self.assertTrue(ledger['unsupported_claims'])
        self.assertEqual(len(ledger['review_response_matrix']), 10)
        self.assertTrue(all(x['status'] != 'solved' for x in ledger['review_response_matrix']))
        metrics = [x for x in ledger['claims'] if x['type'] == 'measured']
        self.assertTrue(metrics)
        self.assertTrue(all(not x['validation_issues'] for x in metrics))

    def test_revision_is_copied_and_requires_evidence_and_reason(self):
        from research.claim_revision import apply_revision
        sections = {'abstract': 'Old wording.'}
        refs = self.metric()['evidence_refs']
        record = apply_revision(sections, {'abstract': 'Controlled finding [temporal].'}, 'Limit scope.', refs)
        self.assertEqual(sections['abstract'], 'Old wording.')
        self.assertEqual(record.sections['abstract'], 'Controlled finding [temporal].')
        self.assertEqual(record.changes[0]['before'], 'Old wording.')
        with self.assertRaises(TypeError):
            record.sections['abstract'] = 'Tampered'
        with self.assertRaises(ValueError):
            apply_revision(sections, {'abstract': 'New wording.'}, '', refs)
        with self.assertRaises(ValueError):
            apply_revision(sections, {'abstract': 'New wording.'}, 'Reason', [])
        with self.assertRaises(ValueError):
            apply_revision(sections, {'abstract': 'We achieve 99%.'}, 'Reason', refs)

    def test_cached_accuracy_is_recomputed_and_absent_run_has_no_old_claims(self):
        from research.claim_revision import build_claim_ledger
        self.summary['methods'][0]['exact_accuracy'] = .99
        self.path.write_text(json.dumps(self.summary), encoding='utf-8')
        ledger = build_claim_ledger(self.run)
        self.assertTrue(ledger['unsupported_claims'])
        empty = self.run / 'empty'
        empty.mkdir()
        ledger = build_claim_ledger(empty)
        self.assertEqual(ledger['claims'], [])
        self.assertTrue(ledger['missing_evidence'])

    def test_condition_retains_all_upgrade_dimensions(self):
        from research.claim_revision import build_claim_ledger
        self.summary['methods'][0].update(kind='external', model='test-model', packer='greedy', reader='conflict')
        self.path.write_text(json.dumps(self.summary), encoding='utf-8')
        condition = build_claim_ledger(self.run)['claims'][0]['condition']
        self.assertEqual(condition['kind'], 'external')
        self.assertEqual(condition['packer'], 'greedy')

    def test_metric_locator_and_arithmetic_schema_are_required(self):
        from research.claim_revision import validate_claim
        claim = self.metric()
        claim['evidence_refs'][0]['locator'] = '/methods/0/absent'
        self.assertTrue(validate_claim(claim, {}))

    def test_imported_claim_cannot_borrow_historical_run_metrics(self):
        from research.claim_revision import build_claim_ledger
        claim = self.metric()
        selected = self.run / 'new-run'
        selected.mkdir()
        (selected / 'summary.json').write_text(json.dumps({'measured_claims': [claim]}))
        ledger = build_claim_ledger(selected)
        self.assertTrue(ledger['unsupported_claims'])
        self.assertTrue(any('selected run' in issue for issue in ledger['claims'][0]['validation_issues']))

    def test_imported_claim_with_selected_run_metrics_is_supported(self):
        from research.claim_revision import build_claim_ledger, make_evidence_ref
        metrics = self.run / 'counts.json'
        metrics.write_text(json.dumps({'correct': 20, 'tasks': 24}))
        claim = self.metric()
        claim['evidence_refs'] = [make_evidence_ref(metrics, '/correct'), make_evidence_ref(metrics, '/tasks')]
        self.path.write_text(json.dumps({'measured_claims': [claim]}))
        ledger = build_claim_ledger(self.run)
        self.assertEqual(ledger['unsupported_claims'], [])

    def test_measured_claim_requires_condition_scope_and_external_proxy_qualifier(self):
        from research.claim_revision import validate_claim
        for field in ('condition', 'scope'):
            claim = self.metric()
            claim.pop(field)
            with self.subTest(field=field):
                self.assertTrue(validate_claim(claim, {}))
        claim = self.metric()
        claim['condition']['kind'] = 'external'
        self.assertTrue(validate_claim(claim, {}))
        claim['scope'] = 'Normalized proxy; not an official benchmark judge score.'
        self.assertEqual(validate_claim(claim, {}), [])

    def test_nonfinite_reported_and_computed_metrics_are_rejected(self):
        from research.claim_revision import make_evidence_ref, validate_claim
        values = self.run / 'values.json'
        values.write_text(json.dumps({'a': 1e308, 'b': 1e308}))
        claim = self.metric()
        claim.update(operation='sum', value=float('inf'),
                     evidence_refs=[make_evidence_ref(values, '/a'), make_evidence_ref(values, '/b')])
        self.assertTrue(validate_claim(claim, {}))
        claim['operation'] = 'identity'
        claim['evidence_refs'] = claim['evidence_refs'][:1]
        for value in (float('inf'), float('nan'), -(10**1000)):
            claim['value'] = value
            self.assertTrue(validate_claim(claim, {}))
        claim = self.metric()
        claim['operation'] = 'unsupported'
        self.assertTrue(validate_claim(claim, {}))


if __name__ == '__main__':
    unittest.main()
