"""Operational whole-task process controller; imports never load credentials or models."""
from __future__ import annotations
import argparse
import asyncio
from collections import defaultdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from research.artifacts import digest, file_digest, save_json
from research.jsonl_ledger import read_jsonl, append_durable
from research.model_gateway import valid_usage
from research.spend_reservation import load_reserves

RESERVE = 150000
LEDGERS = {'requests.jsonl':'id', 'calls.jsonl':'id', 'results.jsonl':'id',
           'judgments.jsonl':'result_id', 'selections.jsonl':'key', 'invocation_errors.jsonl':'id'}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def snapshot_jsonl(path):
    """Read a live ledger, excluding its incomplete final LF-delimited record."""
    path=Path(path)
    if not path.exists(): return []
    data=path.read_bytes()
    data=data[:data.rfind(b'\n')+1]
    return [json.loads(line) for line in data.decode('utf-8').split('\n') if line.strip()]


def partition_pending(grid, completed, workers=3):
    if workers != 3: raise ValueError('This operational amendment specifies three workers')
    groups=defaultdict(list)
    for row in grid:
        if row['id'] not in completed: groups[(row['kind'],row['task_id'])].append(row)
    def weight(rows):
        return sum(2 if r['kind']=='external' or r.get('reader')=='reflection' else 1 for r in rows)
    parts=[[] for _ in range(workers)]; loads=[0]*workers
    # Largest work first; all ties resolve by task identity and worker index.
    for key,rows in sorted(groups.items(),key=lambda pair:(-weight(pair[1]),pair[0])):
        index=min(range(workers),key=lambda i:(loads[i],i))
        parts[index].extend(rows);loads[index]+=weight(rows)
    # Retain the original scientific condition ordering within every process.
    owners={r['id']:i for i,part in enumerate(parts) for r in part}
    return [[r for r in grid if owners.get(r['id'])==i] for i in range(workers)]


def allocate_caps(global_cap, prior_usage, weights):
    available=global_cap-prior_usage-RESERVE
    if available<0: raise ValueError('Global writing reserve exhausted')
    if not weights or any(type(w) is not int or w<0 for w in weights): raise ValueError('Invalid weights')
    total=sum(weights)
    if not total:return [0]*len(weights)
    caps=[available*w//total for w in weights]
    remainder=available-sum(caps)
    for i in sorted(range(len(weights)),key=lambda i:(-(available*weights[i]%total),i))[:remainder]:caps[i]+=1
    return caps


def deduplicate(sources, key, *, selections=False):
    found={}
    for records in sources:
        for row in records:
            identity=row[key]
            if identity in found:
                before=found[identity]
                if selections:
                    # Timing may differ, but every scientific selection field must match.
                    ignored={'selection_hash','preprocessing_seconds'}
                    equivalent={k:v for k,v in before.items() if k not in ignored} == {k:v for k,v in row.items() if k not in ignored}
                else: equivalent=before==row
                if not equivalent:raise ValueError(f'Duplicate {key} conflict: {identity}')
            else:found[identity]=row
    return list(found.values())


def validate_paid(requests,calls,reserves=None):
    reserves=reserves or {}
    requests=deduplicate([requests],'id');calls=deduplicate([calls],'id')
    rq={r['id']:r for r in requests}; ca={r['id']:r for r in calls}
    if set(rq)!=set(ca):raise ValueError('Unresolved request/response IDs')
    for identity,call in ca.items():
        if call.get('status')!='ok' or not valid_usage(call.get('usage')):
            if identity not in reserves:raise ValueError('Unknown usage/status')
        if call.get('tag')!=rq[identity].get('tag'):raise ValueError('Request/call tag conflict')
        if rq[identity].get('fingerprint')!=call.get('fingerprint'):raise ValueError('Request/call fingerprint conflict')
    if any(identity not in ca or (ca[identity].get('status')=='ok' and valid_usage(ca[identity].get('usage'))) for identity in reserves):
        raise ValueError('Reserve does not match unknown call')
    return sum(c['usage']['total_tokens'] for c in calls if valid_usage(c.get('usage'))) + sum(reserves.values())


def segment_name(value):
    if not isinstance(value,str) or not value or value in ('.','..') or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in value):
        raise ValueError('segments-name must be a safe single directory name')
    if value.upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError('segments-name must be a safe single directory name')
    return value


def reserve_hash(root):
    path=Path(root)/'admission_reserves.json'
    return file_digest(path) if path.exists() else None


def check_reserve_hash(root, record):
    if reserve_hash(root)!=record.get('admission_reserves_sha256'):
        raise ValueError('Admission reserves changed after assignment')


