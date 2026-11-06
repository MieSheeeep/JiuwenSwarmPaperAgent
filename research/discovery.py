"""Source-linked literature → question → experiment, with bounded model calls."""
import argparse
import asyncio
import json
from pathlib import Path

from research.artifacts import digest, file_digest, save_json, atomic_write, create_artifact
from research.literature import ArxivClient
from research.model_gateway import ModelGateway

SKILLS = Path(__file__).with_name('skills')
STAGES = ('literature_review', 'question_formulation', 'experiment_design')
MEMORY_PROTOCOL = {
    'dataset': 'synthetic-bitemporal-v1', 'dev_seeds': [101], 'test_seeds': [1729, 2718],
    'dev_tasks': 6, 'test_tasks': 24, 'sensitivity_tasks': 12,
    'main_budget': 256, 'sensitivity_budget': 512,
    'policies': ['full', 'recent', 'lexical', 'bm25', 'versioned', 'no_time', 'no_conflict', 'lexical_summary'],
    'full_reference': 'unbounded', 'answer_max_tokens': 160, 'summary_max_tokens': 256}
PLAN_EXAMPLE = {'candidate_id': 'g1', 'source_ids': ['p1', 'p2'], 'adapter': 'implementation-required',
    'protocol': {}, 'data_split': 'Freeze data before calls; tune on dev only',
    'baselines': ['budget-matched lexical', 'proposed method'], 'metrics': ['held-out accuracy', 'actual API tokens'],
    'ablations': ['remove proposed mechanism'], 'falsification': 'No paired gain on held-out tasks',
    'cost_controls': {'max_total_tokens': 100000, 'max_calls': 100},
    'analysis': 'Paired task-level comparison including ties, failures and uncertainty',
    'pilot': 'First validate a small development-only subset',
    'limitations': ['Bounded source coverage; novelty not established'],
    'required_implementation': ['Implement new experiment adapter']}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_stage(stage, value, papers, selected_id=None, closest_papers=()):
    if not isinstance(value, dict): raise ValueError('Stage must return a JSON object')
    ids = {p['id'] for p in papers}
    if stage == 'experiment_design': ids.update(p['id'] for p in closest_papers)
    chunks = {c['id']: c['text'] for p in papers for c in p['chunks']}
    def refs(items):
        if not isinstance(items, list) or len(set(items)) < 2 or not set(items) <= ids:
            raise ValueError('At least two known source IDs required')
    if stage == 'literature_review':
        rows = value.get('papers')
        if not isinstance(rows, list) or len(rows) != len(ids) or {r.get('paper_id') for r in rows} != ids:
            raise ValueError('Reading notes must cover every supplied paper exactly once')
        if not _text(value.get('comparison')): raise ValueError('Cross-paper comparison required')
        for row in rows:
            if not all(_text(row.get(k)) for k in ('method', 'evaluation', 'limitations')):
                raise ValueError('Incomplete reading note')
            if not isinstance(row.get('evidence'), list) or not row['evidence']:
                raise ValueError('Reading note requires source evidence')
            for evidence in row['evidence']:
                key, quote = evidence.get('chunk_id'), evidence.get('quote')
                if (key not in chunks or not key.startswith(row['paper_id'] + ':') or
                    not _text(quote) or len(quote) > 300 or quote not in chunks[key]):
                    raise ValueError('Evidence quotation is absent from its cited source chunk')
    elif stage == 'question_formulation':
        rows = value.get('candidates')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 3:
            raise ValueError('One to three candidates required')
        candidate_ids = [r.get('id') for r in rows]
        if (not all(_text(i) for i in candidate_ids) or len(set(candidate_ids)) != len(rows)
                or value.get('selected_id') not in candidate_ids): raise ValueError('Invalid selected candidate')
        for row in rows:
            if not all(_text(row.get(k)) for k in ('question', 'hypothesis', 'motivation', 'falsification', 'verification_query')):
                raise ValueError('Incomplete candidate question')
            if len(row['verification_query']) > 500: raise ValueError('Verification query too long')
            refs(row.get('source_ids'))
            if row.get('novelty_status') != 'unverified': raise ValueError('Novelty cannot be established here')
    elif stage == 'experiment_design':
        refs(value.get('source_ids'))
        if value.get('candidate_id') != selected_id: raise ValueError('Plan must test the selected candidate')
        for key in ('data_split', 'falsification', 'analysis', 'pilot'):
            if not _text(value.get(key)): raise ValueError('Missing experiment field: ' + key)
        for key in ('baselines', 'metrics', 'ablations', 'limitations'):
            if not isinstance(value.get(key), list) or not value[key] or not all(_text(i) for i in value[key]):
                raise ValueError('Missing experiment field: ' + key)
        cost = value.get('cost_controls', {})
        if not isinstance(cost, dict) or any(type(cost.get(k)) is not int or cost[k] <= 0
                for k in ('max_total_tokens', 'max_calls')): raise ValueError('Positive explicit experiment cost ceilings required')
        if value.get('adapter') == 'structured-memory-v1':
            validate_handoff(value)
            if cost['max_total_tokens'] <= 20000 or cost['max_calls'] != 700:
                raise ValueError('Registered memory runner requires >20000 tokens and max_calls=700')
        elif value.get('adapter') != 'implementation-required' or not value.get('required_implementation'):
            raise ValueError('Unsupported adapter must identify required implementation')
    else: raise ValueError('Unknown research stage')
    return value


