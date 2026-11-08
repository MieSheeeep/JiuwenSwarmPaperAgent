"""Reporting must expose the saved evidence, including unfavorable decisions."""
import csv
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from research.artifacts import digest, file_digest, save_json


def fixture_rows():
    rows = []
    for case_id, gain, truth, defer in [('useful', .04, 'useful', .8),
                                         ('futile', -.04, 'futile', .2),
                                         ('boundary', 0., 'boundary', .5)]:
        for interval in ('paired_normal', 'exact_joint'):
            for policy, go, no, wait in [('legacy_binary', .6, .4, 0.), ('delta_binary', .3, .7, 0.),
                    ('tri_state', .1, .9-defer, defer), ('always_go', 1., 0., 0.),
                    ('always_reject', 0., 1., 0.), ('always_defer', 0., 0., 1.)]:
                rows.append(dict(case_id=case_id, kind='synthetic', dataset=None, seed=None,
                    pair=None, gain=gain, discordance=.1, delta=0., n=16,
                    interval=interval, policy=policy, p_go=go, p_no_go=no, p_defer=wait,
                    ci_coverage=.97, truth=truth,
                    false_go_probability=go if truth == 'futile' else 0.,
                    false_prune_probability=no if truth == 'useful' else 0.))
    return rows


class ReportingTests(unittest.TestCase):
    def reporting(self):
        spec = importlib.util.find_spec('research.workflow.pilot_pruning_reporting')
        self.assertIsNotNone(spec, 'The reporting module has not been implemented')
        return importlib.import_module(spec.name)

    def study(self, directory, rows):
        root = directory / 'experiment'; root.mkdir()
        (root / 'results.json').write_text(json.dumps({'rows': rows, 'rows_sha256': digest(rows),
                                                      'resources': {}}), encoding='utf-8')
        return SimpleNamespace(root=root, directory=directory, audit=lambda protocol: {'ok': True})

    def test_saved_rows_all_costs_and_nonfree_deferral(self):
        reporting = self.reporting()
        with tempfile.TemporaryDirectory() as tmp:
            study = self.study(Path(tmp), fixture_rows())
            result = reporting.analyze(study, {'figure_formats': ['png']})
            self.assertEqual(result['rows_hash'], digest(fixture_rows()))
            self.assertEqual(len(result['metrics']), 3*2*8)
            self.assertEqual(len(result['costs']), len(result['metrics'])*27)
            for item in result['costs']:
                self.assertAlmostEqual(item['expected_cost'],
                    item['c_defer']*item['p_defer'] +
                    item['c_false_go']*item['false_go_probability'] +
                    item['c_false_prune']*item['false_prune_probability'])
                if item['policy'] == 'always_defer':
                    self.assertAlmostEqual(item['expected_cost'], item['c_defer'])
                    self.assertEqual(item['automatic_coverage'], 0.)
            with (study.directory/'analysis'/'all_metrics.csv').open(encoding='utf-8') as stream:
                csv_rows = list(csv.DictReader(stream))
            self.assertEqual(len(csv_rows), len(fixture_rows()))
            equal = [row for row in result['metrics'] if row['mixture'] == 'equal'
                     and row['interval'] == 'paired_normal']
            tri = next(row for row in equal if row['policy'] == 'tri_state')
            random = next(row for row in equal if row['policy'] == 'matched_random_legacy_binary')
            self.assertAlmostEqual(tri['p_defer'], .5)
            self.assertAlmostEqual(random['p_defer'], .5)
            self.assertAlmostEqual(random['false_prune_probability'], .4/3*.5)
            self.assertAlmostEqual(tri['false_prune_probability'], .1/3)
            self.assertTrue(result['figures'])
            self.assertEqual(len(result['figures']), 2)  # synthetic n curves and cost heatmap
            self.assertTrue(all((study.directory/f['path']).exists() for f in result['figures']))
            self.assertIn('not independent', result['evidence_summary'])
            self.assertIn('no statistical novelty', result['evidence_summary'])

    def test_tampered_or_invalid_rows_are_not_reported(self):
        reporting = self.reporting()
        with tempfile.TemporaryDirectory() as tmp:
            study = self.study(Path(tmp), fixture_rows())
            path = study.root/'results.json'
            saved = json.loads(path.read_text()); saved['rows'][0]['p_go'] = .99
            path.write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError, 'hash'):
                reporting.analyze(study, {'figure_formats': ['png']})

    def test_no_invented_empirical_measurements_or_success_claim(self):
        reporting = self.reporting()
        with tempfile.TemporaryDirectory() as tmp:
            study = self.study(Path(tmp), fixture_rows())
            result = reporting.analyze(study, {'figure_formats': ['png']})
            self.assertEqual(result['scope']['empirical_datasets'], [])
            self.assertIn('No empirical replay rows', result['evidence_summary'])
            self.assertTrue(all(c['kind'] == 'observed' for c in result['claims']))

    def test_failed_source_audit_blocks_reporting(self):
        reporting = self.reporting()
        with tempfile.TemporaryDirectory() as tmp:
            study = self.study(Path(tmp), fixture_rows())
            study.audit = lambda protocol: {'passed': False, 'findings': ['changed predictions']}
            with self.assertRaisesRegex(ValueError, 'audit'):
                reporting.analyze(study, {'figure_formats': ['png']})

    def test_real_core_integration_and_audit_feed_saved_report(self):
        reporting = self.reporting()
        from research.workflow.pilot_pruning_study import PilotPruningStudy, integrate_case
        with tempfile.TemporaryDirectory() as tmp:
            study = PilotPruningStudy(Path(tmp))
            study.root.mkdir(parents=True)
            study.data.mkdir(parents=True)
            save_json(study.manifest_path, {'files': {}, 'datasets': []})
            rows = integrate_case(2, -.04, .1, 0.) + integrate_case(2, .04, .1, 0.)
            save_json(study.root/'results.json', {'rows': rows, 'rows_sha256': digest(rows)})
            protocol = {'figure_formats': ['png'],
                        'source_hashes': {str(study.manifest_path): file_digest(study.manifest_path)},
                        'manifest_sha256': file_digest(study.manifest_path)}
            # This tiny integration fixture is not a registered full experiment.
            # Exercise the real read-only hash/probability audit without claiming
            # full-grid completeness (checked by core's separate frozen audit).
            report_study = SimpleNamespace(root=study.root, directory=study.directory,
                                           audit=lambda ignored: study.audit({}))
            result = reporting.analyze(report_study, protocol)
            self.assertTrue(result['audit']['passed'])
            self.assertEqual(result['audit']['rows'], 24)
            self.assertTrue(all(row['ci_coverage'] >= .95 for row in result['metrics']
                                if row['interval'] == 'exact_joint'))
            self.assertEqual(len(result['cost_frontier']), 3*2*27)


if __name__ == '__main__':
    unittest.main()
