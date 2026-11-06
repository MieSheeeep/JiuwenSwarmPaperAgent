"""Bounded execution of a registered research experiment."""

import json
import argparse
import asyncio
from pathlib import Path

from research.artifacts import atomic_write, digest, save_json
from research.experiment_protocol import result_hash, validate_experiment_plan
from research.model_gateway import ModelGateway
from research.qa_dataset import generate_qa_tasks, score_answer, select_context


def _offline_config():
    return {'model': 'offline-test', 'provider': 'offline', 'api_base': 'offline', 'api_key': ''}


def _answer_text(output):
    try:
        value = json.loads(output)
        if isinstance(value, dict) and isinstance(value.get('answer'), str):
            return value['answer']
    except (TypeError, ValueError):
        pass
    return str(output).strip()


def _messages(task, context):
    passages = '\n'.join(f"[{p['id']}] {p['text']}" for p in context['passages'])
    return [
        {'role': 'system', 'content': 'Answer only with JSON: {"answer":"..."}. Use only supplied passages.'},
        {'role': 'user', 'content': json.dumps({'question': task['question'], 'passages': passages}, ensure_ascii=False)},
    ]


async def run_experiment(directory, plan, *, config=None, invoke=None, max_tasks=None, count_tokens=None):
    validate_experiment_plan(plan)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    tasks = generate_qa_tasks(plan['protocol']['tasks'], plan['protocol']['seed'])
    if max_tasks is not None:
        if type(max_tasks) is not int or not 1 <= max_tasks <= len(tasks):
            raise ValueError('max_tasks must be within the frozen task range')
        tasks = tasks[:max_tasks]
    config = config or _offline_config()
    count_tokens = count_tokens or (lambda text: len(text))
    gateway = ModelGateway(config, directory, max_total_tokens=plan['cost_controls']['max_total_tokens'],
                           max_calls=plan['cost_controls']['max_calls'], wall_seconds=900,
                           count_tokens=count_tokens)
    manifest = {'schema_version': 1, 'adapter': plan['adapter'], 'protocol': plan['protocol'],
                'plan_sha256': digest(plan), 'dataset_sha256': digest(tasks),
                'methods': plan['methods'], 'task_count': len(tasks)}
    save_json(directory / 'manifest.json', manifest)
    save_json(directory / 'plan.json', plan)
    (directory / 'dataset.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = []
    try:
        for task in tasks:
            for method in plan['methods']:
                context = select_context(task, method)
                response = await gateway.call(_messages(task, context),
                                              f"{task['id']}/{method}",
                                              max_tokens=plan['protocol']['answer_max_tokens'], invoke=invoke)
                answer = _answer_text(response['output'])
                score = score_answer(answer, task, context['selected_ids'])
                row = {'task_id': task['id'], 'method': method, 'answer': answer,
                       'selected_ids': context['selected_ids'],
                       'context_sha256': digest(context['passages']), 'call_ids': [response['id']],
                       'provider_tokens': response['usage']['total_tokens'], 'score': score,
                       'status': 'ok'}
                row['result_hash'] = result_hash(row)
                with (directory / 'results.jsonl').open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(row, ensure_ascii=False) + '\n')
                    stream.flush()
                rows.append(row)
        summary = _summarize(rows, plan['methods'])
        save_json(directory / 'summary.json', summary)
        state = {'status': 'completed', 'resources': gateway.totals(), 'rows': len(rows),
                 'manifest_sha256': digest(manifest)}
        save_json(directory / 'state.json', state)
        return state | summary
    except Exception as error:
        save_json(directory / 'state.json', {'status': 'stopped', 'error_type': type(error).__name__,
                                             'reason': str(error), 'resources': gateway.totals(), 'rows': len(rows)})
        raise


def _summarize(rows, methods):
    by_method = {}
    for method in methods:
        subset = [row for row in rows if row['method'] == method]
        by_method[method] = {
            'rows': len(subset),
            'exact_accuracy': sum(row['score']['exact'] for row in subset) / len(subset) if subset else 0.0,
            'evidence_recall': sum(row['score']['evidence_recall'] for row in subset) / len(subset) if subset else 0.0,
            'mean_context_passages': sum(row['score']['context_passages'] for row in subset) / len(subset) if subset else 0.0,
            'provider_tokens': sum(row['provider_tokens'] for row in subset),
        }
    return {'methods': list(methods), 'by_method': by_method, 'row_count': len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--config-dir')
    parser.add_argument('--max-total-tokens', type=int, default=20000)
    parser.add_argument('--max-calls', type=int, default=36)
    args = parser.parse_args()
    from baseline.runtime import read_model_config, token_count
    from research.experiment_protocol import ADAPTIVE_QA_PROTOCOL
    plan = {'adapter': 'adaptive-qa-v1', 'protocol': dict(ADAPTIVE_QA_PROTOCOL),
            'candidate_id': 'qa-stop', 'source_ids': ['literature:adaptive-retrieval', 'literature:multi-hop-qa'],
            'data_split': {'train': 0, 'test': 12, 'seed': ADAPTIVE_QA_PROTOCOL['seed']},
            'baselines': ['single_pass', 'fixed_two_passages'], 'methods': list(ADAPTIVE_QA_PROTOCOL['methods']),
            'metrics': ['exact_accuracy', 'evidence_recall', 'context_passages', 'provider_tokens'],
            'falsification': 'adaptive_stop does not improve exact accuracy at lower context cost',
            'cost_controls': {'max_total_tokens': args.max_total_tokens, 'max_calls': args.max_calls},
            'analysis': 'paired task-level comparison', 'ablations': ['remove adaptive stopping']}
    config = read_model_config(args.config_dir)
    result = asyncio.run(run_experiment(args.output, plan, config=config, count_tokens=token_count))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