def stop_all(workers, reason):
    for worker in workers:(Path(worker)/'STOP_REQUESTED').write_text(reason+'\n',encoding='utf-8')


def stop_on_unknown(workers, *, active_inflight=True):
    """An active request is expected; failed usage or a stopped unresolved request is not."""
    unknown=False
    for worker in workers:
        requests=snapshot_jsonl(Path(worker)/'requests.jsonl');calls=snapshot_jsonl(Path(worker)/'calls.jsonl')
        errors=snapshot_jsonl(Path(worker)/'invocation_errors.jsonl')
        pending={r['id'] for r in requests}-{c['id'] for c in calls}
        unknown |= any(c.get('status')!='ok' or not valid_usage(c.get('usage')) for c in calls)
        unknown |= any(e.get('spend_uncertain') for e in errors)
        unknown |= bool(pending) and not active_inflight
    if unknown:stop_all(workers,'Controller detected unknown paid usage; reconcile before further spend')
    return unknown


def plan_run(root, workers=3, segments_name='segments'):
    segments_name=segment_name(segments_name)
    root=Path(root).resolve();protocol=load(root/'protocol.json');grid=load(root/'grid.json')
    requests=read_jsonl(root/'requests.jsonl');calls=read_jsonl(root/'calls.jsonl')
    reserves=load_reserves(root,requests=requests,calls=calls)
    prior=validate_paid(requests,calls,reserves)
    results=read_jsonl(root/'results.jsonl');completed={r['id'] for r in results if r.get('status')=='ok'}
    if len(completed)!=len(results):raise ValueError('Duplicate or failed root results require reconciliation')
    judgments=read_jsonl(root/'judgments.jsonl');judged={j['result_id'] for j in judgments}
    if any(r['kind']=='external' and r['id'] not in judged for r in results):raise ValueError('Root external judgments must be completed before partition')
    if any(c['tag'].split('/')[1] not in completed for c in calls if c['id'] not in reserves):raise ValueError('Root has paid partial conditions; resume sequentially before partition')
    if any(e.get('spend_uncertain') for e in read_jsonl(root/'invocation_errors.jsonl')):raise ValueError('Unknown root invocation spend')
    parts=partition_pending(grid,completed,workers)
    weights=[sum(2 if r['kind']=='external' or r.get('reader')=='reflection' else 1 for r in part) for part in parts]
    caps=allocate_caps(protocol['token_limit'],prior,weights)
    return {'schema_version':1,'root':str(root),'root_protocol_hash':file_digest(root/'protocol.json'),
            'controller_hash':file_digest(__file__),'source_hashes':{name:file_digest(root/name) for name in [*LEDGERS,'dataset.json','grid.json','external_protocol/tasks.json'] if (root/name).exists()},'global_cap':protocol['token_limit'],
            'prior_known_usage':prior-sum(reserves.values()),'reserved_unknown_tokens':sum(reserves.values()),
            'prior_admission_usage':prior,'admission_reserves_sha256':reserve_hash(root),
            'segments_name':segments_name,'writing_reserve':RESERVE,'completed_ids':sorted(completed),
            'workers':[{'index':i,'weight':weights[i],'token_limit':caps[i],'grid':part} for i,part in enumerate(parts)]}


def prepare_workers(root, plan):
    root=Path(root);paths=[];protocol=load(root/'protocol.json')
    check_reserve_hash(root,plan)
    segments=root/segment_name(plan.get('segments_name','segments'))
    if segments.exists():raise ValueError('Existing segments require reconciliation before a new launch')
    for worker in plan['workers']:
        path=segments/f"worker_{worker['index']}"
        if path.exists():raise ValueError('Segment already exists; reconcile/merge before creating another run')
        path.mkdir(parents=True)
        save_json(path/'protocol.json',{**protocol,'token_limit':worker['token_limit'],'max_calls':6000})
        save_json(path/'grid.json',worker['grid'])
        save_json(path/'assignment.json',{k:v for k,v in worker.items() if k!='grid'} | {
            'root':str(root.resolve()),'root_protocol_hash':plan['root_protocol_hash'],
            'admission_reserves_sha256':plan.get('admission_reserves_sha256'),
            'controller_hash':plan['controller_hash'],'source_hashes':plan['source_hashes'],'row_ids':[r['id'] for r in worker['grid']],
            'grid_hash':digest(worker['grid']),'tasks_file':str((root/'dataset.json').resolve()),
            'external_tasks_file':str((root/'external_protocol/tasks.json').resolve())})
        if (root/'selections.jsonl').exists():shutil.copyfile(root/'selections.jsonl',path/'selections.jsonl')
        paths.append(path)
    save_json(root/'parallel_assignment.json',plan)
    return paths


