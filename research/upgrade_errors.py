"""Offline descriptive synthetic error partitions for the expanded frozen grid."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from research.error_analysis import _category, _counts
from research.jsonl_ledger import read_jsonl


def analyze_errors(run_dir):
    directory=Path(run_dir)
    grid=json.loads((directory/'grid.json').read_text(encoding='utf-8'))
    tasks={t['id']:t for t in json.loads((directory/'dataset.json').read_text(encoding='utf-8'))}
    rows=read_jsonl(directory/'results.jsonl');results={r['id']:r for r in rows}
    if len(results)!=len(rows):raise ValueError('Duplicate result')
    expected={g['id']:g for g in grid}
    if len(expected)!=len(grid) or set(results)-set(expected):raise ValueError('Invalid grid/result identity')
    fields=('cohort','phase','model','policy','packer','reader','budget','repeat')
    items=[];cases=[];groups=defaultdict(list)
    for condition in grid:
        if condition['kind']!='synthetic':continue
        task=tasks[condition['task_id']];row=results.get(condition['id'])
        if row and any(row.get(k)!=condition.get(k) for k in (*fields,'task_id')):
            raise ValueError('Result differs from grid')
        item={k:condition[k] for k in (*fields,'id','task_id')}
        item.update(family=task['family'],category=_category(row))
        items.append(item);groups[tuple(item[k] for k in (*fields,'family'))].append(item)
        if item['category']=='exact_correct':continue
        row=row or {};gold_ids={x for ids in task.get('gold_evidence',{}).values() for x in ids}
        cases.append({**item,'answer':row.get('answer'),'gold':task['gold'],'question':task['question'],
                      'score':row.get('score'),'selected_ids':row.get('selected_ids',[]),
                      'missing_evidence_ids':sorted(gold_ids-set(row.get('selected_ids',[])))})
    return {'schema_version':1,'overview':_counts(items),'cases':cases,
            'groups':[{**dict(zip((*fields,'family'),key)),**_counts(group)} for key,group in sorted(groups.items())],
            'excluded_external_rows':sum(g['kind']!='synthetic' for g in grid),
            'source_hashes':{n:hashlib.sha256((directory/n).read_bytes()).hexdigest() for n in ('grid.json','dataset.json','results.jsonl')},
            'new_model_calls':0,'limitations':[
                'Categories describe saved exactness and gold-evidence recall jointly; they do not establish causes.',
                'External session recall cannot establish answer-bearing passage completeness; external cases are excluded.',
                'Repeats, models, budgets and phases are separate groups; pooled overview counts conditions, not independent tasks.',
                'Missing, failed and invalid-score rows are excluded from scored denominators.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',required=True)
    args=parser.parse_args();directory=Path(args.run_dir);report=analyze_errors(directory)
    (directory/'error_analysis.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    lines=['# Expanded-study error partitions','','These are descriptive joint observations, not causal diagnoses.','']
    lines += ['- '+s for s in report['limitations']]
    lines += ['','| Model | Phase | Policy | Packer | Reader | Budget | Repeat | Family | Scored | Exact errors | Incomplete evidence | Complete evidence |',
              '|---|---|---|---|---|---:|---:|---|---:|---:|---:|---:|']
    for r in report['groups']:
        lines.append('| '+' | '.join(str(r[k]) for k in ('model','phase','policy','packer','reader','budget','repeat','family','scored_rows','exact_errors','retrieval_insufficient_errors','complete_evidence_errors'))+' |')
    (directory/'error_analysis_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':main()
