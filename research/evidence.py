"""Recompute historical evidence from raw answers, labels and provider logs."""
import hashlib
import json
import math
from pathlib import Path

from baseline.dataset import score_answer
from research.artifacts import create_artifact, file_digest

SOURCE_FILES = ('dataset.json', 'manifest.json', 'results.jsonl', 'calls.jsonl')
TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'total_tokens')


def source_hashes(source):
    return {name: file_digest(Path(source) / name) for name in SOURCE_FILES}


def wilson(correct, count):
    z = 1.95996398454
    p = correct / count
    denominator = 1 + z * z / count
    center = (p + z * z / (2 * count)) / denominator
    half = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return [max(0, center - half), min(1, center + half)]


def import_baseline(source):
    source = Path(source)
    blobs = {name: (source / name).read_bytes() for name in SOURCE_FILES}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in blobs.items()}
    # Legacy run.py hashes text before Windows translates LF into CRLF.
    dataset_text = blobs['dataset.json'].decode('utf-8').replace('\r\n', '\n')
    tasks = json.loads(dataset_text)
    manifest = json.loads(blobs['manifest.json'])
    if not isinstance(manifest, dict):
        raise ValueError('manifest must be a JSON object')
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('dataset must contain a nonempty task list')
    if hashlib.sha256(dataset_text.encode('utf-8')).hexdigest() != manifest.get('dataset_sha256'):
        raise ValueError('dataset text digest does not match legacy manifest')
    rows = [json.loads(line) for line in blobs['results.jsonl'].decode('utf-8').splitlines() if line.strip()]
    calls = [json.loads(line) for line in blobs['calls.jsonl'].decode('utf-8').splitlines() if line.strip()]
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get('id'), str) or not task['id']:
            raise ValueError('Invalid task record or task ID')
        gold = task.get('gold')
        if not isinstance(gold, dict) or set(gold) != {'port', 'timeout', 'owner'}:
            raise ValueError('Invalid task gold fields')
        if any(gold[key] is not None and type(gold[key]) is not int for key in ('port', 'timeout')):
            raise ValueError('Invalid task numeric gold types')
        if gold['owner'] is not None and not isinstance(gold['owner'], str):
            raise ValueError('Invalid task owner gold type')
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('answer'), str):
            raise ValueError('Invalid result record: answer must be text')
        if (not isinstance(row.get('task_id'), str) or not isinstance(row.get('policy'), str) or
                not isinstance(row.get('call_ids'), list) or not row['call_ids'] or
                not all(isinstance(call_id, str) and call_id for call_id in row['call_ids'])):
            raise ValueError('Invalid result task-policy or call association fields')
    for call in calls:
        if (not isinstance(call, dict) or not isinstance(call.get('id'), str) or not call['id'] or
                not isinstance(call.get('tag'), str) or not isinstance(call.get('output'), str)):
            raise ValueError('Invalid call record, tag or output')
    policies = manifest.get('policies')
    if (not isinstance(policies, list) or not policies or not all(isinstance(p, str) for p in policies)
            or len(set(policies)) != len(policies)):
        raise ValueError('Invalid policies')
    if set(policies) - {'full', 'recent', 'retrieve', 'retrieve_summary'}:
        raise ValueError('Unsupported historical policy')
    task_map = {t['id']: t for t in tasks}
    if len(task_map) != len(tasks) or type(manifest.get('tasks')) is not int or manifest['tasks'] != len(tasks):
        raise ValueError('Invalid dataset task count or duplicate task IDs')
    expected_pairs = {(task_id, policy) for task_id in task_map for policy in policies}
    actual_pairs = [(r['task_id'], r['policy']) for r in rows]
    if len(actual_pairs) != len(expected_pairs) or set(actual_pairs) != expected_pairs:
        raise ValueError('Incomplete or duplicate task-policy pairs')
    call_map = {c['id']: c for c in calls}
    associated = [call_id for row in rows for call_id in row['call_ids']]
    if len(call_map) != len(calls) or len(set(associated)) != len(associated) or set(associated) != set(call_map):
        raise ValueError('Orphan, duplicate or missing call association')
    model_id = manifest.get('model')
    if not isinstance(model_id, str) or not model_id:
        raise ValueError('Missing model ID')
    for call in calls:
        usage = call.get('usage')
        if not isinstance(usage, dict) or any(type(usage.get(key)) is not int or usage[key] < 0 for key in TOKEN_FIELDS):
            raise ValueError(f"Missing or invalid API usage for {call['id']}")
        if usage['input_tokens'] + usage['output_tokens'] != usage['total_tokens']:
            raise ValueError('API usage totals do not reconcile')
        if call.get('model') != model_id or call.get('status') != 'ok':
            raise ValueError('Historical milestone requires successful calls from the declared model')
    for row in rows:
        if row.get('status') != 'ok':
            raise ValueError('Historical milestone requires completed successful result rows')
        recomputed = score_answer(row['answer'], task_map[row['task_id']]['gold'])
        if recomputed != row.get('score'):
            raise ValueError(f"Saved score disagrees with answer and gold: {row['task_id']}/{row['policy']}")
        linked = [call_map[call_id] for call_id in row['call_ids']]
        prefix = f"{row['task_id']}/{row['policy']}/"
        expected_steps = ['summary', 'answer'] if row['policy'] == 'retrieve_summary' else ['answer']
        if [call['tag'] for call in linked] != [prefix + step for step in expected_steps]:
            raise ValueError('Call association has wrong task, policy or step sequence')
        if row['answer'] != linked[-1].get('output'):
            raise ValueError('Result answer disagrees with logged API response')
        elapsed = row.get('elapsed_seconds')
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('Invalid elapsed time')
    metadata_keys = ('seed', 'history_budget_proxy_tokens', 'summary_budget_proxy_tokens',
                     'tokenizer_proxy', 'temperature', 'top_p', 'thinking',
                     'answer_max_tokens', 'summary_max_tokens')
    run = create_artifact('RunManifest', {
        'origin': 'historical_baseline', 'source_files': hashes,
        'source_directory': str(source.resolve()), 'model_id': model_id,
        'task_count': len(tasks), 'policies': policies, 'call_ids': sorted(call_map),
        'code_revision': None, 'historical_code_provenance': 'Not recorded by original manifest; cannot reconstruct from current HEAD.',
        'scorer_sha256': file_digest(Path(__file__).resolve().parents[1] / 'baseline/dataset.py'),
        'configuration': {key: manifest[key] for key in metadata_keys if key in manifest},
        'dataset_text_sha256': manifest['dataset_sha256'],
        'result_refs': [{'task_id': r['task_id'], 'policy': r['policy'], 'call_ids': r['call_ids']} for r in rows],
    })
    metrics = []
    for policy in policies:
        selected = [r for r in rows if r['policy'] == policy]
        used = [call_map[call_id] for row in selected for call_id in row['call_ids']]
        correct = sum(score_answer(r['answer'], task_map[r['task_id']]['gold'])['exact'] for r in selected)
        total_tokens = sum(c['usage']['total_tokens'] for c in used)
        metrics.append({'policy': policy, 'tasks': len(selected), 'correct': correct,
                        'exact_accuracy': correct / len(selected), 'wilson_95': wilson(correct, len(selected)),
                        'api_calls': len(used), 'total_tokens': total_tokens,
                        'input_tokens': sum(c['usage']['input_tokens'] for c in used),
                        'output_tokens': sum(c['usage']['output_tokens'] for c in used),
                        'mean_tokens_per_task': total_tokens / len(selected),
                        'mean_seconds_per_task': sum(r['elapsed_seconds'] for r in selected) / len(selected),
                        'call_ids': [c['id'] for c in used],
                        'run_id': run['artifact_id']})
    evidence = create_artifact('EvidenceBundle', {
        'origin': 'historical_baseline', 'metrics': metrics,
        'total_api_calls': len(calls), 'total_api_tokens': sum(m['total_tokens'] for m in metrics),
        'limitations': ['Historical synthetic pilot, not a new method evaluation or competition score.',
                        'Exact identifier matching favors lexical retrieval; no held-out generalization test.',
                        'Full history is an unbounded reference; nominal intervals do not establish equivalence.',
                        'Original run code revision was not recorded; hashes prove local consistency, not authenticity.'],
        'resource_accounting': {
            'scope': 'All answer and summary calls in this historical experiment.',
            'usage_source': 'API-reported input_tokens/output_tokens/total_tokens',
            'currency_cost': None, 'currency_cost_reason': 'No dated pricing evidence supplied; zero-valued SDK cost fields are not invoices.',
            'new_pipeline_model_calls': 0, 'new_pipeline_api_tokens': 0,
            'excluded': ['Original draft-writing calls', 'Original smoke-test calls'],
        },
    }, [run['artifact_id']])
    return run, evidence
