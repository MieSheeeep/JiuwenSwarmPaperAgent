"""Dated-price cost bounds over actual runtime usage, never SDK zero-cost fields."""
from collections import defaultdict
import json
from pathlib import Path

from research.jsonl_ledger import read_jsonl
from research.artifacts import save_json,file_digest


def estimate_cost(calls,pricing):
    groups=defaultdict(lambda:{'calls':0,'input_tokens':0,'cached_input_tokens':0,'output_tokens':0,'usd_lower':0.,'usd_upper':0.})
    unknown=[]
    for call in calls:
        usage=call.get('usage') or {};model=call.get('model')
        if model not in pricing['rates'] or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('input_tokens','output_tokens')):
            unknown.append(call.get('id'));continue
        inputs,outputs=usage['input_tokens'],usage['output_tokens'];cache=usage.get('cache_tokens')
        cache_known=type(cache) is int and 0<=cache<=inputs
        cached_min=cache if cache_known else 0;cached_max=cache if cache_known else inputs
        rates=pricing['rates'][model];off=rates['off_peak'];peak=rates['peak']
        low=(cached_max*off['input_cached']+(inputs-cached_max)*off['input_uncached']+outputs*off['output'])/1e6
        high=(cached_min*peak['input_cached']+(inputs-cached_min)*peak['input_uncached']+outputs*peak['output'])/1e6
        group=groups[model];group['calls']+=1;group['input_tokens']+=inputs;group['cached_input_tokens']+=cache if cache_known else 0;group['output_tokens']+=outputs;group['usd_lower']+=low;group['usd_upper']+=high
    return {'currency':'USD','usd_lower':sum(x['usd_lower'] for x in groups.values()),'usd_upper':sum(x['usd_upper'] for x in groups.values()),
            'per_model':dict(groups),'unpriced_call_ids':unknown,'is_invoice':False,
            'scope':'Known SDK-reported token/cache usage at dated public rate bounds; unknown calls excluded, not free. No peak-hour or holiday assumption.',
            'pricing_source':pricing['source'],'pricing_date':pricing['checked_date']}


def write_resource_report(run):
    run=Path(run);root=Path(__file__).resolve().parents[1]
    pricepath=root/'sources/deepseek_pricing_20261106.json';pricing=json.loads(pricepath.read_text(encoding='utf-8'))
    experiment=read_jsonl(run/'calls.jsonl');writing=read_jsonl(run/'writing_ledger/calls.jsonl');calls=experiment+writing
    protocol=json.loads((run/'protocol.json').read_text(encoding='utf-8'))
    result={'scope':'Recorded research runtime API usage; excludes coding assistant, web/search and whole-machine energy.',
            'token_limit':protocol['token_limit'],'known_api_tokens':sum(c['usage']['total_tokens'] for c in calls if c.get('usage')),
            'api_calls':len(calls),'unknown_usage_calls':sum(not bool(c.get('usage')) for c in calls),
            'experiment_calls':len(experiment),'writing_calls':len(writing),'cost_estimate':estimate_cost(calls,pricing),
            'pricing_snapshot_sha256':file_digest(pricepath),'upstream_pr_status':'No PR or merge claimed'}
    from research.spend_reservation import load_reserves
    reserves=load_reserves(run)
    result['reserved_unknown_tokens']=sum(reserves.values())
    result['admission_total_tokens']=result['known_api_tokens']+sum(reserves.values())
    result['admission_within_limit']=result['admission_total_tokens']<=protocol['token_limit']
    result['reservation_note']='Conservative admission holds are not provider-reported usage or invoice amounts; unresolved calls remain unpriced.'
    local=[]
    for path in sorted(run.glob('segments*/*/parallel_preprocessing.json')):
        local.append({'artifact':str(path.relative_to(run)),'sha256':file_digest(path),
                      'measurements':json.loads(path.read_text(encoding='utf-8'))})
    hardware=run/'local_resources.json';audit=run/'retrieval_audit_summary.json'
    result['local_resources']={
        'hardware_snapshot':json.loads(hardware.read_text(encoding='utf-8')) if hardware.exists() else None,
        'reported_embedding_segments':local,
        'retrieval_audit':json.loads(audit.read_text(encoding='utf-8')) if audit.exists() else None,
        'summed_api_elapsed_seconds':sum(c.get('elapsed_seconds',0) for c in calls),
        'scope':'Reported CPU segments and pre-run hardware availability only. Summed API latency is not parallel wall time; preflight/restart CPU and peak RAM/energy are not fully measured.'}
    save_json(run/'resource_report.json',result);return result
