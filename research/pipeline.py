"""Atomic, resumable local evidence-to-manuscript pipeline."""
import json
from pathlib import Path
import time

from research.artifacts import atomic_write, digest, file_digest, save_json, validate_artifact
from research.evidence import import_baseline, source_hashes
from research.reviewer import review_manuscript
from research.writer import build_manuscript, render_markdown

ARTIFACT_FILES = {'run.json': 'RunManifest', 'evidence.json': 'EvidenceBundle',
                  'manuscript.json': 'ManuscriptBundle', 'review.json': 'ReviewDecision'}
OUTPUT_FILES = (*ARTIFACT_FILES, 'paper.md', 'resources.json', 'scorecard.json')


def implementation_hashes():
    root = Path(__file__).resolve().parent
    paths = list(root.glob('*.py')) + [root.parent / 'baseline/dataset.py']
    return {str(p.relative_to(root.parent)).replace('\\', '/'): file_digest(p) for p in sorted(paths)}


def scorecard():
    return {'source': 'User-provided competition rubric, 2026-10-11',
            'rubric': [{'category': 'paper_quality', 'maximum': 60,
                        'components': {'stanford_agentic_reviewer': 40, 'paper_evaluation_agent': 20}},
                       {'category': 'agent_system', 'maximum': 15},
                       {'category': 'resources', 'maximum': 10},
                       {'category': 'openjiuwen_contribution', 'maximum': 15}],
            'current_scores': None,
            'milestone_support': {
                'paper_quality': 'Raw-result rescoring and claim consistency; no scientific-quality or external score claim.',
                'agent_system': 'Explicit artifacts, parent links, failure records and integrity-aware resume.',
                'resources': 'Historical provider tokens and offline runtime; original draft costs excluded explicitly.',
                'openjiuwen_contribution': 'This research package is local tooling, not an additional framework contribution. Existing rail patch remains a separate contribution.'},
            'remaining': ['Broader and budget-matched experiments with ablations and held-out tests',
                          'Free-form scientific writing and citation verification',
                          'Separate official Stanford and paper-agent assessments',
                          'New openJiuwen/JiuwenSwarm feature with tests, documentation and patch/PR evidence',
                          'End-to-end resource report including writing/review calls']}


def can_resume(output, state, fingerprint):
    if not isinstance(state, dict) or state.get('status') != 'succeeded' or state.get('fingerprint') != fingerprint:
        return False
    try:
        if set(state.get('output_hashes', {})) != set(OUTPUT_FILES):
            return False
        for name in OUTPUT_FILES:
            if file_digest(output / name) != state['output_hashes'][name]:
                return False
        artifacts = {name: validate_artifact(json.loads((output / name).read_text(encoding='utf-8')), kind)
                     for name, kind in ARTIFACT_FILES.items()}
        run, evidence, manuscript, review = (artifacts[name] for name in ARTIFACT_FILES)
        if evidence['parent_ids'] != [run['artifact_id']]:
            return False
        if review['parent_ids'] != [manuscript['artifact_id'], evidence['artifact_id']]:
            return False
        return review['payload']['passed'] and review_manuscript(manuscript, evidence)['payload']['passed']
    except (OSError, ValueError, KeyError, TypeError):
        return False


def run_pipeline(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError('Source and output must be separate, non-nested directories')
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / 'state.json'
    started = time.perf_counter()
    stage = 'input_import'
    state = {'schema_version': 1, 'status': 'running', 'stage': stage,
             'source': str(source), 'output': str(output)}
    try:
        hashes = source_hashes(source)
        code_hashes = implementation_hashes()
        fingerprint = digest({'source': str(source), 'source_files': hashes, 'implementation': code_hashes})
        old_state = {}
        if state_path.exists():
            try:
                old_state = json.loads(state_path.read_text(encoding='utf-8'))
            except ValueError:
                pass
        if can_resume(output, old_state, fingerprint):
            return {'status': 'succeeded', 'resumed': True, 'fingerprint': fingerprint,
                    'output': str(output), 'new_model_calls': 0}
        state.update(fingerprint=fingerprint, source_files=hashes, implementation=code_hashes)
        save_json(state_path, state)
        run, evidence = import_baseline(source)
        if run['payload']['source_files'] != hashes:
            raise ValueError('Source changed during import; retry with stable inputs')
        save_json(output / 'run.json', run)
        save_json(output / 'evidence.json', evidence)
        stage = 'manuscript'
        state['stage'] = stage
        save_json(state_path, state)
        manuscript = build_manuscript(evidence)
        review = review_manuscript(manuscript, evidence)
        if not review['payload']['passed']:
            raise ValueError('Mechanical manuscript review failed')
        save_json(output / 'manuscript.json', manuscript)
        save_json(output / 'review.json', review)
        atomic_write(output / 'paper.md', render_markdown(manuscript))
        stage = 'resource_report'
        save_json(output / 'resources.json', {
            **evidence['payload']['resource_accounting'],
            'historical_experiment_api_calls': evidence['payload']['total_api_calls'],
            'historical_experiment_api_tokens': evidence['payload']['total_api_tokens'],
            'offline_pipeline_elapsed_seconds': time.perf_counter() - started,
            'methods': [{key: row[key] for key in ('policy', 'api_calls', 'input_tokens', 'output_tokens', 'total_tokens')}
                        for row in evidence['payload']['metrics']],
        })
        save_json(output / 'scorecard.json', scorecard())
        if source_hashes(source) != hashes or implementation_hashes() != code_hashes:
            raise ValueError('Inputs or implementation changed during execution')
        state.update(status='succeeded', stage='complete',
                     output_hashes={name: file_digest(output / name) for name in OUTPUT_FILES},
                     artifact_ids={name: artifact['artifact_id'] for name, artifact in
                                   zip(ARTIFACT_FILES, (run, evidence, manuscript, review))})
        save_json(state_path, state)
        return {'status': 'succeeded', 'resumed': False, 'fingerprint': fingerprint,
                'output': str(output), 'new_model_calls': 0}
    except Exception as error:
        state.update(status='failed', stage=stage, error_type=type(error).__name__, error=str(error))
        save_json(state_path, state)
        raise
