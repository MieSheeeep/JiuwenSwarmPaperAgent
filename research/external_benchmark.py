"""Offline adapter for original LongMemEval; lexical scores are not official QA scores."""
from __future__ import annotations
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics
import string


ORIGINAL_DATASET = "xiaowu0162/longmemeval-cleaned"
ORIGINAL_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
ORIGINAL_S_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_longmemeval(path):
    """Load original cleaned S/M/oracle JSON. Preserve source dates, strip annotations."""
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(raw, list):
        raise ValueError('LongMemEval source must be a JSON array')
    tasks, seen = [], set()
    for index, item in enumerate(raw):
        try:
            if not isinstance(item, dict):
                raise ValueError('entry must be an object')
            for field in ('question_id', 'question_type', 'question', 'question_date'):
                if not isinstance(item[field], str) or not item[field].strip():
                    raise ValueError(f'{field} must be a nonempty string')
            answer = item['answer']
            if isinstance(answer, bool) or not isinstance(answer, (str, int, float)) or not str(answer).strip():
                raise ValueError('answer must be a string or number')
            task_id = item['question_id']
            if task_id in seen:
                raise ValueError(f'duplicate question id: {task_id}')
            seen.add(task_id)
            ids, dates, histories, gold_ids = (item[key] for key in
                ('haystack_session_ids', 'haystack_dates', 'haystack_sessions', 'answer_session_ids'))
            if not all(isinstance(v, list) for v in (ids, dates, histories, gold_ids)):
                raise ValueError('session fields must be arrays')
            if not (len(ids) == len(dates) == len(histories)):
                raise ValueError('parallel session arrays have different lengths')
            if not all(isinstance(v, str) and v for v in ids + dates + gold_ids):
                raise ValueError('session ids and dates must be nonempty strings')
            if len(set(gold_ids)) != len(gold_ids):
                raise ValueError('duplicate session ids')
            if not set(gold_ids) <= set(ids):
                raise ValueError('gold session ids absent from history')
            sessions = []
            for session_id, date, turns in zip(ids, dates, histories):
                if not isinstance(turns, list):
                    raise ValueError('session must be an array of turns')
                texts = []
                for turn in turns:
                    if not isinstance(turn, dict) or turn.get('role') not in ('user', 'assistant', 'system') or not isinstance(turn.get('content'), str):
                        raise ValueError('turn requires a supported role and string content')
                    texts.append(f"{turn['role']}: {turn['content']}")
                sessions.append(dict(id=session_id, date=date, text='\n'.join(texts)))
            tasks.append(dict(id=task_id, family='abstention' if task_id.endswith('_abs') else item['question_type'],
                              question=item['question'], question_date=item['question_date'], gold=str(answer),
                              sessions=sessions, gold_session_ids=list(gold_ids), source_question_type=item['question_type']))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f'invalid LongMemEval entry {index}: {exc}') from exc
    return tasks


def stratified_sample(tasks, n, seed):
    """Largest-remainder proportional family allocation; independent of input order."""
    if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= len(tasks):
        raise ValueError('n must be an integer between zero and corpus size')
    if len({t['id'] for t in tasks}) != len(tasks):
        raise ValueError('task ids must be unique')
    if not tasks:
        return []
    groups = defaultdict(list)
    for task in tasks:
        groups[task['family']].append(task)
    quotas = {family: n * len(group) / len(tasks) for family, group in groups.items()}
    counts = {family: math.floor(value) for family, value in quotas.items()}
    for family in sorted(groups, key=lambda f: (-(quotas[f] - counts[f]), f))[:n - sum(counts.values())]:
        counts[family] += 1
    chosen = []
    for family in sorted(groups):
        group = sorted(groups[family], key=lambda t: t['id'])
        random.Random(f'{seed}:{family}').shuffle(group)
        chosen.extend(group[:counts[family]])
    return sorted(chosen, key=lambda t: t['id'])


def disjoint_dev_test(tasks, n_dev, n_test, seed=20261106):
    if n_dev < 0 or n_test < 0 or n_dev + n_test > len(tasks):
        raise ValueError('dev and test sizes exceed corpus')
    dev = stratified_sample(tasks, n_dev, f'{seed}:dev')
    dev_ids = {task['id'] for task in dev}
    test = stratified_sample([t for t in tasks if t['id'] not in dev_ids], n_test, f'{seed}:test')
    return dev, test


def build_external_messages(task, selected_session_ids=None):
    """Model-visible content allowlist: task question/date and original session text/date/id."""
    sessions = task['sessions']
    if selected_session_ids is not None:
        selected = set(selected_session_ids)
        if not selected <= {s['id'] for s in sessions}:
            raise ValueError('unknown selected session id')
        sessions = [s for s in sessions if s['id'] in selected]
    history = '\n\n'.join(f"[source session={s['id']} date={s['date']}]\n{s['text']}" for s in sessions)
    question_date = task.get('question_date', '')
    return [dict(role='system', content='Answer the question using the dated conversation history. If the history does not support an answer, say you do not know.'),
            dict(role='user', content=f"Conversation history:\n{history}\n\nQuestion date: {question_date}\nQuestion: {task['question']}")]