def merge_segments(root, workers):
    """Validate every proposed append first. Never rewrite an existing paid ledger."""
    root=Path(root);plan=load(root/'parallel_assignment.json')
    if file_digest(root/'protocol.json')!=plan['root_protocol_hash']:raise ValueError('Root protocol changed')
    if file_digest(__file__)!=plan['controller_hash']:raise ValueError('Controller changed after assignment')
    check_reserve_hash(root,plan)
    reserves=load_reserves(root)
    merged={};manifest=[]
    for worker in workers:
        worker=Path(worker);assignment=load(worker/'assignment.json')
        assigned={r['id']:r for r in load(worker/'grid.json')}
        if digest(list(assigned.values()))!=assignment['grid_hash']:raise ValueError('Assigned grid changed')
        if assignment['root_protocol_hash']!=plan['root_protocol_hash']:raise ValueError('Assigned root protocol changed')
        if assignment.get('admission_reserves_sha256')!=plan.get('admission_reserves_sha256'):raise ValueError('Assigned admission reserves changed')
        worker_usage=validate_paid(read_jsonl(worker/'requests.jsonl'),read_jsonl(worker/'calls.jsonl'))
        if worker_usage>assignment['token_limit']:raise ValueError('Worker token allocation exceeded')
        for row in read_jsonl(worker/'results.jsonl'):
            if row['id'] not in assigned:raise ValueError('Result outside assigned grid')
            if any(row.get(k)!=v for k,v in assigned[row['id']].items()):raise ValueError('Assigned condition changed')
            if row.get('result_hash')!=digest({k:v for k,v in row.items() if k!='result_hash'}):raise ValueError('Result hash changed')
        for row in read_jsonl(worker/'selections.jsonl'):
            if row.get('selection_hash')!=digest({k:v for k,v in row.items() if k!='selection_hash'}):raise ValueError('Selection hash changed')
    for name,key in LEDGERS.items():
        sources=[read_jsonl(root/name)]+[read_jsonl(Path(w)/name) for w in workers]
        merged[name]=deduplicate(sources,key,selections=name=='selections.jsonl')
        for w in workers:
            source=Path(w)/name
            if source.exists():manifest.append({'path':str(source.resolve()),'sha256':file_digest(source),'records':len(read_jsonl(source))})
    usage=validate_paid(merged['requests.jsonl'],merged['calls.jsonl'],reserves)
    if usage>plan['global_cap']-RESERVE:raise ValueError('Global token cap/writing reserve exceeded')
    for name,key in LEDGERS.items():
        existing={r[key] for r in read_jsonl(root/name)}
        for row in merged[name]:
            if row[key] not in existing:append_durable(root/name,row);existing.add(row[key])
    save_json(root/'segment_merge_manifest.json',{'root_protocol_hash':plan['root_protocol_hash'],
              'controller_hash':plan['controller_hash'],'sources':manifest,'actual_total_tokens':usage-sum(reserves.values()),
              'admission_reserves_sha256':plan.get('admission_reserves_sha256'),
              'reserved_unknown_tokens':sum(reserves.values()),'admission_total_tokens':usage,
              'writing_reserve':RESERVE,'global_cap':plan['global_cap']})
    return usage


