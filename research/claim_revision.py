"""Offline claim checks and traceable revision plans; never a semantic fact checker."""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping

from research.memory_paper import REFERENCES

ROOT = Path(__file__).resolve().parents[1]
CITATIONS = frozenset(r['key'] for r in REFERENCES)
GAPS = (
    ('novelty_limited', 'Introduction / Related work', 'The central mechanism is established temporal database practice.',
     'Frame the contribution as a reusable engineering component; distinguish filtering, packing and answer arbitration.',
     'Primary-source comparison of the exact contribution; code integration alone cannot establish novelty.'),
    ('small_synthetic', 'Methods / Evaluation', 'The original held-out evaluation is small and synthetic.',
     'Separate the historical case study from fresh task generation; state distributions and uncertainty.',
     'Expanded frozen datasets, disjoint evaluation splits, per-family outcomes and repeated measurements.'),
    ('semantic_baseline', 'Evaluation', 'No semantic or hybrid retrieval baseline was evaluated originally.',
     'Describe embedding identity, objective, latency and common context budget before comparing quality.',
     'Completed dense/hybrid retrieval and answer results with tokenizer rechecks and model provenance.'),
    ('external_benchmark', 'Evaluation / Limitations', 'External validity remains unestablished.',
     'Report external retrieval and answer evaluation separately; preserve the original free-text task interface.',
     'Pinned external dataset, split/sample provenance, answer evaluation and judge provenance; no official-score equivalence.'),
    ('multimodel_repeats', 'Evaluation / Limitations', 'One backbone and one frozen run limit generalization.',
     'Report available models and repeat dimensions, failed/unrun cells and independent task seeds.',
     'Completed model-by-repeat grid with uncertainty; repeated deterministic calls are not independent seeds.'),
    ('packer_heuristic', 'Methods / Ablations', 'Greedy packing lacks comparison and tokenization sensitivity analysis.',
     'State the objective and compare alternative atomic-group packers with actual context token counts.',
     'Stress-case and held-out packer outcomes, runtime, retained evidence and nonadditivity violations.'),
    ('conflict_reader_tie', 'Ablations / Discussion', 'Conflict preservation showed no answer accuracy advantage originally.',
     'Keep the negative finding; compare baseline and conflict-aware readers with the same evidence and budgets.',
     'Paired reader outcomes, abstention/conflict correctness, failures and uncertainty; mechanism alone is insufficient.'),
    ('errors_recent_full', 'Error analysis / Discussion', 'Recent and full-history behavior requires task-level explanation.',
     'Separate missing-evidence errors from answer errors and show per-family recent/full cases.',
     'Artifact-linked task breakdowns; distraction is a hypothesis unless controlled evidence tests it.'),
    ('proxy_billing', 'Methods / Cost', 'Proxy context tokens and provider billing are distinct quantities.',
     'Show proxy context counts beside provider input/output usage and all overhead; disclose unknown usage.',
     'Per-request provider usage, context proxy measurements and mismatch distribution; no billing bound from proxy alone.'),
    ('portable_interface', 'Implementation / Reproducibility', 'Project-specific names obscure transferability.',
     'Present a minimal input/output contract, dependency boundaries and an adapter example.',
     'Public interface/source hashes, independent adapter test and dependency/resource instructions.'),
)
GAP_ARTIFACTS = {
    'novelty_limited': ('research/memory_paper.py',),
    'small_synthetic': ('research/memory_dataset.py',),
    'semantic_baseline': ('research/advanced_retrieval.py', 'docs/retrieval_upgrade.md'),
    'external_benchmark': ('research/external_benchmark.py', 'docs/external_benchmark_protocol.md'),
    'multimodel_repeats': ('research/review_upgrade.py',),
    'packer_heuristic': ('research/advanced_retrieval.py',),
    'conflict_reader_tie': ('research/review_upgrade.py',),
    'errors_recent_full': ('output/workbench_analysis_20261106/error_analysis.json',),
    'proxy_billing': ('research/model_gateway.py',),
    'portable_interface': ('upstream/jiuwenswarm/agents/harness/common/versioned_memory.py',),
}


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _safe_path(path):
    path = Path(path).resolve()
    if any(re.search(r'(^|[._-])(token|secret|credential|config|env)([._-]|$)', part, re.I)
           for part in path.parts):
        raise ValueError('Configuration and credential paths are not evidence inputs')
    return path


