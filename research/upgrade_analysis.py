"""Predeclared, offline matched-task diagnostics for the fresh upgrade run."""
from __future__ import annotations
import argparse
from collections import defaultdict
from itertools import combinations
import json
import math
from pathlib import Path
import random

from research.artifacts import digest, file_digest
from research.jsonl_ledger import read_jsonl

DIMS = ('kind', 'split', 'model', 'policy', 'packer', 'reader', 'budget', 'repeat', 'phase', 'cohort')
FAMILIES = ('reader', 'conflict_selection', 'retrieval', 'packing', 'model', 'budget')
BOOTSTRAP_SEED = 20261106


def _jsonl(path):
    return read_jsonl(path)


def paired_statistics(pairs, resamples=1000, seed=BOOTSTRAP_SEED):
    """One (unique task id, left correctness, right correctness) per unit."""
    if len({p[0] for p in pairs}) != len(pairs):
        raise ValueError('Repeated task units in paired analysis')
    if any(a not in (0, 1, False, True) or b not in (0, 1, False, True) for _, a, b in pairs):
        raise ValueError('Paired outcomes must be binary')
    pairs = sorted(pairs)
    n = len(pairs)
    b = sum(bool(a) and not bool(c) for _, a, c in pairs)
    c = sum(bool(v) and not bool(a) for _, a, v in pairs)
    discordant = b+c
    p = min(1., 2 * sum(math.comb(discordant, k) for k in range(min(b,c)+1)) / (1 << discordant)) if n else None
    deltas = [int(a)-int(b) for _, a, b in pairs]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(deltas) for _ in range(n))/n for _ in range(resamples)) if n else []
    ids = [p[0] for p in pairs]
    return dict(n_paired=n, task_ids=ids, task_ids_hash=digest(ids),
                left_correct=sum(int(a) for _, a, _ in pairs), right_correct=sum(int(b) for _, _, b in pairs),
                left_only_correct=b, right_only_correct=c, discordant=discordant,
                both_correct=sum(bool(a) and bool(b) for _, a, b in pairs),
                both_wrong=sum(not bool(a) and not bool(b) for _, a, b in pairs),
                difference_left_minus_right=sum(deltas)/n if n else None,
                mcnemar_exact_p=p,
                descriptive_task_bootstrap_95=[means[int(.025*(resamples-1))], means[int(.975*(resamples-1))]] if means else None,
                bootstrap_resamples=resamples, bootstrap_seed=seed)


def holm_adjust(pvalues):
    """Holm step-down; None hypotheses still count in the predeclared family size."""
    result = [None]*len(pvalues)
    running = 0.
    for rank, (index, p) in enumerate(sorted(((i,p) for i,p in enumerate(pvalues) if p is not None), key=lambda x:x[1])):
        running = max(running, min(1., (len(pvalues)-rank)*p))
        result[index] = running
    return result


def _unique(rows, label):
    result = {}
    for row in rows:
        if row['id'] in result:
            raise ValueError(f'Duplicate {label} id')
        result[row['id']] = row
    return result


def _judge_values(directory, results, calls):
    judgments = _jsonl(directory/'judgments.jsonl')
    counts = defaultdict(int)
    for item in judgments:
        counts[item.get('result_id')] += 1
    values, excluded = {}, []
    for item in judgments:
        rid = item.get('result_id')
        try:
            if counts[rid] != 1: raise ValueError('Duplicate judgment result id')
            if rid not in results or results[rid]['kind'] != 'external': raise ValueError('Unknown/non-external judged result')
            if item.get('record_hash') != digest({k:v for k,v in item.items() if k!='record_hash'}):
                raise ValueError('Judgment hash mismatch')
            call = calls[item['call_id']]
            parsed = json.loads(call['output'])
            if parsed != item['judgment'] or call['model'] != item['judge_model']:
                raise ValueError('Judge response/model mismatch')
            tag = call.get('tag', call.get('logical_key'))
            if tag is not None and tag != f'upgrade/{rid}/judge': raise ValueError('Judge call belongs to another result')
            if call.get('status', 'ok') != 'ok' or not isinstance(parsed.get('correct'), bool):
                raise ValueError('Missing/invalid boolean judge outcome')
            values[rid] = int(parsed['correct'])
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            excluded.append({'result_id': rid, 'reason': str(exc)})
    for rid, row in results.items():
        if row['kind']=='external' and row.get('status')=='ok' and rid not in values:
            excluded.append({'result_id':rid, 'reason':'No valid independent judge; excluded, never counted wrong.'})
    return values, excluded


