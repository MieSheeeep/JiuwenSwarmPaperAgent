"""Mechanical consistency review, kept separate from external scientific scores."""
from research.artifacts import create_artifact, validate_artifact
from research.writer import build_manuscript, claim_statement, CLAIM_FIELDS


def review_manuscript(manuscript, evidence):
    validate_artifact(manuscript, 'ManuscriptBundle')
    validate_artifact(evidence, 'EvidenceBundle')
    issues = []

    def issue(code, message, claim_id=None):
        issues.append({'code': code, 'severity': 'error', 'message': message,
                       'claim_id': claim_id, 'action': 'rebuild_from_evidence'})

    payload = manuscript['payload']
    if payload['evidence_id'] != evidence['artifact_id'] or manuscript['parent_ids'] != [evidence['artifact_id']]:
        issue('evidence_link', 'Manuscript refers to different evidence')
    metrics = {row['policy']: row for row in evidence['payload']['metrics']}
    expected_ids = {f'{policy}.{field}' for policy in metrics for field in CLAIM_FIELDS}
    seen = []
    for claim in payload['claims']:
        claim_id = claim.get('claim_id')
        seen.append(claim_id)
        policy, field = claim.get('policy'), claim.get('metric')
        if policy not in metrics or field not in CLAIM_FIELDS or claim_id != f'{policy}.{field}':
            issue('claim_reference', 'Unknown policy, metric or claim ID', claim_id)
            continue
        value = metrics[policy][field]
        if type(claim.get('value')) is not type(value) or claim['value'] != value:
            issue('claim_value', 'Claim value disagrees with measured evidence', claim_id)
        if claim.get('statement') != claim_statement(policy, field, value):
            issue('claim_statement', 'Statement does not match measured value', claim_id)
        if (claim.get('evidence_ids') != [evidence['artifact_id']] or
                claim.get('status') != 'supported' or claim.get('scope') != 'historical synthetic pilot'):
            issue('claim_scope', 'Claim scope, status or evidence link differs', claim_id)
    if len(seen) != len(expected_ids) or set(seen) != expected_ids:
        issue('claim_completeness', 'Missing, duplicate or unexpected claims')
    canonical = build_manuscript(evidence)['payload']
    if payload['sections'] != canonical['sections'] or payload.get('title') != canonical['title']:
        issue('unregistered_prose', 'This milestone only certifies the evidence-bound template; changed prose needs separate review')
    if payload.get('references') != [] or payload.get('draft_mode') != canonical['draft_mode']:
        issue('unverified_metadata', 'Unexpected references or writing mode')
    return create_artifact('ReviewDecision', {
        'passed': not issues, 'issues': issues,
        'coverage': ['artifact integrity', 'claim values and evidence links',
                     'claim completeness and scope', 'deterministic prose and table inputs'],
        'not_covered': ['scientific novelty', 'citation truth', 'external reviewer scores',
                        'authenticity of original API execution', 'free-form LLM prose'],
        'external_scores': {'stanford_agentic_reviewer': None, 'paper_evaluation_agent': None},
        'stop_reason': 'mechanical_checks_passed' if not issues else 'evidence_or_manuscript_mismatch',
    }, [manuscript['artifact_id'], evidence['artifact_id']])