def refresh_summary(root, workers=(), terminal=None, active_workers=0):
    from research.review_upgrade import summarize, _row_summary
    root=Path(root);grid=load(root/'grid.json');protocol=load(root/'protocol.json')
    # Root summarize checks provenance against root ledgers. Live rows are reflected
    # separately, without merging files that are still being appended by workers.
    summary=summarize(root,protocol,grid,read_jsonl(root/'results.jsonl'),terminal=terminal)
    reserves=load_reserves(root)
    child_results=[r for w in workers for r in snapshot_jsonl(Path(w)/'results.jsonl')]
    allrows=deduplicate([read_jsonl(root/'results.jsonl'),child_results],'id')
    allcalls=deduplicate([read_jsonl(root/'calls.jsonl')]+[snapshot_jsonl(Path(w)/'calls.jsonl') for w in workers],'id')
    allrequests=deduplicate([read_jsonl(root/'requests.jsonl')]+[snapshot_jsonl(Path(w)/'requests.jsonl') for w in workers],'id')
    judges=deduplicate([read_jsonl(root/'judgments.jsonl')]+[snapshot_jsonl(Path(w)/'judgments.jsonl') for w in workers],'result_id')
    judge_map={j['result_id']:j for j in judges};callmap={c['id']:c for c in allcalls}
    padded={r['id']:dict(r) for r in allrows}
    for row in padded.values():
        judge=judge_map.get(row['id'])
        if judge:
            row['judge']=judge['judgment']
            call=callmap.get(judge['call_id'],{})
            if valid_usage(call.get('usage')):row['actual_total_tokens']+=call['usage']['total_tokens']
    summary['methods']=_row_summary([padded.get(r['id'],{**r,'status':'not_run'}) for r in grid])
    summary.update(completed=len(allrows),not_run=len(grid)-len(allrows))
    known=sum(c['usage']['total_tokens'] for c in allcalls if valid_usage(c.get('usage')))
    pending=sorted({r['id'] for r in allrequests}-set(callmap))
    summary['resources']={'total_calls':len(allrequests),'total_tokens':known,
        'reserved_unknown_tokens':sum(reserves.values()),'admission_total_tokens':known+sum(reserves.values()),
        'input_tokens':sum(c['usage']['input_tokens'] for c in allcalls if valid_usage(c.get('usage'))),
        'output_tokens':sum(c['usage']['output_tokens'] for c in allcalls if valid_usage(c.get('usage'))),
        'pending_request_ids':pending,'unknown_usage_calls':len(pending)+sum(not valid_usage(c.get('usage')) for c in allcalls)}
    summary['resources']['unreserved_unknown_usage_calls']=len(pending)+sum(not valid_usage(c.get('usage')) and c['id'] not in reserves for c in allcalls)
    needed={r['id'] for r in allrows if r['kind']=='external'}
    valid={j['result_id'] for j in judges if isinstance(j.get('judgment',{}).get('correct'),bool)}
    summary.update(external_judges_needed=len(needed),external_judges_valid=len(needed & valid))
    summary['answer_conditions_complete']=len(allrows)==len(grid) and all(r.get('status')=='ok' for r in allrows) and needed<=valid
    summary['evaluation_complete']=summary['answer_conditions_complete'] and not summary['resources']['unknown_usage_calls']
    save_json(root/'summary.json',summary)
    stopping=any((Path(w)/'STOP_REQUESTED').exists() for w in workers)
    save_json(root/'run_state.json',{'status':'complete' if summary['evaluation_complete'] else 'stopped' if terminal else 'parallel_stopping' if stopping else 'parallel_running',
              'completed':len(allrows),'planned':len(grid),'resources':summary['resources'],'reason':terminal,
              'active_workers':active_workers,'segmentcounts':{Path(w).name:len(snapshot_jsonl(Path(w)/'results.jsonl')) for w in workers}})
    return summary


async def worker_main(args):
    # Credentials and model weights are accessed only in an explicitly invoked
    # worker subprocess, never on import, planning, unit testing, or dry run.
    from baseline.runtime import read_model_config
    from research.proxy_tokenizer import token_count, ENCODER
    from research.advanced_retrieval import DenseEncoder
    from research.review_upgrade import execute_grid
    directory=Path(args.run_dir).resolve()
    assignment=load(directory/'assignment.json') if not args.validate_only else None
    root=Path(assignment['root']) if assignment else directory
    protocol=load(directory/'protocol.json');encoder=DenseEncoder(download=False,threads=4)
    if encoder.identity!=protocol['encoder']:raise ValueError('Encoder identity changed')
    if assignment:
        check_reserve_hash(root,assignment)
        if file_digest(root/'protocol.json')!=assignment['root_protocol_hash']:raise ValueError('Root protocol changed')
        if file_digest(__file__)!=assignment['controller_hash']:raise ValueError('Controller source changed')
        if digest(load(directory/'grid.json'))!=assignment['grid_hash']:raise ValueError('Assignment grid changed')
        for name in ('dataset.json','external_protocol/tasks.json'):
            if file_digest(root/name)!=assignment['source_hashes'][name]:raise ValueError('Frozen task source changed')
    if args.validate_only and not (root/'STOP_REQUESTED').exists():raise ValueError('Preflight requires paused root STOP_REQUESTED')
    if digest(load(root/'dataset.json'))!=protocol['dataset_sha256']:raise ValueError('Synthetic dataset hash changed')
    config=read_model_config(args.config_dir)
    await execute_grid(directory,protocol,load(root/'dataset.json'),load(root/'external_protocol/tasks.json'),
                       load(directory/'grid.json'),config=config,count_tokens=token_count,tokenizer=ENCODER,encoder=encoder)
    save_json(directory/'parallel_preprocessing.json',{'identity':encoder.identity,'encoder_load_seconds':encoder.load_seconds,
              'encoder_seconds':encoder.encode_seconds,'encoded_texts':encoder.encoded_text_count})


