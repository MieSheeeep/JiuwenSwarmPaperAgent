"""Complete local retrieval audit; oracle labels are used only after selection."""
from collections import defaultdict
import json
from pathlib import Path
import statistics
import time

from research.artifacts import digest, save_json
from research.memory_dataset import score_memory_answer
from research.model_gateway import append_durable, read_jsonl


def audit_retrieval(directory,tasks,variants,encoder,count_tokens,frozen):
    from research.advanced_retrieval import select_records
    directory=Path(directory);target=directory/'retrieval_audit.jsonl'
    identity=digest({'tasks':tasks,'variants':variants,'encoder':encoder.identity,'budgets':[128,256,512]})
    metadata=directory/'retrieval_audit_summary.json'
    if metadata.exists():
        previous=json.loads(metadata.read_text(encoding='utf-8'))
        if previous.get('identity')!=identity:raise ValueError('Retrieval audit input changed')
        if previous.get('rows_sha256')!=digest(read_jsonl(target)):raise ValueError('Retrieval audit changed')
        return previous
    rows=read_jsonl(target);seen={(r['task_id'],r['policy'],r['packer'],r['budget']) for r in rows}
    started=time.perf_counter()
    for task in tasks:
        for policy,packer in variants:
            for budget in (128,256,512):
                key=(task['id'],policy,packer,budget)
                if key in seen:continue
                begin=time.perf_counter()
                query={**task['query'],'question':task['question']}
                if policy in ('full','recent','no_time','no_conflict'):
                    selection=frozen.select_records(task['records'],query,policy,budget,count_tokens)
                else:
                    selection=select_records(task['records'],query,policy,budget,count_tokens,encoder=encoder,packer=packer)
                score=score_memory_answer('{}',task,selection['record_ids'])
                row={'task_id':task['id'],'split':task['split'],'family':task['family'],'source_seed':task['source_seed'],
                     'policy':policy,'packer':packer,'budget':budget,'proxy_tokens':selection['proxy_tokens'],
                     'evidence_recall':score['evidence_recall'],'selected_ids':selection['record_ids'],
                     'context_hash':digest(selection['text']),'elapsed_seconds':time.perf_counter()-begin,
                     'packing':selection.get('metadata',{})}
                rows.append(row);append_durable(target,row);seen.add(key)
        if len(seen)%300==0:print(json.dumps({'offline_retrieval_conditions':len(seen)}),flush=True)
    groups=defaultdict(list)
    for row in rows:groups[tuple(row[k] for k in ('split','family','policy','packer','budget'))].append(row)
    summary={'identity':identity,'complete':len(rows)==len(tasks)*len(variants)*3,
             'planned':len(tasks)*len(variants)*3,'completed':len(rows),'new_model_calls':0,
             'wall_seconds_this_invocation':time.perf_counter()-started,'encoder_seconds':encoder.encode_seconds,
             'rows_sha256':digest(rows),'methods':[{**dict(zip(('split','family','policy','packer','budget'),key)),
                        'tasks':len(group),'mean_evidence_recall':statistics.mean(r['evidence_recall'] for r in group),
                        'mean_context_proxy_tokens':statistics.mean(r['proxy_tokens'] for r in group),
                        'mean_selection_seconds':statistics.mean(r['elapsed_seconds'] for r in group)} for key,group in sorted(groups.items())],
             'limits':['Source record availability is not answer correctness or citation faithfulness.',
                       'Full history is unbounded; all other policies are rechecked against actual joined proxy tokens.',
                       'DP optimizes the documented additive surrogate, not arbitrary-tokenizer global optimality.']}
    save_json(metadata,summary);return summary
