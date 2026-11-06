"""Deterministic, read-only descriptive analysis of saved memory experiment scores.

This module never imports the model gateway or recomputes answers. Its categories
describe joint observations, not causal attribution to a retriever or reader.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

SUCCESS = {'ok', 'success', 'completed', 'succeeded'}
COUNT_FIELDS = ('expected_rows', 'observed_rows', 'missing_rows', 'failed_rows',
                'invalid_score_rows', 'scored_rows', 'exact_correct', 'exact_errors',
                'retrieval_insufficient_errors', 'complete_evidence_errors')
LONGMEMEVAL = 'https://github.com/xiaowu0162/LongMemEval'


def next_experiment_plan():
    """A frozen proposal template, with no assertion of newly measured outcomes."""
    return {
        'schema_version': 1, 'status': 'proposed_not_run', 'paid_calls_performed': 0,
        'title': 'Separate evidence selection, packing, and conflict-aware reading',
        'sources': [{'url': LONGMEMEVAL, 'checked_date': '2026-11-06',
                     'facts': ['The original benchmark contains 500 questions.',
                               'Its abilities include knowledge updates, temporal reasoning, and abstention.',
                               'The README announces LongMemEval-V2 in May 2026.'],
                     'use': 'Future external validity evaluation; neither release was run here.'}],
        'protocol_status': 'Proposed configuration frozen in this artifact; register exact data, model, code and hardware hashes before execution.',
        'data': {'controlled': 'New disjoint seeds; development-only tuning, then lock a held-out set before calls.',
                 'external': 'Pin the cleaned original LongMemEval release and hash all files; evaluate its 500 questions separately from synthetic tasks. Treat V2 as a distinct future protocol.',
                 'no_test_tuning': True},
        'experiments': [
            {'id': 'semantic_hybrid', 'hypothesis': 'Semantic or hybrid selection may recover evidence missed by lexical selection.',
             'arms': ['BM25', 'dense semantic retriever with pinned local embedding model revision',
                      'BM25+dense reciprocal rank fusion (k=60)'],
             'controls': 'Same source records, query, reader, tokenizer and 256/512 source-token budgets; rank per record; deterministic ties by record ID. Tune no weights on held-out tasks.',
             'measure': ['saved evidence recall', 'exact accuracy', 'index and retrieval latency', 'embedding and inference cost']},
            {'id': 'conflict_reader', 'hypothesis': 'An explicit conflict-aware reader may reduce errors observed with complete evidence.',
             'arms': ['existing reader', 'conflict-aware reader that compares valid_at/observed_at, lists competing maximal claims, and emits null for unresolved claims'],
             'controls': 'Replay identical saved contexts to both readers; same model revision, temperature, answer budget and output schema. Keep internal comparison out of final JSON answer.',
             'measure': ['exact accuracy conditional on complete evidence', 'conflict-family abstention accuracy', 'token usage and latency']},
            {'id': 'packer_ablation', 'hypothesis': 'Atomic-group selection heuristics may change coverage at fixed context budget; current versioned already preserves maximal-time groups atomically.',
             'arms': ['record-level ranking/packing baseline (e.g. lexical/BM25)',
                      'current versioned atomic maximal-time-group smaller-first packer',
                      'proposed alternate atomic-group utility/coverage-aware packer'],
             'controls': 'The record-level baseline provides context, not an isolated packing-heuristic comparison. Compare current and alternate atomic packers with identical eligible maximal-time groups, reader and budgets; pre-register utility/coverage rules on development data only. Count every metadata token; prohibit gold labels in packing; report dropped or oversized bundles. Cross the three arms with both readers; no arm is newly run here.',
             'measure': ['evidence recall', 'all-conflict-claim coverage', 'exact accuracy', 'actual context tokens']}],
        'analysis': ['Report per split, family, policy and budget; use paired task comparisons and ties.',
                     'Declare missing responses and provider failures separately; report denominators.',
                     'Report descriptive paired uncertainty with task/seed dependence disclosed; no causal claims from this retrospective error partition.',
                     'Publish complete artifacts, hashes, model configuration, source-token counts and actual provider usage.'],
        'execution_gate': 'No benchmark download, new inference or paid evaluation is performed by this offline module. Set a separate explicit call/token/cost cap before any future live run.',
        'success_criteria': 'Pre-register primary held-out exact accuracy and complete-evidence error rate; compare paired outcomes at matched budgets. Improvements remain hypotheses until measured.'}


def _index(rows, key, label):
    indexed = {}
    for row in rows:
        identity = key(row)
        if identity in indexed:
            raise ValueError(f'Duplicate {label}: {identity}')
        indexed[identity] = row
    return indexed


def _category(row):
    if row is None:
        return 'missing_result'
    if row.get('status') not in SUCCESS:
        return 'failed_result'
    score = row.get('score')
    if not isinstance(score, dict) or type(score.get('exact')) is not bool:
        return 'invalid_score'
    recall = score.get('evidence_recall')
    if type(recall) not in (int, float) or not math.isfinite(recall) or not 0 <= recall <= 1:
        return 'invalid_score'
    if score['exact']:
        return 'exact_correct'
    return 'complete_evidence_error' if recall == 1 else 'retrieval_insufficient_error'


def _counts(items):
    counts = dict.fromkeys(COUNT_FIELDS, 0)
    for item in items:
        category = item['category']
        counts['expected_rows'] += 1
        counts['observed_rows'] += category != 'missing_result'
        for cat, field in [('missing_result', 'missing_rows'), ('failed_result', 'failed_rows'),
                           ('invalid_score', 'invalid_score_rows'), ('exact_correct', 'exact_correct'),
                           ('retrieval_insufficient_error', 'retrieval_insufficient_errors'),
                           ('complete_evidence_error', 'complete_evidence_errors')]:
            counts[field] += category == cat
    counts['exact_errors'] = counts['retrieval_insufficient_errors'] + counts['complete_evidence_errors']
    counts['scored_rows'] = counts['exact_errors'] + counts['exact_correct']
    counts['exact_accuracy_scored'] = counts['exact_correct'] / counts['scored_rows'] if counts['scored_rows'] else None
    return counts


def analyze_errors(run_dir):
    """Return JSON-safe diagnostics using saved score.exact/evidence_recall only.

    Missing planned rows, failed statuses and invalid scores remain visible and
    excluded from scored denominators. Duplicate/unplanned identities are rejected.
    No source file is changed. Endpoint credentials and call ledgers are not read.
    """
    directory = Path(run_dir).resolve()
    inputs = {name: (directory / name).read_bytes() for name in ('dataset.json', 'manifest.json', 'results.jsonl')}
    tasks = _index(json.loads(inputs['dataset.json']), lambda t: t['id'], 'task')
    manifest = json.loads(inputs['manifest.json'])
    key = lambda r: (r['task_id'], r['policy'], r['budget'])
    expected = _index(manifest['grid'], key, 'grid entry')
    rows = _index([json.loads(line) for line in inputs['results.jsonl'].decode('utf-8').splitlines() if line.strip()], key, 'result')
    if set(rows) - set(expected):
        raise ValueError('Result outside manifest grid')
    items = []
    for identity in sorted(expected):
        task_id, policy, budget = identity
        if task_id not in tasks:
            raise ValueError(f'Unknown task in manifest: {task_id}')
        task, row = tasks[task_id], rows.get(identity)
        for field in ('split', 'family'):
            if row and field in row and row[field] != task[field]:
                raise ValueError(f'Result {field} differs from dataset: {identity}')
        items.append(dict(task_id=task_id, split=task['split'], family=task['family'], policy=policy,
                          budget=budget, category=_category(row)))
    grouped = defaultdict(list)
    summaries = defaultdict(list)
    for item in items:
        grouped[(item['split'], item['family'], item['policy'], item['budget'])].append(item)
        summaries[(item['split'], item['policy'], item['budget'])].append(item)
    groups = [dict(zip(('split', 'family', 'policy', 'budget'), identity), **_counts(group))
              for identity, group in sorted(grouped.items())]
    group_summaries = [dict(zip(('split', 'policy', 'budget'), identity), **_counts(group))
                       for identity, group in sorted(summaries.items())]
    comparisons = []
    for split, budget in sorted({(i['split'], i['budget']) for i in items}):
        pairs = [(rows.get((t['id'], 'versioned', budget)), rows.get((t['id'], 'no_conflict', budget)))
                 for t in tasks.values() if t['split'] == split
                 and (t['id'], 'versioned', budget) in expected
                 and (t['id'], 'no_conflict', budget) in expected]
        if not pairs:
            continue
        valid = [(a, b) for a, b in pairs if _category(a) in ('exact_correct', 'complete_evidence_error', 'retrieval_insufficient_error')
                 and _category(b) in ('exact_correct', 'complete_evidence_error', 'retrieval_insufficient_error')]
        comparison = dict(split=split, budget=budget, left='versioned', right='no_conflict',
                          expected_pairs=len(pairs), paired_rows=len(valid), excluded_pairs=len(pairs)-len(valid))
        for name, predicate in {
            'both_correct': lambda a,b: a['score']['exact'] and b['score']['exact'],
            'both_wrong': lambda a,b: not a['score']['exact'] and not b['score']['exact'],
            'left_only_correct': lambda a,b: a['score']['exact'] and not b['score']['exact'],
            'right_only_correct': lambda a,b: not a['score']['exact'] and b['score']['exact'],
            'exact_ties': lambda a,b: a['score']['exact'] == b['score']['exact'],
            'evidence_recall_equal': lambda a,b: a['score']['evidence_recall'] == b['score']['evidence_recall'],
            'selected_ids_equal': lambda a,b: 'selected_ids' in a and 'selected_ids' in b and a['selected_ids'] == b['selected_ids'],
            'response_equal': lambda a,b: 'answer' in a and 'answer' in b and a['answer'] == b['answer'],
        }.items():
            comparison[name] = sum(bool(predicate(a,b)) for a,b in valid)
        comparisons.append(comparison)
    cases = []
    for item in items:
        if item['category'] == 'exact_correct':
            continue
        task = tasks[item['task_id']]
        row = rows.get((item['task_id'], item['policy'], item['budget'])) or {}
        gold_ids = {rid for ids in task.get('gold_evidence', {}).values() for rid in ids}
        selected = row.get('selected_ids', [])
        saved_score = row.get('score') if isinstance(row.get('score'), dict) else {}
        # Explicit allowlist: no call messages, endpoint values or credentials.
        cases.append({**item, 'status': row.get('status', 'missing'), 'question': task['question'],
                      'response': row.get('answer'), 'gold': task['gold'],
                      'score': {k: v for k,v in saved_score.items()
                                if isinstance(v, (bool, int, float)) and (not isinstance(v, float) or math.isfinite(v))},
                      'selected_ids': selected, 'gold_evidence': task.get('gold_evidence', {}),
                      'missing_evidence_ids': sorted(gold_ids - set(selected)), 'query': task.get('query', {}),
                      'relevant_records': [r for r in task.get('records', []) if r['id'] in gold_ids or
                                           (r.get('entity') == task.get('query', {}).get('entity') and
                                            r.get('attribute') in task.get('query', {}).get('attributes', []))]})
    return {'schema_version': 1, 'run_dir': str(directory),
            'provenance': {'input_sha256': {name: hashlib.sha256(data).hexdigest() for name,data in inputs.items()},
                           'score_source': 'Existing result.score.exact and result.score.evidence_recall; not regraded.',
                           'new_model_calls': 0},
            'definitions': {'retrieval_insufficient_error': 'Successful response, score.exact false, evidence_recall < 1.',
                            'complete_evidence_error': 'Successful response, score.exact false, evidence_recall == 1.',
                            'counts': 'Expected grid rows; missing, failed and invalid-score rows excluded from scored denominators.'},
            'overview': _counts(items), 'groups': groups, 'group_summaries': group_summaries,
            'comparisons': comparisons, 'cases': cases,
            'limitations': ['These are descriptive co-occurrences, not proven causes or reader/retriever causal attribution.',
                            'Evidence recall is the existing metric; summary-context evidence may differ from source selected IDs.',
                            'Full is an unbounded context reference, not a matched-budget baseline.',
                            'Small synthetic task families and shared seeds limit generalization; dev is separate from test.',
                            'Equal outcomes or selections do not prove equivalence; versioned/no_conflict ties do not establish conflict-handler benefit.',
                            'No new measurements, model calls, external benchmark evaluation, or paper edits.'],
            'next_experiment_plan': next_experiment_plan()}


def render_markdown(report):
    lines = ['# Descriptive error analysis', '',
             'Offline analysis of saved scores. No new model calls. Categories describe observations, not causes.', '',
             '## Counts', '',
             '| Split | Policy | Budget | Scored | Correct | Evidence incomplete errors | Complete evidence errors | Missing / failed / invalid |',
             '|---|---|---:|---:|---:|---:|---:|---|']
    for g in report['group_summaries']:
        lines.append(f"| {g['split']} | {g['policy']} | {g['budget']} | {g['scored_rows']} | {g['exact_correct']} | {g['retrieval_insufficient_errors']} | {g['complete_evidence_errors']} | {g['missing_rows']} / {g['failed_rows']} / {g['invalid_score_rows']} |")
    lines += ['', '## Versioned versus no_conflict', '', 'Equal exact outcomes do not identify the effect of conflict handling.', '']
    for pair in report['comparisons']:
        lines.append(f"- {pair['split']}, budget {pair['budget']}: {pair['exact_ties']}/{pair['paired_rows']} exact ties; {pair['both_correct']} both correct, {pair['both_wrong']} both wrong; {pair['left_only_correct']} versioned-only correct, {pair['right_only_correct']} no_conflict-only correct; {pair['selected_ids_equal']} identical selections.")
    lines += ['', '## Observed error cases', '', 'Every error is retained in JSON. The following recent/full cases include actual saved responses and gold.', '']
    for c in report['cases']:
        if c['policy'] not in ('recent', 'full'):
            continue
        lines += [f"### {c['task_id']} / {c['policy']} / {c['budget']}", '',
                  f"Split: {c['split']}; family: {c['family']}; category: {c['category']}.", '',
                  c['question'], '', 'Saved response:', '```json', str(c['response']), '```',
                  'Gold:', '```json', json.dumps(c['gold'], ensure_ascii=False, sort_keys=True), '```',
                  f"Missing gold evidence IDs in selection: {', '.join(c['missing_evidence_ids']) or 'none'}.", '']
    lines += ['## Interpretation limits', ''] + ['- '+s for s in report['limitations']]
    lines += ['', '## Next experiment proposal', '',
              f"Source: [Official LongMemEval repository]({LONGMEMEVAL}), checked 2026-11-06. The original benchmark has 500 questions and includes knowledge updates, temporal reasoning and abstention. The README announces V2 in May 2026. Neither benchmark was run here.", '',
              'The accompanying next_experiment_plan.json freezes future semantic/hybrid selection, conflict-aware reader and packer ablation proposals. They are hypotheses, not measured improvements.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source, target = args.run_dir.resolve(), args.output.resolve()
    if target == source or target.is_relative_to(source):
        parser.error('Output must be outside the immutable source run directory')
    report = analyze_errors(source)
    target.mkdir(parents=True, exist_ok=True)
    for filename, value in [('error_analysis.json', report), ('next_experiment_plan.json', report['next_experiment_plan'])]:
        (target / filename).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    (target / 'ERROR_ANALYSIS.md').write_text(render_markdown(report), encoding='utf-8')
    print(f"Saved offline analysis: {target}")


if __name__ == '__main__':
    main()