def controller_main(args):
    root=Path(args.run_dir).resolve();plan=plan_run(root,args.workers,args.segments_name)
    if args.dry_run:
        print(json.dumps({k:v for k,v in plan.items() if k not in ('workers','completed_ids','source_hashes')} | {'completed':len(plan['completed_ids']),'workers':[
            {k:v for k,v in w.items() if k!='grid'} | {'pending_rows':len(w['grid'])} for w in plan['workers']]}));return
    if not (root/'STOP_REQUESTED').exists():raise ValueError('Pause the original process and create STOP_REQUESTED first')
    if (root/plan['segments_name']).exists():raise ValueError('Existing segments require reconciliation before a new launch')
    command=[sys.executable,'-m','research.parallel_upgrade','--worker']
    if args.config_dir:command+=['--config-dir',args.config_dir]
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    # The existing execution path validates all hashes, prompts and context before
    # honoring STOP_REQUESTED. This validator cannot start a new condition.
    with (root/'parallel_preflight.log').open('a',encoding='utf-8') as stream:
        subprocess.run(command+['--run-dir',str(root),'--validate-only'],stdout=stream,stderr=subprocess.STDOUT,
                       creationflags=flags,check=True)
    # Re-read after validation and require the root process to have remained idle.
    validated=plan_run(root,args.workers,args.segments_name)
    if validated!=plan:raise ValueError('Root changed during preflight; original process may still be running')
    paths=prepare_workers(root,plan);processes=[];streams=[];process_paths=[]
    try:
        for path,w in zip(paths,plan['workers']):
            if not w['grid'] or w['token_limit']<=RESERVE:continue
            stream=(path/'worker.log').open('a',encoding='utf-8');streams.append(stream)
            processes.append(subprocess.Popen(command+['--run-dir',str(path)],stdout=stream,stderr=subprocess.STDOUT,creationflags=flags))
            process_paths.append(path)
        while any(process.poll() is None for process in processes):
            stop_on_unknown(paths,active_inflight=True)
            # A terminated worker's pending requests can no longer be in flight.
            for process,path in zip(processes,process_paths):
                if process.poll() is not None and stop_on_unknown([path],active_inflight=False):
                    stop_all(paths,'An exited worker has unresolved spend')
            for path in paths:
                state_path=path/'run_state.json'
                if state_path.exists() and load(state_path).get('status')=='stopped':
                    if stop_on_unknown([path],active_inflight=False):stop_all(paths,'A stopped worker has unresolved spend')
            refresh_summary(root,paths,active_workers=sum(p.poll() is None for p in processes))
            time.sleep(args.poll_seconds)
        stop_on_unknown(paths,active_inflight=False)
        merge_segments(root,paths)
        failed=any(p.returncode for p in processes)
        final=refresh_summary(root)
        if not final['evaluation_complete']:
            if final['answer_conditions_complete'] and not final['resources']['unreserved_unknown_usage_calls']:
                reason=f"All answer conditions complete; {final['resources']['unknown_usage_calls']} historical usage records remain unreconciled under explicit admission holds"
            else:
                reason='Parallel workers stopped; pending conditions may resume sequentially' if not failed else 'Worker process failed; inspect segment logs before resume'
            refresh_summary(root,terminal=reason)
        from research.review_upgrade import report
        from research.upgrade_analysis import analyze_upgrade,write_analysis
        from research.claim_revision import build_claim_ledger,write_outputs
        report(root);write_analysis(analyze_upgrade(root),root);write_outputs(build_claim_ledger(root),root)
    except BaseException:
        stop_all(paths,'Controller stopped; reconcile before resuming')
        # Never kill an in-flight paid call; workers stop at condition boundaries.
        for process in processes:process.wait()
        raise
    finally:
        for stream in streams:stream.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',required=True);parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--dry-run',action='store_true');parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--validate-only',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--config-dir');parser.add_argument('--poll-seconds',type=float,default=10)
    parser.add_argument('--segments-name',default='segments')
    args=parser.parse_args()
    if not 0<args.poll_seconds<=60:parser.error('poll-seconds must be in (0, 60]')
    if args.validate_only and not args.worker:parser.error('--validate-only requires --worker')
    if args.worker:asyncio.run(worker_main(args))
    else:controller_main(args)


if __name__=='__main__':main()