def validate_handoff(plan):
    if plan.get('adapter') != 'structured-memory-v1' or plan.get('protocol') != MEMORY_PROTOCOL:
        raise ValueError('Plan needs a new experiment implementation; fixed memory runner cannot execute it')


def load_bundle(directory):
    directory = Path(directory)
    state = json.loads((directory / 'state.json').read_text(encoding='utf-8'))
    if state['status'] != 'completed': raise ValueError('Research design is incomplete')
    required = {'sources.json', *[s + '.json' for s in STAGES], 'closest_work.json', 'handoff.json', 'REPORT.md'}
    if set(state.get('artifact_hashes', {})) != required:
        raise ValueError('Incomplete research artifact inventory')
    for name, expected in state['artifact_hashes'].items():
        if name not in ('sources.json', *[s + '.json' for s in STAGES], 'closest_work.json', 'handoff.json', 'REPORT.md'):
            raise ValueError('Unexpected artifact path')
        if file_digest(directory / name) != expected: raise ValueError('Research artifact changed: ' + name)
    return {name: json.loads((directory / (name + '.json')).read_text(encoding='utf-8'))
            for name in ('sources', *STAGES, 'closest_work', 'handoff')}


def research_artifacts(directory):
    bundle = load_bundle(directory)
    plan = bundle['experiment_design']; validate_handoff(plan)
    question = next(c for c in bundle['question_formulation']['candidates'] if c['id'] == plan['candidate_id'])
    brief = create_artifact('ResearchBrief', {'question': question['question'], 'hypothesis': question['hypothesis'],
        'closest_work': [p['title'] for p in bundle['sources']],
        'source_ids': question['source_ids'], 'falsification': question['falsification'],
        'feasibility': plan['pilot'], 'novelty_status': 'unverified',
        'discovery_manifest_sha256': file_digest(Path(directory) / 'manifest.json')})
    experiment = create_artifact('ExperimentPlan', {'dataset_version': plan['protocol']['dataset'],
        'split': plan['data_split'], 'methods': plan['protocol']['policies'],
        'budget_policy': plan['cost_controls'], 'metrics': plan['metrics'],
        'acceptance': plan['falsification'], 'commands': ['registered:structured-memory-v1'],
        'protocol': plan['protocol'], 'analysis': plan['analysis'], 'ablations': plan['ablations']}, [brief['artifact_id']])
    return brief, experiment


def report(bundle):
    lines = ['# 文献到实验方案', '', '状态：已形成研究方案；未证明创新，未运行新实验。', '', '## 阅读范围', '']
    for paper in bundle['sources']:
        lines += [f"- [{paper['title']}]({paper['url']})：{paper['reading_scope']}；{len(paper['chunks'])} 个原文片段。"]
    for stage in STAGES:
        lines += ['', '## ' + {'literature_review': '文献比较', 'question_formulation': '问题与假设',
                               'experiment_design': '实验设计'}[stage], '', '```json',
                  json.dumps(bundle[stage], ensure_ascii=False, indent=2), '```']
    lines += ['', '## 最近工作复查', '', f"检索状态：{bundle['closest_work']['status']}；结果仍需阅读，不能证明不存在相同工作。",
              '', '## 执行交接', '', json.dumps(bundle['handoff'], ensure_ascii=False, indent=2),
              '', '原文是有限摘录；引用匹配只验证出处，不自动验证模型解释。没有自动启动付费实验或上传论文。']
    return '\n'.join(lines) + '\n'


