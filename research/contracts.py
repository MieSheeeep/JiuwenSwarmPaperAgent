"""Versioned contracts for the implemented historical-evidence milestone."""
SCHEMA_VERSION = 1
REQUIRED_FIELDS = {
    'ResearchBrief': {'question', 'hypothesis', 'closest_work', 'source_ids', 'falsification', 'feasibility'},
    'ExperimentPlan': {'dataset_version', 'split', 'methods', 'budget_policy', 'metrics', 'acceptance', 'commands'},
    'RunManifest': {'origin', 'source_files', 'model_id', 'task_count', 'policies', 'call_ids', 'code_revision'},
    'EvidenceBundle': {'origin', 'metrics', 'total_api_calls', 'total_api_tokens', 'limitations', 'resource_accounting'},
    'ManuscriptBundle': {'title', 'sections', 'claims', 'evidence_id'},
    'ReviewDecision': {'passed', 'issues', 'coverage', 'external_scores'},
}


def validate_payload(kind, payload):
    if kind not in REQUIRED_FIELDS:
        raise ValueError(f'Unsupported artifact kind: {kind}')
    if not isinstance(payload, dict) or REQUIRED_FIELDS[kind] - payload.keys():
        raise ValueError(f'{kind} missing required payload fields')
