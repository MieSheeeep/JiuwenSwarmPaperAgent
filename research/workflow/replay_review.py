"""Offline released analysis artifact. Run: python -I replay.py (no API required)."""
import collections
import json
from pathlib import Path
import re
import string


def normalized(text):
    text = ''.join(c for c in text.lower() if c not in string.punctuation)
    return re.sub(r'\b(a|an|the)\b', ' ', text).split()


def main():
    data = json.loads(Path('evidence.json').read_text(encoding='utf-8'))
    tasks = {t['id']:t for t in data['dataset'] if t['split'] == 'test'}
    if set(tasks) != set(data['design']['split']['test']):
        raise ValueError('Test split mismatch')
    rows = data['results']
    pairs = [(r['task_id'],r['method']) for r in rows]
    expected = {(task,method) for task in tasks for method in data['design']['methods']}
    if len(set(pairs)) != len(pairs) or set(pairs) != expected:
        raise ValueError('Incomplete or duplicate task/method grid')
    for row in rows:
        prediction, gold = normalized(row['answer']), normalized(tasks[row['task_id']]['answer'])
        exact = float(prediction == gold)
        overlap = sum((collections.Counter(prediction) & collections.Counter(gold)).values())
        f1 = 2*overlap/(len(prediction)+len(gold)) if overlap else 0.0
        # Match registered QA special-answer handling.
        if prediction in (['yes'],['no'],['noanswer']) or gold in (['yes'],['no'],['noanswer']):
            f1 = exact
        if abs(row['em']-exact)>1e-12 or abs(row['f1']-f1)>1e-12:
            raise ValueError('Saved answer score mismatch')
    metrics = {}
    for method in data['design']['methods']:
        group = [r for r in rows if r['method'] == method]
        metrics[method] = {'n':len(group), 'exact':sum(r['em'] for r in group)/len(group),
            'f1':sum(r['f1'] for r in group)/len(group),
            'mean_documents':sum(r['documents'] for r in group)/len(group),
            'provider_tokens':sum(r['tokens'] for r in group)}
    if metrics != data['metrics']:
        raise ValueError('Aggregate metric mismatch')
    print(json.dumps({'status':'verified', 'scope':'saved-answer rescoring only', 'metrics':metrics}))


if __name__ == '__main__':
    main()