async def discover(directory, *, topic, query, max_total_tokens, config, count_tokens,
                   paper_limit=6, client=None, gateway=None):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    identity = {'schema_version': 1, 'topic': topic, 'query': query, 'paper_limit': paper_limit,
        'model': config['model'], 'provider': config['provider'], 'endpoint_hash': digest(config['api_base']),
        'max_total_tokens': max_total_tokens,
        'code_hashes': {p.name: file_digest(p) for p in (Path(__file__), Path(__file__).with_name('literature.py'))},
        'skill_hashes': {s: file_digest(SKILLS / (s + '.md')) for s in STAGES}}
    manifest = directory / 'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text(encoding='utf-8')) != identity:
            raise ValueError('Research inputs/code/skills/model changed; choose a new output directory')
        if (directory / 'state.json').exists():
            state = json.loads((directory / 'state.json').read_text(encoding='utf-8'))
            if state.get('status') == 'completed': return load_bundle(directory)
            # Verify already completed checkpoints before any further network/model call.
            for name, expected in state.get('artifact_hashes', {}).items():
                if '/' in name or '\\' in name or file_digest(directory / name) != expected:
                    raise ValueError('Changed checkpoint; choose a new output directory')
    else:
        if any(directory.iterdir()): raise ValueError('New research output directory must be empty')
        save_json(manifest, identity)
    gateway = gateway or ModelGateway(config, directory, max_total_tokens=max_total_tokens,
        max_calls=3, wall_seconds=900, count_tokens=count_tokens)
    client = client or ArxivClient(directory)
    hashes = {}
    def checkpoint(name, data):
        save_json(directory / name, data); hashes[name] = file_digest(directory / name)
        save_json(directory / 'state.json', {'status': 'running', 'artifact_hashes': hashes, 'resources': gateway.totals()})
    bundle = {}
    try:
        if (directory / 'sources.json').exists():
            papers = json.loads((directory / 'sources.json').read_text(encoding='utf-8'))
        else:
            found = client.search(query, paper_limit)
            if len(found) < 2: raise ValueError('Insufficient sources; broaden the query')
            papers = [client.read(p) for p in found]
        checkpoint('sources.json', papers); bundle['sources'] = papers
        for stage in STAGES:
            if stage == 'experiment_design':
                selected = next(c for c in bundle['question_formulation']['candidates']
                                if c['id'] == bundle['question_formulation']['selected_id'])
                closest_file = directory / 'closest_work.json'
                if closest_file.exists(): closest = json.loads(closest_file.read_text(encoding='utf-8'))
                else:
                    try:
                        closest = {'status': 'retrieved_not_exhaustive', 'query': selected['verification_query'],
                                   'papers': client.search(selected['verification_query'], 4)}
                    except (OSError, ValueError) as error:
                        closest = {'status': 'failed', 'papers': [], 'error_type': type(error).__name__}
                checkpoint('closest_work.json', closest); bundle['closest_work'] = closest
            example = ({'papers': [{'paper_id': p['id'], 'method': 'source-grounded description',
                'evaluation': 'source-grounded description or not established', 'limitations': 'source-grounded or not established',
                'evidence': [{'chunk_id': p['chunks'][0]['id'], 'quote': 'short exact source quotation'}]} for p in papers],
                'comparison': 'source-grounded comparison'} if stage == 'literature_review' else
                {'candidates': [{'id': 'g1', 'question': 'testable question', 'hypothesis': 'testable hypothesis',
                'motivation': 'evidence versus inference', 'source_ids': [p['id'] for p in papers[:2]],
                'novelty_status': 'unverified', 'falsification': 'negative result', 'verification_query': 'all:memory'}],
                'selected_id': 'g1'} if stage == 'question_formulation' else PLAN_EXAMPLE)
            if stage == 'experiment_design':
                example = {**PLAN_EXAMPLE, 'candidate_id': selected['id'], 'source_ids': selected['source_ids']}
            messages = [{'role': 'system', 'content': (SKILLS / (stage + '.md')).read_text(encoding='utf-8') +
                '\nReturn JSON only, no markdown. Write descriptions in Chinese; retain exact English quotes and schema keys.'},
                {'role': 'user', 'content': json.dumps({'topic': topic, 'sources': papers,
                    'previous_stages': {k: v for k, v in bundle.items() if k != 'sources'},
                    'schema_example': example, 'registered_adapter': MEMORY_PROTOCOL,
                    'adapter_cost_requirement': {'max_total_tokens': '>20000', 'max_calls': 700}}, ensure_ascii=False)}]
            response = await gateway.call(messages, 'discovery/' + stage, max_tokens=3500)
            value = json.loads(response['output'])
            validate_stage(stage, value, papers, bundle.get('question_formulation', {}).get('selected_id'),
                           bundle.get('closest_work', {}).get('papers', []))
            checkpoint(stage + '.json', value); bundle[stage] = value
        plan = bundle['experiment_design']
        handoff = {'status': 'registered_protocol_ready' if plan['adapter'] == 'structured-memory-v1' else 'implementation_required',
                   'adapter': plan['adapter'], 'plan_sha256': digest(plan), 'experiments_executed': False,
                   'novelty_status': 'unverified', 'closest_work_review': bundle['closest_work']['status']}
        checkpoint('handoff.json', handoff); bundle['handoff'] = handoff
        atomic_write(directory / 'REPORT.md', report(bundle)); hashes['REPORT.md'] = file_digest(directory / 'REPORT.md')
        save_json(directory / 'state.json', {'status': 'completed', 'artifact_hashes': hashes, 'resources': gateway.totals()})
        return bundle
    except Exception as error:
        save_json(directory / 'state.json', {'status': 'stopped', 'error_type': type(error).__name__,
                  'reason': str(error), 'artifact_hashes': hashes, 'resources': gateway.totals()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--topic', required=True)
    parser.add_argument('--query', required=True, help='Official arXiv search query')
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-total-tokens', type=int, required=True)
    parser.add_argument('--paper-limit', type=int, default=6)
    parser.add_argument('--config-dir')
    args = parser.parse_args()
    from baseline.runtime import read_model_config, token_count
    result = asyncio.run(discover(args.output, topic=args.topic, query=args.query,
        max_total_tokens=args.max_total_tokens, paper_limit=args.paper_limit,
        config=read_model_config(args.config_dir), count_tokens=token_count))
    print(json.dumps(result['handoff'], ensure_ascii=False))


if __name__ == '__main__': main()