def make_evidence_ref(path, locator='', kind='metric'):
    """Bind a JSON pointer or whole-file artifact to its exact SHA-256 bytes."""
    path = _safe_path(path)
    return {'kind': kind, 'source': str(path), 'source_hash': _hash(path.read_bytes()), 'locator': locator}


def _resolve(ref, evidence):
    if ref.get('kind') not in {'metric', 'artifact', 'review', 'source'}:
        raise ValueError('Unknown evidence kind')
    path = _safe_path(ref['source'])
    data = path.read_bytes()
    if _hash(data) != ref.get('source_hash'):
        raise ValueError('Evidence source hash mismatch')
    pointer = ref.get('locator')
    if not isinstance(pointer, str):
        raise ValueError('Evidence locator is required')
    if ref['kind'] == 'metric' and not pointer:
        raise ValueError('Metric locator must be a nonempty JSON pointer')
    if not pointer:
        return data.decode('utf-8')
    if not pointer.startswith('/'):
        raise ValueError('Locator must be a JSON pointer')
    value = json.loads(data)
    for part in pointer[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _finite_number(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def validate_claim(claim, evidence):
    """Check whitelisted citations, explicit arithmetic and hashes, not semantic truth.

    Numeric findings live in ``value``, never in prose. Measured syntax supports
    identity(one locator), ratio(two), difference(two), sum(one or more). Evidence
    may bind run_directory; local refs always reread the source bytes. Cross-run
    measurements are rejected rather than silently inherited by a selected run.
    """
    issues = []
    text = claim.get('text', '')
    if not isinstance(text, str) or not text.strip():
        issues.append('Claim text is required')
        text = ''
    cited = [key.strip() for group in re.findall(r'\[([^\]]+)\]', text)
             for key in re.split(r'[,;]', group)] + claim.get('citations', [])
    if any(key not in CITATIONS for key in cited):
        issues.append('Unverified citation: use a curated REFERENCES key')
    cleaned = re.sub(r'\[[^\]]+\]', '', text)
    cleaned = re.sub(r'\b(?:BM25|Mem0|cl100k_base)\b', '', cleaned)
    if re.search(r'\d|%', cleaned):
        issues.append('Unstructured numeric prose: use measured value and metric locators')
    if re.search(r'\b(?:novel|state.of.the.art|statistically significant|proves?|review score|reviewer satisfied)\b', text, re.I):
        issues.append('Unsupported strength, novelty or review-outcome language requires human review')
    refs = claim.get('evidence_refs', [])
    values = []
    for ref in refs:
        try:
            if claim.get('type') == 'measured' and evidence.get('run_directory'):
                if not _safe_path(ref['source']).is_relative_to(_safe_path(evidence['run_directory'])):
                    raise ValueError('Metric source is outside the selected run')
            values.append(_resolve(ref, evidence))
        except (ValueError, KeyError, IndexError, TypeError, OSError, UnicodeError) as exc:
            issues.append(f'Invalid evidence: {exc}')
    if claim.get('type') not in {'measured', 'qualitative', 'limitation'}:
        issues.append('Unknown claim type')
    if claim.get('type') == 'measured':
        condition = claim.get('condition')
        scope = claim.get('scope')
        if not isinstance(condition, dict) or not condition or 'kind' not in condition:
            issues.append('Measured condition must identify the data kind and evaluation condition')
        if not isinstance(scope, str) or not scope.strip():
            issues.append('Measured scope is required')
        elif isinstance(condition, dict) and condition.get('kind') == 'external':
            if not re.search(r'\bproxy\b', scope, re.I) or not re.search(r'\bnot (?:an? )?official\b', scope, re.I):
                issues.append('External scope must qualify the measurement as a proxy, not an official score')
        if not refs or any(ref.get('kind') != 'metric' for ref in refs):
            issues.append('Measured claims require typed metric evidence')
        operation = claim.get('operation')
        arities = {'identity': 1, 'ratio': 2, 'difference': 2}
        if operation not in {*arities, 'sum'} or (operation in arities and len(values) != arities[operation]) or not values:
            issues.append('Invalid measured operation or operand count')
        elif all(_finite_number(x) for x in values):
            try:
                actual = {'identity': lambda: values[0], 'ratio': lambda: values[0]/values[1],
                          'difference': lambda: values[0]-values[1], 'sum': lambda: sum(values)}[operation]()
                reported = claim.get('value')
                if not _finite_number(actual) or not _finite_number(reported):
                    issues.append('Computed and reported numeric values must both be finite')
                elif not math.isclose(actual, reported, rel_tol=1e-10, abs_tol=1e-12):
                    issues.append(f'Reported numeric value disagrees with recomputed value {actual}')
            except ZeroDivisionError:
                issues.append('Numeric denominator is zero')
            except OverflowError:
                issues.append('Numeric operation overflowed')
        else:
            issues.append('Metric locators must resolve to finite numbers')
    return issues


def _claims_from_summary(path):
    summary = json.loads(path.read_text(encoding='utf-8'))
    claims = []
    # These paired counts are sufficient to recompute the reported ratios. Never
    # trust an accuracy scalar merely because it appears in a saved summary.
    ratios = [('exact_accuracy', 'exact_correct', 'tasks'),
              ('micro_field_accuracy', 'field_correct', 'field_total'),
              ('context_evidence_recall', 'evidence_available', 'evidence_required')]
    for index, row in enumerate(summary.get('methods', [])):
        for metric, numerator, denominator in ratios:
            if numerator not in row or denominator not in row or not row[denominator]:
                continue
            claim = {'id': f'methods-{index}-{metric}', 'type': 'measured',
                     'text': f'Observed {metric.replace("_", " ")} in the identified condition.',
                     'condition': {key: row.get(key) for key in ('kind', 'split', 'policy', 'packer', 'budget', 'model', 'seed', 'reader', 'repeat')},
                     'value': row.get(metric, row[numerator]/row[denominator]), 'operation': 'ratio',
                     'scope': ('External answer exact match is a normalized proxy, not an official benchmark judge score.'
                               if row.get('kind') == 'external' else
                               'Only the run and condition identified by these source hashes.'),
                     'evidence_refs': [make_evidence_ref(path, f'/methods/{index}/{numerator}'),
                                       make_evidence_ref(path, f'/methods/{index}/{denominator}')]}
            claims.append(claim)
    # Upgrade runners may publish their own explicit measured claims; subject to
    # the identical validation rules rather than inferred meaning of field names.
    claims.extend(copy.deepcopy(summary.get('measured_claims', [])))
    return claims


def build_claim_ledger(run_dir, sections=None):
    run_dir = _safe_path(run_dir)
    claims, source_refs = [], []
    summary_path = run_dir/'summary.json'
    if summary_path.exists():
        claims = _claims_from_summary(summary_path)
        source_refs.append(make_evidence_ref(summary_path, kind='artifact'))
    review_path = ROOT/'submission/memory-20261016-review.txt'
    review_ref = make_evidence_ref(review_path, kind='review') if review_path.exists() else None
    for chapter, text in (sections or {}).items():
        claims.append({'id': f'section-{chapter}', 'type': 'qualitative', 'text': text,
                       'chapter': chapter, 'evidence_refs': []})
    for claim in claims:
        claim['validation_issues'] = validate_claim(claim, {'run_directory': str(run_dir)})
        claim['validation_status'] = 'unsupported' if claim['validation_issues'] else 'mechanically_checked'
    matrix = []
    for key, chapter, critique, action, needed in GAPS:
        # Artifact presence is traceability, never acceptance or empirical closure.
        artifacts = list(source_refs)
        if review_ref:
            artifacts.append(review_ref)
        implementation_refs = [make_evidence_ref(ROOT/path, kind='artifact')
                               for path in GAP_ARTIFACTS[key] if (ROOT/path).is_file()]
        artifacts.extend(implementation_refs)
        matrix.append({'gap_id': key, 'chapter': chapter, 'reviewer_weakness': critique,
                       'status': 'open_evidence_required', 'action': action, 'evidence_needed': needed,
                       'evidence_refs': artifacts,
                       'artifact_status': 'Related artifacts available; empirical adequacy remains unassessed.' if implementation_refs else 'No related implementation artifact found.',
                       'resolution_rule': 'Human evaluation of completed, relevant measurements is required; implementation alone does not close this gap.'})
    plan = [{'chapter': chapter,
             'review_gaps': [r['gap_id'] for r in matrix if chapter in r['chapter']],
             'revision_actions': [r['action'] for r in matrix if chapter in r['chapter']],
             'supported_claim_ids': [c['id'] for c in claims if not c['validation_issues'] and c['type'] == 'measured']
                                    if chapter in {'Evaluation', 'Ablations', 'Discussion', 'Error analysis'} else [],
             'evidence_needed': [r['evidence_needed'] for r in matrix if chapter in r['chapter']]}
            for chapter in ('Introduction', 'Related work', 'Methods', 'Evaluation', 'Ablations', 'Error analysis', 'Discussion', 'Limitations', 'Implementation', 'Reproducibility')]
    return {'schema_version': 1, 'run_directory': str(run_dir), 'review_score': None,
            'validation_scope': 'Source identity, curated citation keys and structured numeric arithmetic only. No certification of full-text semantic truth or reviewer acceptance.',
            'claims': claims, 'unsupported_claims': [c for c in claims if c['validation_issues']],
            'chapter_plan': plan, 'review_response_matrix': matrix, 'references': REFERENCES,
            'missing_evidence': [] if summary_path.exists() else ['Run summary is absent; no historical result is substituted.']}


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class RevisionRecord:
    sections: Mapping
    changes: tuple
    reason: str
    evidence_refs: tuple
    record_hash: str
    created_at: str


def apply_revision(sections, updates, reason, evidence_refs):
    """Return a deeply immutable edit record; never overwrite a manuscript."""
    if not isinstance(reason, str) or not reason.strip() or not evidence_refs:
        raise ValueError('Revision requires a nonempty reason and evidence references')
    for ref in evidence_refs:
        _resolve(ref, {})
    revised = copy.deepcopy(sections)
    changes = []
    for chapter, text in updates.items():
        if chapter not in sections:
            raise ValueError(f'Unknown chapter: {chapter}')
        issues = validate_claim({'type': 'qualitative', 'text': text, 'evidence_refs': evidence_refs}, {})
        if issues:
            raise ValueError('; '.join(issues))
        changes.append({'chapter': chapter, 'before': sections[chapter], 'after': text,
                        'reason': reason, 'evidence_refs': copy.deepcopy(evidence_refs)})
        revised[chapter] = text
    created_at = datetime.now(timezone.utc).isoformat()
    payload = {'sections': revised, 'changes': changes, 'reason': reason,
               'evidence_refs': evidence_refs, 'created_at': created_at}
    return RevisionRecord(_freeze(revised), _freeze(changes), reason, _freeze(evidence_refs),
                          _hash(json.dumps(payload, sort_keys=True).encode()), created_at)


def write_outputs(ledger, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in [('claim_ledger.json', ledger), ('chapter_plan.json', ledger['chapter_plan'])]:
        (output/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    lines = ['# Reviewer response worklist', '', ledger['validation_scope'], '',
             'The original review score is not a score for this revision. No reviewer concern is declared solved.', '']
    for row in ledger['review_response_matrix']:
        lines.extend([f'## {row["gap_id"]}', '', f'Concern: {row["reviewer_weakness"]}',
                      f'Status: {row["status"]}', f'Proposed revision: {row["action"]}',
                      f'Evidence still needed: {row["evidence_needed"]}', 'Evidence sources:'])
        lines.extend(f'- `{ref["source"]}`; SHA-256 `{ref["source_hash"]}`; locator `{ref["locator"] or "whole file"}`'
                     for ref in row['evidence_refs'])
        lines.append('')
    (output/'reviewer_response.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--sections', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sections = json.loads(_safe_path(args.sections).read_text(encoding='utf-8')) if args.sections else None
    write_outputs(build_claim_ledger(args.run_dir, sections), args.output)


if __name__ == '__main__':
    main()
