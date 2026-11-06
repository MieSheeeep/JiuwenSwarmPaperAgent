"""Small deterministic multi-hop QA benchmark used by the registered adapter."""

import hashlib
import string


def generate_qa_tasks(n=12, seed=20261106):
    if type(n) is not int or n < 1 or type(seed) is not int:
        raise ValueError('n must be a positive integer and seed must be an integer')
    tasks = []
    for index in range(n):
        suffix = hashlib.sha256(f'{seed}:{index}'.encode()).hexdigest()[:6]
        researcher, lab, city = f'Researcher-{suffix}', f'Lab-{suffix}', f'City-{suffix}'
        passages = [
            {'id': f'{index}:p0', 'text': f'{researcher} founded {lab}.', 'evidence': 'hop1'},
            {'id': f'{index}:p1', 'text': f'{lab} has its headquarters in {city}.', 'evidence': 'hop2'},
            {'id': f'{index}:p2', 'text': f'{lab} publishes reports about historical {city} weather.', 'evidence': 'distractor'},
        ]
        tasks.append({
            'id': f'qa-{index:03d}',
            'question': f'Which city is the headquarters of the lab founded by {researcher}? Return only the city name.',
            'gold': city,
            'passages': passages,
            'required_evidence': ['hop1', 'hop2'],
        })
    return tasks


def select_context(task, method):
    if method == 'single_pass':
        selected = task['passages'][:1]
    elif method == 'fixed_two_passages':
        selected = task['passages'][:2]
    elif method == 'adaptive_stop':
        selected = []
        evidence = set()
        for passage in task['passages']:
            selected.append(passage)
            evidence.add(passage['evidence'])
            if set(task['required_evidence']) <= evidence:
                break
    else:
        raise ValueError('Unknown context selection method: ' + str(method))
    evidence = {p['evidence'] for p in selected}
    return {'passages': selected,
            'selected_ids': [p['id'] for p in selected],
            'evidence_recall': len(evidence & set(task['required_evidence'])) / len(task['required_evidence'])}


def _normalize(answer):
    text = str(answer).strip().lower().translate(str.maketrans('', '', string.punctuation))
    return ' '.join(text.split())


def score_answer(answer, task, selected_ids=()):
    exact = _normalize(answer) == _normalize(task['gold'])
    selected = set(selected_ids)
    required_ids = {p['id'] for p in task['passages'] if p['evidence'] in task['required_evidence']}
    return {
        'exact': exact,
        'evidence_recall': len(selected & required_ids) / len(required_ids),
        'context_passages': len(selected),
    }
