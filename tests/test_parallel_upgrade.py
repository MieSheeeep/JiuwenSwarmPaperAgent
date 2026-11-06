import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from research import parallel_upgrade as p


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')


def make_root(tmp_path):
    root=tmp_path/'root';root.mkdir()
    p.save_json(root/'protocol.json',{'token_limit':3000000,'max_calls':6000})
    p.save_json(root/'grid.json',[{'id':'row','kind':'synthetic','task_id':'task','reader':'baseline'}])
    return root


def reserve_unknown(root):
    request={'id':'unknown','tag':'upgrade/row/answer','reserved_tokens':10000}
    call={**request,'status':'unknown','usage':None,'error_type':'FrameworkError','output':''}
    write(root/'requests.jsonl',[request]);write(root/'calls.jsonl',[call])
    registry={'schema_version':1,'mode':'conservative_reservation_not_actual_usage',
              'authorization':'User continued after provider recharge; no free/zero-cost inference.',
              'entries':[{'id':request['id'],'request_sha256':p.digest(request),
                          'call_sha256':p.digest(call),'reserved_tokens':10000,
                          'reason':'unreconciled transport failure'}]}
    p.save_json(root/'admission_reserves.json',registry)
    return request,call,registry


class ParallelUpgradeTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp_path=Path(temporary.name)


    def test_whole_tasks_disjoint_exhaustive(self):
        grid=[{'id':f'{k}-{t}-{j}', 'kind':k, 'task_id':t, 'reader':'baseline'} for k in ['synthetic','external'] for t in ['a','b','c'] for j in range(4)]
        parts=p.partition_pending(grid, {'synthetic-a-0'}, 3)
        assert {r['id'] for part in parts for r in part} == {r['id'] for r in grid}-{'synthetic-a-0'}
        seen={}
        for i,part in enumerate(parts):
            for r in part:
                key=(r['kind'],r['task_id'])
                assert seen.setdefault(key,i)==i
        assert parts == p.partition_pending(grid, {'synthetic-a-0'}, 3)

    def test_allocations_never_exceed_cap_0(self):
        prior=0
        caps=p.allocate_caps(3000000, prior, [1,2,3])
        assert sum(caps)+prior <= 3000000-150000
        assert all(type(n) is int and n>=0 for n in caps)

    def test_allocations_never_exceed_cap_123456(self):
        prior=123456
        caps=p.allocate_caps(3000000, prior, [1,2,3])
        assert sum(caps)+prior <= 3000000-150000
        assert all(type(n) is int and n>=0 for n in caps)

    def test_allocations_never_exceed_cap_2849999(self):
        prior=2849999
        caps=p.allocate_caps(3000000, prior, [1,2,3])
        assert sum(caps)+prior <= 3000000-150000
        assert all(type(n) is int and n>=0 for n in caps)

    def test_allocations_never_exceed_cap_2850000(self):
        prior=2850000
        caps=p.allocate_caps(3000000, prior, [1,2,3])
        assert sum(caps)+prior <= 3000000-150000
        assert all(type(n) is int and n>=0 for n in caps)

    def test_duplicate_paid_id_different_row_rejected(self):
        with self.assertRaisesRegex(ValueError, 'conflict'):
            p.deduplicate([[{'id':'paid', 'tag':'upgrade/a/answer'}],[{'id':'paid','tag':'upgrade/b/answer'}]], 'id')

    def test_selection_context_conflict_rejected(self):
        with self.assertRaisesRegex(ValueError, 'conflict'):
            p.deduplicate([[{'key':'s','text':'a','record_ids':['a']}],[{'key':'s','text':'b','record_ids':['a']}]], 'key', selections=True)
        first={'key':'s','text':'a','record_ids':['a'],'preprocessing_seconds':1,'selection_hash':'original'}
        second={**first,'preprocessing_seconds':2,'selection_hash':'later'}
        assert p.deduplicate([[first],[second]], 'key', selections=True)==[first]

    def test_unknown_child_request_stops_every_worker(self):
        tmp_path=self.tmp_path
        workers=[tmp_path/f'worker_{i}' for i in range(3)]
        for worker in workers: worker.mkdir()
        write(workers[0]/'requests.jsonl',[{'id':'unresolved'}])
        assert p.stop_on_unknown(workers, active_inflight=False)
        assert all((w/'STOP_REQUESTED').exists() for w in workers)

    def test_active_inflight_does_not_stop_other_workers(self):
        tmp_path=self.tmp_path
        workers=[tmp_path/'worker_0'];workers[0].mkdir()
        write(workers[0]/'requests.jsonl',[{'id':'inflight'}])
        assert not p.stop_on_unknown(workers, active_inflight=True)
        write(workers[0]/'calls.jsonl',[{'id':'inflight','status':'unknown','usage':None}])
        assert p.stop_on_unknown(workers, active_inflight=True)

    def test_snapshot_ignores_only_unterminated_tail(self):
        tmp_path=self.tmp_path
        path=tmp_path/'calls.jsonl';path.write_bytes(b'{"id":"ok"}\n{"id":')
        assert p.snapshot_jsonl(path)==[{'id':'ok'}]
        path.write_bytes(b'bad\n')
        with self.assertRaises(ValueError):p.snapshot_jsonl(path)

    def test_complete_usage_validated(self):
        request={'id':'x','tag':'upgrade/a/answer'}
        call={**request,'status':'ok','usage':{'input_tokens':2,'output_tokens':1,'total_tokens':3}}
        assert p.validate_paid([request],[call])==3
        with self.assertRaises(ValueError):p.validate_paid([request],[])
        with self.assertRaises(ValueError):p.validate_paid([request],[{**call,'status':'unknown'}])

    def test_plan_and_prepare_copy_cache_but_no_paid_ledger(self):
        tmp_path=self.tmp_path
        root=make_root(tmp_path)
        write(root/'selections.jsonl',[{'key':'cache','text':'unchanged'}])
        plan=p.plan_run(root)
        workers=p.prepare_workers(root,plan)
        assert len(workers)==3
        assert sum(w['token_limit'] for w in plan['workers'])==2850000
        for w in workers:
            assert (w/'selections.jsonl').read_bytes()==(root/'selections.jsonl').read_bytes()
            assert not (w/'calls.jsonl').exists()
            assert p.load(w/'assignment.json')['root_protocol_hash']==p.file_digest(root/'protocol.json')

    def test_approved_root_unknown_deducts_hold_without_changing_usage(self):
        root=make_root(self.tmp_path)
        _,call,_=reserve_unknown(root)
        before=(root/'calls.jsonl').read_bytes()
        plan=p.plan_run(root)
        assert plan['prior_known_usage']==0
        assert plan['reserved_unknown_tokens']==10000
        assert plan['prior_admission_usage']==10000
        assert sum(w['token_limit'] for w in plan['workers'])==2840000
        workers=p.prepare_workers(root,plan)
        assert all(p.load(w/'assignment.json')['admission_reserves_sha256']==p.file_digest(root/'admission_reserves.json') for w in workers)
        assert p.merge_segments(root,workers)==10000
        manifest=p.load(root/'segment_merge_manifest.json')
        assert manifest['actual_total_tokens']==0
        assert manifest['admission_total_tokens']==10000
        assert (root/'calls.jsonl').read_bytes()==before
        assert p.read_jsonl(root/'calls.jsonl')[0]['usage'] is None

    def test_unknown_absent_bad_or_modified_reserve_fails_closed(self):
        root=make_root(self.tmp_path)
        _,_,registry=reserve_unknown(root)
        (root/'admission_reserves.json').unlink()
        with self.assertRaises(ValueError):p.plan_run(root)
        registry['entries'][0]['reserved_tokens']=9999
        p.save_json(root/'admission_reserves.json',registry)
        with self.assertRaises(ValueError):p.plan_run(root)
        registry['entries'][0]['reserved_tokens']=10000
        registry['entries'][0]['call_sha256']='changed'
        p.save_json(root/'admission_reserves.json',registry)
        with self.assertRaises(ValueError):p.plan_run(root)

    def test_reserve_change_after_assignment_rejected_before_merge(self):
        root=make_root(self.tmp_path)
        _,_,registry=reserve_unknown(root)
        workers=p.prepare_workers(root,p.plan_run(root))
        registry['entries'][0]['reserved_tokens']=11000
        p.save_json(root/'admission_reserves.json',registry)
        with self.assertRaisesRegex(ValueError,'reserves changed'):p.merge_segments(root,workers)

    def test_root_reserve_never_approves_unknown_child(self):
        root=make_root(self.tmp_path)
        request,call,_=reserve_unknown(root)
        workers=p.prepare_workers(root,p.plan_run(root))
        write(workers[0]/'requests.jsonl',[{**request,'id':'child'}])
        write(workers[0]/'calls.jsonl',[{**call,'id':'child'}])
        with self.assertRaisesRegex(ValueError,'Unknown usage'):p.merge_segments(root,workers)

    def test_only_approved_unknowns_bypass_paid_partial_guard(self):
        root=make_root(self.tmp_path)
        request,call,_=reserve_unknown(root)
        request={**request,'id':'known'}
        call={**call,**request,'status':'ok','usage':{'input_tokens':2,'output_tokens':1,'total_tokens':3}}
        p.append_durable(root/'requests.jsonl',request);p.append_durable(root/'calls.jsonl',call)
        with self.assertRaisesRegex(ValueError,'paid partial'):p.plan_run(root)

    def test_summary_separates_answer_completion_actual_usage_and_holds(self):
        root=make_root(self.tmp_path)
        reserve_unknown(root)
        write(root/'results.jsonl',[{'id':'row','kind':'synthetic','status':'ok'}])
        with patch('research.review_upgrade.summarize',return_value={}),patch('research.review_upgrade._row_summary',return_value=[]):
            summary=p.refresh_summary(root)
        assert summary['answer_conditions_complete']
        assert not summary['evaluation_complete']
        assert summary['resources']['total_tokens']==0
        assert summary['resources']['reserved_unknown_tokens']==10000
        assert summary['resources']['admission_total_tokens']==10000
        assert summary['resources']['unknown_usage_calls']==1
        assert summary['resources']['unreserved_unknown_usage_calls']==0
        assert p.load(root/'summary.json')['answer_conditions_complete']

    def test_new_segment_directory_keeps_old_evidence_immutable(self):
        root=make_root(self.tmp_path)
        old=root/'segments'/'worker_0'/'evidence.txt'
        old.parent.mkdir(parents=True);old.write_text('original',encoding='utf-8')
        plan=p.plan_run(root,segments_name='segments_round2')
        workers=p.prepare_workers(root,plan)
        assert all(w.parent==root/'segments_round2' for w in workers)
        assert old.read_text(encoding='utf-8')=='original'
        with self.assertRaises(ValueError):p.prepare_workers(root,plan)
        for name in ('..','../escape','a/b','a\\b','C:escape','', '/absolute','CON','nul','COM1'):
            with self.subTest(name=name),self.assertRaises(ValueError):p.plan_run(root,segments_name=name)

    def test_merge_is_append_only_and_idempotent(self):
        tmp_path=self.tmp_path
        root=make_root(tmp_path)
        request={'id':'paid','tag':'upgrade/row/answer'}
        call={**request,'status':'ok','usage':{'input_tokens':2,'output_tokens':1,'total_tokens':3}}
        write(root/'requests.jsonl',[request]);write(root/'calls.jsonl',[call])
        # A root paid condition must have its successful result before partition.
        write(root/'results.jsonl',[{'id':'row','kind':'synthetic','status':'ok'}])
        p.save_json(root/'grid.json',p.load(root/'grid.json')+[{'id':'next','kind':'synthetic','task_id':'next','reader':'baseline'}])
        plan=p.plan_run(root);workers=p.prepare_workers(root,plan)
        request={**request,'id':'new','tag':'upgrade/next/answer'}
        call={**call,**request}
        write(workers[0]/'requests.jsonl',[request]);write(workers[0]/'calls.jsonl',[call])
        before=(root/'calls.jsonl').read_bytes()
        assert p.merge_segments(root,workers)==6
        merged=(root/'calls.jsonl').read_bytes()
        assert merged.startswith(before)
        assert p.merge_segments(root,workers)==6
        assert (root/'calls.jsonl').read_bytes()==merged

    def test_merge_rejects_conflict_before_any_append(self):
        tmp_path=self.tmp_path
        root=make_root(tmp_path);plan=p.plan_run(root);workers=p.prepare_workers(root,plan)
        write(workers[0]/'requests.jsonl',[{'id':'x','tag':'upgrade/row/answer'}])
        write(workers[1]/'requests.jsonl',[{'id':'x','tag':'upgrade/other/answer'}])
        with self.assertRaises(ValueError):p.merge_segments(root,workers)
        assert not (root/'requests.jsonl').exists()

    def test_merge_rejects_unassigned_child_result(self):
        tmp_path=self.tmp_path
        root=make_root(tmp_path);plan=p.plan_run(root);workers=p.prepare_workers(root,plan)
        row={'id':'foreign','kind':'synthetic','task_id':'foreign','status':'ok'}
        row['result_hash']=p.digest(row)
        write(workers[0]/'results.jsonl',[row])
        with self.assertRaisesRegex(ValueError, 'assigned'):p.merge_segments(root,workers)
        assert not (root/'results.jsonl').exists()


if __name__ == "__main__":
    unittest.main()
