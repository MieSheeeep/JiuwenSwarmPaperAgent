"""Deterministic synthetic history tasks and independent field-wise scoring."""
import json
import random
import re

FIELDS = ('port', 'timeout', 'owner')


def task_payload(task):
    return {key: task[key] for key in ('history', 'question')}


def infer_gold(history, project):
    state = dict.fromkeys(FIELDS)
    for line in history:
        if re.search(r'\bproject\s+' + re.escape(project) + r'\b', line):
            for key, value in re.findall(r'\b(port|timeout|owner)=([a-z0-9]+)', line):
                state[key] = int(value) if key != 'owner' else value
    return state


def generate_tasks(n=24, seed=20261008):
    rng = random.Random(seed)
    tasks = []
    owners = ['alex', 'blair', 'casey', 'drew', 'ellis', 'frank', 'gray', 'harper']
    for i in range(n):
        family = ('lookup', 'revision', 'partial')[i % 3]
        project = f'P{1000+i}'
        position = ('early', 'middle', 'late')[(i // 3) % 3]
        rows = []
        for j in range(60):
            p = f'P{2000+i*100+j}'
            rows.append(f'Event {j:02d}: project {p} port={rng.randint(7000,9999)} '
                        f'timeout={rng.randint(10,90)} owner={rng.choice(owners)}. '
                        'Deployment note: validate staging metrics, preserve rollback artifacts, '
                        'check health probes, review service routing, and confirm incident contacts '
                        'before the next scheduled maintenance window.')
        initial = {'port': rng.randint(7000,9999), 'timeout': rng.randint(10,90), 'owner':rng.choice(owners)}
        anchor = {'early': 2, 'middle': 27, 'late': 53}[position]
        rows[anchor] = f'Event {anchor:02d}: project {project} ' + ' '.join(f'{k}={v}' for k,v in initial.items()) + '.'
        if family == 'revision':
            update = {'port': initial['port']+1, 'timeout':initial['timeout']+2,
                      'owner': owners[(owners.index(initial['owner'])+1)%len(owners)]}
            rows[anchor+2] = f'Event {anchor+2:02d}: project {project} confirmed revision ' + ' '.join(f'{k}={v}' for k,v in update.items()) + '.'
        if family == 'partial':
            rows[anchor+2] = f'Event {anchor+2:02d}: project {project} partial update timeout={initial["timeout"]+3}; other fields unchanged.'
            rows[anchor+3] = f'Event {anchor+3:02d}: project {project} partial update owner={owners[(owners.index(initial["owner"])+2)%len(owners)]}; other fields unchanged.'
        question = (f'What are the final confirmed settings for project {project}? '
                    'Process records in event order; later updates replace only the fields they mention. '
                    'Return exactly one JSON object with keys port, timeout, owner. '
                    'Use integers for port and timeout, lowercase string for owner, '
                    'and null for any field not supported by the provided history.')
        tasks.append({'id':f'task-{i:03d}','family':family,'position':position,
                      'project':project,'history':rows,'question':question,
                      'gold':infer_gold(rows,project)})
    return tasks


def score_answer(text, gold):
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned)
    try:
        obj = json.loads(cleaned)
    except (ValueError, TypeError):
        obj = None
    correct = {}
    for key in FIELDS:
        value = obj.get(key) if isinstance(obj, dict) and key in obj else object()
        valid_type = (type(value) is int if key != 'owner' else isinstance(value,str)) if gold[key] is not None else value is None
        correct[key] = valid_type and value == gold[key]
    return {'exact':all(correct.values()),'fields':correct,'parsed':obj,
            'valid_json':isinstance(obj,dict)}
