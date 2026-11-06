"""Synthetic structured-memory tasks and an independent bitemporal reference oracle.

Evidence metrics measure records available in the selected context, never citations
or model faithfulness. Dev and test streams are fixed independently of outcomes.
"""
import hashlib
import json
import random

FAMILIES = ('static', 'late_stale', 'historical', 'conflict', 'deletion_no_answer', 'paraphrase_distractors')
DEFAULT_SEEDS = (1729, 2718)


def reference_gold(records, query):
    """Resolve visible records without importing any framework selector code."""
    gold, evidence = {}, {}
    for attribute in query['attributes']:
        visible = [r for r in records if r['entity'] == query['entity']
                   and r['attribute'] == attribute and r['valid_at'] <= query['as_of']
                   and r['observed_at'] <= query['known_at']]
        if not visible:
            gold[attribute], evidence[attribute] = None, []
            continue
        latest = max(r['valid_at'] for r in visible)
        current = [r for r in visible if r['valid_at'] == latest]
        states = {(r['operation'], json.dumps(r['value'], sort_keys=True)) for r in current}
        gold[attribute] = current[0]['value'] if len(states) == 1 and current[0]['operation'] == 'set' else None
        evidence[attribute] = sorted(r['id'] for r in current)
    return gold, evidence


def generate_tasks(n_per_family=2, seeds=DEFAULT_SEEDS, split='test'):
    """Return reproducible JSON-serializable tasks; split namespaces separate RNGs."""
    if split not in ('dev', 'test') or n_per_family < 1 or not seeds:
        raise ValueError('Require dev/test split, positive n_per_family, and seeds')
    tasks = []
    for family in FAMILIES:
        for index in range(n_per_family):
            source_seed = seeds[index % len(seeds)]
            key = f'{split}:{source_seed}:{family}:{index}'
            seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big')
            rng = random.Random(seed)
            task_id = f'{split}-{family}-{seed:016x}'
            entity = f'project-{rng.randrange(10000, 99999)}'
            attrs = ['owner', 'region', 'stage']
            records = []

            def value(attribute):
                return f'{attribute}-{rng.randrange(100000, 999999)}'

            def add(ent, attr, val, valid, observed, operation='set'):
                records.append(dict(id=f'r{len(records):03}', entity=ent,
                                    attribute=attr, value=val, valid_at=valid,
                                    observed_at=observed, operation=operation))

            # A mixture of irrelevant entities, partial updates, and future facts.
            for j in range(30):
                distract_entity = entity if j % 5 == 0 else f'project-{rng.randrange(10000, 99999)}'
                distract_attr = f'archive_field_{j}' if distract_entity == entity else rng.choice(attrs)
                add(distract_entity, distract_attr, value(distract_attr), rng.randrange(1, 15), rng.randrange(1, 20))
            for attr in attrs:
                add(entity, attr, value(attr), 2, 2)
            query = dict(entity=entity, attributes=attrs, as_of=10, known_at=20)
            if family in ('late_stale', 'paraphrase_distractors'):
                for attr in attrs:
                    add(entity, attr, value(attr), 8, 9)
                    add(entity, attr, value(attr), 1, 19)
            elif family == 'historical':
                query['as_of'] = 5
                for attr in attrs:
                    add(entity, attr, value(attr), 8, 9)
                    add(entity, attr, value(attr), 4, 25)  # Not yet known.
            elif family == 'conflict':
                add(entity, 'owner', value('owner'), 8, 8)
                add(entity, 'owner', value('owner'), 8, 9)
            elif family == 'deletion_no_answer':
                add(entity, 'owner', None, 8, 9, 'delete')
                attrs.append('unrecorded_cost')
            # Arrival order is observed time, with independently shuffled ties.
            # Local IDs encode only that order, not family or generation recipe.
            rng.shuffle(records)
            records.sort(key=lambda record: record['observed_at'])
            for record_index, record in enumerate(records):
                record['id'] = f'r{record_index:03}'
            gold, evidence = reference_gold(records, query)
            stale = {}
            for attr in attrs:
                visible = [r for r in records if r['entity'] == entity and r['attribute'] == attr
                           and r['valid_at'] <= query['as_of'] and r['observed_at'] <= query['known_at']]
                latest = max((r['valid_at'] for r in visible), default=-1)
                stale[attr] = list(dict.fromkeys(r['value'] for r in visible
                                                if r['valid_at'] < latest and r['value'] is not None
                                                and r['value'] != gold[attr]))
            phrasing = ('Who is responsible, where is it assigned, and what phase has it reached?'
                        if family == 'paraphrase_distractors' else
                        f'What are the requested attributes for {entity} at the specified effective and observation cutoffs?')
            question = (f'{phrasing} Query metadata: {json.dumps(query, sort_keys=True)}. '
                        'Return JSON only: an object mapping every requested attribute to its value. '
                        'Use null for missing, deleted, or unresolved conflicting facts. Do not include citations.')
            tasks.append(dict(id=task_id, split=split, seed=seed, source_seed=source_seed,
                              family=family, records=records, query=query, question=question,
                              gold=gold, gold_evidence=evidence, stale_values=stale))
    return tasks


def score_memory_answer(text, task, selected_ids=()):
    """Score strict attribute JSON and selected-context evidence availability."""
    try:
        answer = json.loads(text)
        valid = isinstance(answer, dict)
    except (ValueError, TypeError):
        answer, valid = {}, False
    if not valid:
        answer = {}
    gold = task['gold']
    selected = set(selected_ids)
    # JSON types matter: True is not the numeric value 1.
    def equal(a, b):
        return type(a) is type(b) and a == b
    correct = {a: a in answer and equal(answer[a], v) for a, v in gold.items()}
    required = {r for ids in task['gold_evidence'].values() for r in ids}
    return dict(exact=valid and set(answer) == set(gold) and all(correct.values()),
                field_accuracy=sum(correct.values()) / len(gold) if gold else 1.0,
                correct_fields=sum(correct.values()), total_fields=len(gold),
                stale_fields=sum(a in answer and answer[a] is not None
                                 and any(equal(answer[a], v) for v in task.get('stale_values', {}).get(a, []) if v is not None)
                                 for a in gold),
                supported_fields=sum(correct[a] and answer[a] is not None
                                     and set(task['gold_evidence'].get(a, [])) <= selected for a in gold),
                nonnull_fields=sum(a in answer and answer[a] is not None for a in gold),
                refusal_correct=sum(correct[a] for a, v in gold.items() if v is None),
                refusal_total=sum(v is None for v in gold.values()),
                evidence_recall=len(required & selected)/len(required) if required else 1.0,
                evidence_available=len(required & selected), evidence_required=len(required),
                valid_json=valid)
