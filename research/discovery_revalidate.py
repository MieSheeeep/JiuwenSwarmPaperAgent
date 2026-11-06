"""Validate already captured discovery responses offline into a new derived bundle."""
import argparse
import json
from pathlib import Path

from research.artifacts import atomic_write, file_digest, save_json, digest
from research.discovery import STAGES, SKILLS, validate_stage, report
from research.model_gateway import read_jsonl, valid_usage


def revalidate_capture(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Derived output must be separate from source')
    if output.exists() and any(output.iterdir()): raise ValueError('Derived output must be empty')
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    papers = json.loads((source/'sources.json').read_text(encoding='utf-8'))
    closest = json.loads((source/'closest_work.json').read_text(encoding='utf-8'))
    calls = read_jsonl(source/'calls.jsonl')
    if len(calls) != 3 or any(c.get('status') != 'ok' or not valid_usage(c.get('usage')) for c in calls):
        raise ValueError('Exactly three accounted, successful stage responses required')
    bundle = {'sources': papers, 'closest_work': closest}
    for stage in STAGES:
        matches = [c for c in calls if c['tag'] == 'discovery/' + stage]
        if len(matches) != 1: raise ValueError('Missing or duplicate stage response')
        value = json.loads(matches[0]['output'])
        validate_stage(stage, value, papers, bundle.get('question_formulation', {}).get('selected_id'), closest['papers'])
        bundle[stage] = value
    plan = bundle['experiment_design']
    bundle['handoff'] = {'status': 'registered_protocol_ready' if plan['adapter'] == 'structured-memory-v1' else 'implementation_required',
        'adapter': plan['adapter'], 'plan_sha256': digest(plan), 'experiments_executed': False,
        'novelty_status': 'unverified', 'closest_work_review': closest['status']}
    output.mkdir(parents=True, exist_ok=True)
    save_json(output/'manifest.json', {**manifest, 'derived_by': 'offline-revalidation',
        'source_hashes': {name: file_digest(source/name) for name in ('manifest.json', 'sources.json', 'closest_work.json', 'calls.jsonl')},
        'validator_sha256': file_digest(Path(__file__).with_name('discovery.py')),
        'original_generation_skill_hashes': manifest['skill_hashes']})
    hashes = {}
    for name, value in bundle.items():
        save_json(output/(name+'.json'), value); hashes[name+'.json'] = file_digest(output/(name+'.json'))
    atomic_write(output/'REPORT.md', report(bundle))
    hashes['REPORT.md'] = file_digest(output/'REPORT.md')
    save_json(output/'state.json', {'status': 'completed', 'artifact_hashes': hashes,
        'new_model_calls': 0, 'validation_scope': 'source identifiers and exact evidence quotes, not scientific truth',
        'resources': {'api_calls': len(calls), 'known_api_tokens': sum(c['usage']['total_tokens'] for c in calls),
                      'unknown_spend_ids': [], 'summed_call_seconds': sum(c.get('elapsed_seconds', 0) for c in calls)}})
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = revalidate_capture(args.source, args.output)
    print(json.dumps(result['handoff'], ensure_ascii=False))


if __name__ == '__main__': main()