def _normalize(text):
    text = text.casefold().translate(str.maketrans('', '', string.punctuation))
    return ' '.join(re.sub(r'\b(a|an|the)\b', ' ', text).split())


def evaluate_answer(gold, response):
    """Local lexical diagnostics only; semantic correctness requires an independent judge."""
    expected, actual = _normalize(gold), _normalize(response)
    reference_tokens, answer_tokens = expected.split(), actual.split()
    overlap = sum((Counter(reference_tokens) & Counter(answer_tokens)).values())
    f1 = 2 * overlap / (len(reference_tokens) + len(answer_tokens)) if reference_tokens or answer_tokens else 1.0
    return dict(exact_normalized=int(expected == actual), proxy_token_f1=f1, needs_semantic_judge=True)


def evidence_recall(selected_session_ids, gold_session_ids):
    """Session recall; None when source contains no gold sessions (undefined denominator)."""
    gold = set(gold_session_ids)
    return len(set(selected_session_ids) & gold) / len(gold) if gold else None


def corpus_statistics(tasks):
    def summary(values):
        values = sorted(values)
        if not values:
            return dict(min=None, median=None, mean=None, p95=None, max=None, total=0)
        return dict(min=values[0], median=statistics.median(values), mean=statistics.mean(values),
                    p95=values[max(0, math.ceil(.95 * len(values)) - 1)], max=values[-1], total=sum(values))
    return dict(instances=len(tasks), families=dict(sorted(Counter(t['family'] for t in tasks).items())),
                tasks_with_repeated_session_ids=sum(len({s['id'] for s in t['sessions']}) < len(t['sessions']) for t in tasks),
                source_question_types=dict(sorted(Counter(t['source_question_type'] for t in tasks).items())),
                sessions_per_task=summary([len(t['sessions']) for t in tasks]),
                history_words_per_task=summary([sum(len(s['text'].split()) for s in t['sessions']) for t in tasks]),
                history_characters_per_task=summary([sum(len(s['text']) for s in t['sessions']) for t in tasks]),
                gold_sessions_per_task=summary([len(t['gold_session_ids']) for t in tasks]),
                length_definition='Whitespace words / Unicode characters of role-prefixed session text; not model tokens.')


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def prepare_external(directory, sourcepath, n=500, seed=20261106):
    """Freeze a corpus; certify original S only against trusted checksum/revision.

    Schema-compatible fixtures remain explicitly custom/unverified. Existing
    freezes are never rewritten, including freezes using an older schema.
    """
    directory, sourcepath = Path(directory), Path(sourcepath)
    tasks = load_longmemeval(sourcepath)
    selected = stratified_sample(tasks, n, seed)
    payload = _json_bytes(selected)
    manifest = dict(schema_version=2, benchmark='LongMemEval-compatible custom/unverified',
                    original_source_verified=False, source_filename=sourcepath.name,
                    source_sha256=sha256_file(sourcepath), source_instances=len(tasks), selected_instances=len(selected),
                    seed=seed, sampling='family proportional largest remainder; sorted-id seeded shuffle',
                    selected_ids=[t['id'] for t in selected], tasks_sha256=hashlib.sha256(payload).hexdigest(),
                    metrics='Local lexical proxies and session evidence recall; not official LongMemEval QA accuracy')
    source_manifest = sourcepath.parent / 'source_manifest.json'
    if source_manifest.exists():
        provenance = json.loads(source_manifest.read_text(encoding='utf-8'))
        if provenance.get('sha256') != manifest['source_sha256']:
            raise ValueError('source provenance checksum does not match dataset')
        manifest['source_provenance'] = provenance
        verified = (manifest['source_sha256'] == ORIGINAL_S_SHA256
                    and provenance.get('revision') == ORIGINAL_REVISION
                    and provenance.get('dataset') == ORIGINAL_DATASET
                    and len(tasks) == 500)
        if verified:
            manifest['benchmark'] = 'LongMemEval original cleaned'
            manifest['original_source_verified'] = True
    expected = {'tasks.json':payload, 'manifest.json':_json_bytes(manifest), 'corpus_statistics.json':_json_bytes(corpus_statistics(tasks))}
    if directory.exists() and any(directory.iterdir()):
        if any(not (directory/name).exists() or (directory/name).read_bytes() != data for name,data in expected.items()):
            raise ValueError('frozen external dataset differs or is incomplete; use a new directory')
        return manifest
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in expected.items():
        with (directory/name).open('xb') as stream:
            stream.write(data)
    return manifest
