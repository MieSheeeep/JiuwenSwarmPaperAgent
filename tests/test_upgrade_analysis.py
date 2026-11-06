import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.artifacts import digest


def cell(task, policy='versioned', reader='baseline', repeat=0, phase='mechanism', **extra):
    value = dict(task_id=task, kind='synthetic', split='test', model='Flash', policy=policy,
                 packer='smaller_first', reader=reader, budget=256, repeat=repeat, phase=phase,
                 family='conflict', source_seed=1)
    value.update(extra)
    value['id'] = digest(value)[:24]
    return value


def outcome(item, exact):
    row = dict(item, status='ok', score={'exact': exact}, call_ids=[])
    row['result_hash'] = digest(row)
    return row


class UpgradeAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)

    def write(self, grid, rows, judgments=None, calls=None):
        (self.run/'grid.json').write_text(json.dumps(grid))
        for name, values in [('results', rows), ('judgments', judgments or []), ('calls', calls or [])]:
            (self.run/f'{name}.jsonl').write_text(''.join(json.dumps(v)+'\n' for v in values))

    def test_exact_paired_binomial_and_holm(self):
        from research.upgrade_analysis import paired_statistics, holm_adjust
        stats = paired_statistics([(f't{i}', 1, 0) for i in range(6)])
        self.assertEqual(stats['n_paired'], 6)
        self.assertEqual(stats['left_only_correct'], 6)
        self.assertEqual(stats['mcnemar_exact_p'], .03125)
        self.assertEqual(holm_adjust([.01, .04, .03]), [.03, .06, .06])
        self.assertEqual(stats['bootstrap_resamples'], 1000)

    def test_unequal_cohorts_match_task_intersection_not_denominators(self):
        from research.upgrade_analysis import analyze_upgrade
        left = [cell(t, reader='conflict_aware') for t in ('a', 'b')]
        right = [cell(t) for t in ('b', 'c')]
        self.write(left+right, [outcome(x, True) for x in left]+[outcome(x, False) for x in right])
        report = analyze_upgrade(self.run)
        contrasts = [x for x in report['contrasts'] if x['family']=='reader' and x['metric']=='exact']
        self.assertEqual(len(contrasts), 1)
        self.assertEqual(contrasts[0]['n_paired'], 1)
        self.assertEqual(contrasts[0]['task_ids'], ['b'])

    def test_repeat_rows_never_become_primary_units(self):
        from research.upgrade_analysis import analyze_upgrade
        a, b = cell('a', reader='conflict_aware'), cell('a')
        repeat = cell('a', reader='conflict_aware', repeat=1, phase='repeat')
        self.write([a,b,repeat], [outcome(a, True),outcome(b,False),outcome(repeat,False)])
        report = analyze_upgrade(self.run)
        reader = next(x for x in report['contrasts'] if x['family']=='reader' and x['metric']=='exact')
        self.assertEqual(reader['n_paired'], 1)
        self.assertEqual(len(report['repeat_consistency']), 1)
        self.assertEqual(report['repeat_consistency'][0]['n_paired'], 1)
        self.assertEqual(report['repeat_consistency'][0]['exact_agreement'], 0)

    def test_missing_invalid_judge_excluded_not_wrong(self):
        from research.upgrade_analysis import analyze_upgrade
        grid = [cell('a', kind='external', phase='external', policy=p, model=m, packer='rank_first')
                for p in ('bm25','dense','hybrid') for m in ('Flash','Pro')]
        rows = [outcome(x, True) for x in grid]
        bad = dict(result_id=grid[0]['id'], call_id='judge', judge_model='Judge', judgment={'correct':True}, record_hash='bad')
        self.write(grid, rows, [bad], [dict(id='judge', model='Judge', output='{"correct":true}')])
        report = analyze_upgrade(self.run)
        judged = [x for x in report['contrasts'] if x['metric']=='external_judge_proxy']
        self.assertTrue(judged)
        self.assertTrue(all(x['n_paired']==0 and x['status']=='not_run' for x in judged))
        self.assertTrue(report['judge_exclusions'])

    def test_valid_judge_provenance_and_tampered_result(self):
        from research.upgrade_analysis import analyze_upgrade
        grid = [cell('a', kind='external', phase='external', policy=p, model=m, packer='rank_first')
                for p in ('bm25','dense','hybrid') for m in ('Flash','Pro')]
        rows = [outcome(x, True) for x in grid]
        judges, calls = [], []
        for row in rows:
            call_id = 'judge-'+row['id']
            call = dict(id=call_id, model='Judge', output='{"correct":true}', logical_key='upgrade/'+row['id']+'/judge')
            judgment = dict(result_id=row['id'], call_id=call_id, judge_model='Judge', judgment={'correct':True})
            judgment['record_hash'] = digest(judgment)
            judges.append(judgment); calls.append(call)
        self.write(grid, rows, judges, calls)
        report = analyze_upgrade(self.run)
        self.assertTrue(any(x['n_paired']==1 for x in report['contrasts'] if x['metric']=='external_judge_proxy'))
        rows[0]['score']['exact'] = False
        self.write(grid, rows, judges, calls)
        with self.assertRaises(ValueError): analyze_upgrade(self.run)

    def test_duplicate_same_condition_task_rejected(self):
        from research.upgrade_analysis import analyze_upgrade
        a = cell('a'); b = dict(a, id='other-id')
        self.write([a,b], [])
        with self.assertRaises(ValueError): analyze_upgrade(self.run)

    def test_result_seed_strata_and_unrun_family_status(self):
        from research.upgrade_analysis import analyze_upgrade
        a, b = cell('a', reader='conflict_aware'), cell('a')
        a.pop('source_seed'); b.pop('source_seed')
        rows = [outcome(a, True), outcome(b, False)]
        for row in rows:
            row['source_seed'] = 77
            row['result_hash'] = digest({k:v for k,v in row.items() if k!='result_hash'})
        self.write([a,b], rows)
        result = analyze_upgrade(self.run)
        contrast = next(x for x in result['contrasts'] if x['family']=='reader')
        self.assertIn('77', contrast['strata']['source_seed'])
        self.write([a,b], [])
        self.assertEqual(analyze_upgrade(self.run)['contrast_family_status']['reader'], 'not_run')

    def test_external_extension_never_enters_matched_contrasts(self):
        from research.upgrade_analysis import analyze_upgrade
        grid = [cell('matched', kind='external', phase='external', policy=p, model=m,
                     packer='rank_first', cohort='external_matched')
                for p in ('bm25','dense','hybrid') for m in ('Flash','Pro')]
        grid.append(cell('extension',kind='external',phase='external',policy='hybrid',model='Flash',
                         packer='rank_first',cohort='external_extension'))
        self.write(grid, [outcome(x,True) for x in grid])
        result = analyze_upgrade(self.run)
        self.assertTrue(all(x['task_ids']==['matched'] for x in result['contrasts'] if x['metric']=='normalized_exact_proxy'))
        full = next(c for c in result['cohorts'] if c['cohort']=='external_full500_hybrid_flash')
        self.assertEqual(full['planned_unique_tasks'], 2)


if __name__ == '__main__': unittest.main()