def _cohort(row):
    if row.get('cohort'):
        return row['cohort']
    if row['kind']=='external': return 'external_unassigned'
    return 'synthetic_packing' if row.get('family')=='packing_stress' else 'synthetic_controlled'


def _metric(row, metric, judges):
    if not row or row.get('status')!='ok': return None
    if metric=='external_judge_proxy': return judges.get(row['id'])
    value = row.get('score',{}).get('exact')
    return int(value) if isinstance(value,bool) or type(value) is int and value in (0,1) else None


def _compare(family, dimension, left, right, group, mapped, judges, metric, metadata):
    lhs = {r['task_id']:r for r in group if r[dimension]==left}
    rhs = {r['task_id']:r for r in group if r[dimension]==right}
    planned = sorted(lhs.keys() & rhs.keys())
    pairs, exclusions = [], []
    for task_id in planned:
        a = _metric(mapped.get(lhs[task_id]['id']), metric, judges)
        b = _metric(mapped.get(rhs[task_id]['id']), metric, judges)
        if a is None or b is None:
            exclusions.append(task_id)
        else:
            pairs.append((task_id,a,b))
    output = dict(family=family, varying_dimension=dimension, left=left, right=right, metric=metric,
                  condition=metadata, planned_paired=len(planned), planned_task_ids_hash=digest(planned),
                  excluded_missing_or_invalid=exclusions, unmatched_left=sorted(lhs.keys()-rhs.keys()),
                  unmatched_right=sorted(rhs.keys()-lhs.keys()), **paired_statistics(pairs))
    output['status'] = 'not_run' if not pairs else 'partial' if len(pairs)<len(planned) else 'complete_matched'
    output['strata'] = {}
    for key in ('family','source_seed'):
        strata = defaultdict(list)
        for pair in pairs:
            strata[str(lhs[pair[0]].get(key, 'unknown'))].append(pair)
        output['strata'][key] = {value:dict(n_paired=len(items), difference_left_minus_right=sum(a-b for _,a,b in items)/len(items))
                                for value,items in sorted(strata.items())}
    return output


