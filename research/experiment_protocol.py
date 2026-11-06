"""Allow-list and integrity checks for non-memory research experiments."""

from research.artifacts import digest


ADAPTIVE_QA_PROTOCOL = {
    'dataset': 'synthetic-multihop-qa-v1',
    'seed': 20261106,
    'tasks': 12,
    'methods': ['single_pass', 'fixed_two_passages', 'adaptive_stop'],
    'answer_max_tokens': 64,
    'evidence_required': 2,
}

REGISTERED_ADAPTERS = {'adaptive-qa-v1': ADAPTIVE_QA_PROTOCOL}


def validate_experiment_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError('Experiment plan must be an object')
    if plan.get('adapter') not in REGISTERED_ADAPTERS:
        raise ValueError('Unknown experiment adapter; implementation is required before execution')
    if plan.get('protocol') != REGISTERED_ADAPTERS[plan['adapter']]:
        raise ValueError('Experiment protocol does not match the registered adapter')
    methods = plan.get('methods')
    if methods != list(ADAPTIVE_QA_PROTOCOL['methods']):
        raise ValueError('Methods must match the registered adaptive QA protocol')
    data_split = plan.get('data_split')
    if not isinstance(data_split, dict) or data_split.get('test') != ADAPTIVE_QA_PROTOCOL['tasks']:
        raise ValueError('The frozen test split must contain exactly the registered tasks')
    cost = plan.get('cost_controls')
    if not isinstance(cost, dict) or any(type(cost.get(k)) is not int or cost[k] <= 0
                                         for k in ('max_total_tokens', 'max_calls')):
        raise ValueError('Positive token and call ceilings are required')
    if cost['max_calls'] < ADAPTIVE_QA_PROTOCOL['tasks'] * len(methods):
        raise ValueError('Call ceiling is below the frozen experiment grid')
    commands = plan.get('commands')
    if commands:
        raise ValueError('Registered experiments do not execute plan-supplied commands')
    for key in ('falsification', 'analysis'):
        if not isinstance(plan.get(key), str) or not plan[key].strip():
            raise ValueError('Missing experiment field: ' + key)
    return plan


def result_hash(row):
    """Hash a result row while excluding its self-referential hash field."""
    return digest({key: value for key, value in row.items() if key != 'result_hash'})