def analyze_upgrade(run_dir):
    directory = Path(run_dir).resolve()
    grid = json.loads((directory/'grid.json').read_text(encoding='utf-8'))
    planned = _unique(grid,'planned')
    results = _unique(_jsonl(directory/'results.jsonl'),'result')
    calls = _unique(_jsonl(directory/'calls.jsonl'),'call')
    units = set()
    for item in grid:
        unit = (item['task_id'],)+tuple(item.get(k, _cohort(item) if k=='cohort' else None) for k in DIMS)
        if unit in units: raise ValueError('Duplicate task within the same planned condition')
        units.add(unit)
    for rid, row in results.items():
        if rid not in planned or any(row.get(k)!=v for k,v in planned[rid].items()):
            raise ValueError('Unplanned or changed result condition')
        if row.get('result_hash') is not None and row['result_hash']!=digest({k:v for k,v in row.items() if k!='result_hash'}):
            raise ValueError('Result hash mismatch')
    judges, judge_exclusions = _judge_values(directory,results,calls)
    dataset_path = directory/'dataset.json'
    dataset = json.loads(dataset_path.read_text(encoding='utf-8')) if dataset_path.exists() else []
    lookup = {t['id']:t for t in dataset} if isinstance(dataset,list) else {}
    primary = []
    for item in grid:
        row = dict(item, cohort=_cohort(item))
        if row.get('source_seed') is None:
            row['source_seed'] = lookup.get(row['task_id'],{}).get('source_seed', results.get(row['id'],{}).get('source_seed'))
        if row.get('repeat',0)==0 and row.get('split')=='test': primary.append(row)
    # Matched external membership is fixed by planned coverage, never successes.
    external = [r for r in primary if r['kind']=='external']
    models = sorted({r['model'] for r in external})
    coverage = defaultdict(set)
    for r in external: coverage[r['task_id']].add((r['model'],r['policy']))
    required = {(m,p) for m in models for p in ('bm25','dense','hybrid')}
    matched_ids = {t for t,have in coverage.items() if len(models)>=2 and required<=have}
    for row in primary:
        if row['kind']=='external':
            row['cohort'] = 'external_matched' if row['task_id'] in matched_ids else 'external_extension'
    contrasts = []
    specs = [('reader','reader','conflict_aware','baseline'),
             ('conflict_selection','policy','versioned','no_conflict'),
             ('retrieval','policy','bm25','dense'),('retrieval','policy','bm25','hybrid'),
             ('packing','packer','smaller_first','utility_dp'),('packing','packer','smaller_first','diverse')]
    all_models = sorted({r['model'] for r in primary})
    specs += [('model','model',a,b) for a,b in combinations(all_models,2)]
    specs += [('budget','budget',a,b) for a,b in ((128,256),(256,512),(128,512))]
    for family, dimension, left, right in specs:
        grouped = defaultdict(list)
        for row in primary:
            if row[dimension] not in (left,right): continue
            if row['kind']=='external' and row['cohort']!='external_matched': continue
            if family=='packing' and (row['cohort']!='synthetic_packing' or row['policy']!='versioned'): continue
            condition = {k:row.get(k) for k in DIMS if k not in (dimension,'repeat')}
            # Only these named bridges are allowed across phase allocations.
            if family=='budget' and row['kind']=='synthetic' and row['phase'] in ('mechanism','budget'):
                condition['phase']='mechanism_budget_bridge'
            grouped[json.dumps(condition,sort_keys=True)].append(row)
        for condition, group in sorted(grouped.items()):
            levels = {r[dimension] for r in group}
            if not {left,right} <= levels: continue
            metrics = ('normalized_exact_proxy','external_judge_proxy') if group[0]['kind']=='external' else ('exact',)
            for metric in metrics:
                contrasts.append(_compare(family,dimension,left,right,group,results,judges,metric,json.loads(condition)))
    for family in FAMILIES:
        for metric in ('exact','normalized_exact_proxy','external_judge_proxy'):
            selected = [r for r in contrasts if r['family']==family and r['metric']==metric]
            adjusted = holm_adjust([r['mcnemar_exact_p'] for r in selected])
            for row, value in zip(selected,adjusted):
                row.update(holm_adjusted_p=value, holm_family=f'{family}/{metric}', holm_family_size=len(selected),
                           inferential_assumptions_verified=False, significance_claim_permitted=False)
    repeats = []
    for row in grid:
        if row.get('repeat',0)==0: continue
        candidates = [p for p in primary if p['task_id']==row['task_id'] and
                      all(p.get(k)==row.get(k) for k in ('kind','split','model','policy','packer','reader','budget')) and
                      (p['phase']==row['phase'] or p['phase']=='mechanism' and row['phase']=='repeat')]
        if len(candidates)>1: raise ValueError('Ambiguous primary counterpart for repeat')
        p = candidates[0] if candidates else None
        a = _metric(results.get(p['id']) if p else None,'exact',judges)
        b = _metric(results.get(row['id']),'exact',judges)
        repeats.append({'task_id':row['task_id'],'repeat':row['repeat'],'result_id':row['id'],
                        'primary_result_id':p['id'] if p else None,'n_paired':int(a is not None and b is not None),
                        'exact_agreement':int(a==b) if a is not None and b is not None else None,
                        'status':'paired_repeat_diagnostic' if a is not None and b is not None else 'not_run'})
    cohort_summaries = []
    for name in sorted({r['cohort'] for r in primary} | {'external_full500_hybrid_flash'}):
        group = [r for r in primary if r['cohort']==name]
        if name=='external_full500_hybrid_flash':
            flash = next((m for m in models if 'flash' in m.casefold()),models[0] if models else None)
            group = [r for r in primary if r['kind']=='external' and r['model']==flash and r['policy']=='hybrid']
        task_ids = sorted({r['task_id'] for r in group})
        observed = [results[r['id']] for r in group if r['id'] in results and results[r['id']].get('status')=='ok']
        cohort_summaries.append({'cohort':name,'planned_unique_tasks':len(task_ids),'task_ids_hash':digest(task_ids),
                                 'planned_rows':len(group),'completed_rows':len(observed),
                                 'status':'not_run' if not observed else 'partial' if len(observed)<len(group) else 'complete',
                                 'scope':'Descriptive coverage only; full hybrid-Flash cohort is never pooled into matched-retriever contrasts.'})
    return {'schema_version':1,'run_directory':str(directory),'analysis_protocol':'predeclared-matched-task-v1',
            'source_hashes':{p.name:file_digest(p) for p in [directory/n for n in ('grid.json','results.jsonl','judgments.jsonl','calls.jsonl','dataset.json')] if p.exists()},
            'primary_repeat':0,'contrasts':contrasts,'repeat_consistency':repeats,'cohorts':cohort_summaries,
            'judge_exclusions':judge_exclusions,
            'contrast_family_status':{f:('not_planned_in_grid' if not any(r['family']==f for r in contrasts) else
                                          'not_run' if not any(r['family']==f and r['n_paired'] for r in contrasts) else
                                          'partial' if any(r['family']==f and r['status']!='complete_matched' for r in contrasts) else
                                          'complete_matched') for f in FAMILIES},
            'assumptions':['McNemar exact binomial p assumes independent task-pair discordance and exchangeability under the null.',
                           'Synthetic cases share generators, families and seeds; external questions can share conversation histories. Independence is unverified.',
                           'Bootstrap intervals resample matched task IDs, never repeated calls; they are descriptive and unadjusted.',
                           'Holm adjustment is separate per contrast family and metric and counts unrun hypotheses; it does not correct all exploratory subgroup analyses.',
                           'Only paired completed valid outcomes enter denominators; missing/invalid outcomes are excluded, not scored as incorrect.',
                           'External normalized exact and adapted model-judge outcomes are separate proxies, neither official LongMemEval accuracy.',
                           'Repeat calls are consistency diagnostics, not independent provider seeds or extra sample units.'],
            'significance_claim_permitted':False}


def write_analysis(analysis, output):
    output = Path(output); output.mkdir(parents=True,exist_ok=True)
    (output/'analysis.json').write_text(json.dumps(analysis,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# Matched-cohort upgrade analysis','','All p-values and intervals are diagnostics. Inferential assumptions remain unverified; no significance claim is granted.','']
    lines += ['- '+s for s in analysis['assumptions']]
    lines += ['', '| Family | Metric | Left vs right | Paired tasks | Left-only / right-only | Difference | Exact p | Holm p | Status |',
              '| --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |']
    for r in analysis['contrasts']:
        lines.append(f"| {r['family']} | {r['metric']} | {r['left']} vs {r['right']} | {r['n_paired']} | {r['left_only_correct']} / {r['right_only_correct']} | {r['difference_left_minus_right']} | {r['mcnemar_exact_p']} | {r['holm_adjusted_p']} | {r['status']} |")
    lines += ['', 'Full conditions, task identities/hashes, exclusions, strata, coverage and repeat diagnostics are recorded in analysis.json.']
    (output/'analysis_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();write_analysis(analyze_upgrade(args.run_dir),args.output)


if __name__=='__main__': main()
