"""Deterministic draft from measured evidence; LLM writing is a later stage."""
from research.artifacts import create_artifact, validate_artifact

CLAIM_FIELDS = ('tasks', 'correct', 'exact_accuracy', 'api_calls', 'total_tokens')
TITLE = 'Traceable Historical Context-Selection Pilot'


def claim_statement(policy, metric, value):
    formatted = f'{value:.1%}' if metric == 'exact_accuracy' else str(value)
    return f'{policy}: {metric} = {formatted}.'


def build_manuscript(evidence):
    validate_artifact(evidence, 'EvidenceBundle')
    claims = []
    for row in evidence['payload']['metrics']:
        for field in CLAIM_FIELDS:
            claims.append({'claim_id': f'{row["policy"]}.{field}', 'policy': row['policy'],
                           'metric': field, 'value': row[field],
                           'statement': claim_statement(row['policy'], field, row[field]),
                           'evidence_ids': [evidence['artifact_id']],
                           'scope': 'historical synthetic pilot', 'status': 'supported'})
    sections = [
        {'name': 'Scope', 'text': 'This is an offline, historical synthetic pilot report. '
         'It reuses saved experiments and does not report a new method, external review score, or competition score.', 'claim_ids': []},
        {'name': 'Methods', 'text': 'Answers were scored again against saved dataset labels. '
         'Each task-policy pair was checked for completeness, response identity, call sequence and provider usage. '
         'Full history is an unbounded reference; bounded policies use the legacy configuration. '
         'Exact project identifiers favor lexical retrieval. Original experiment code provenance was not recorded.', 'claim_ids': []},
        {'name': 'Results', 'text': '\n'.join(claim['statement'] for claim in claims),
         'claim_ids': [claim['claim_id'] for claim in claims]},
        {'name': 'Limitations', 'text': '\n'.join(evidence['payload']['limitations']), 'claim_ids': []},
        {'name': 'Resource accounting', 'text': 'Reported experiment tokens include all saved answer and summary calls. '
         'Historical drafting and smoke tests are excluded. This offline pipeline makes no model calls. '
         'Currency costs are unknown because no dated pricing evidence is supplied.', 'claim_ids': []},
    ]
    return create_artifact('ManuscriptBundle', {'title': TITLE, 'sections': sections, 'claims': claims,
                           'evidence_id': evidence['artifact_id'],
                           'draft_mode': 'deterministic_evidence_report', 'references': []},
                           [evidence['artifact_id']])


def render_markdown(manuscript):
    validate_artifact(manuscript, 'ManuscriptBundle')
    payload = manuscript['payload']
    lines = ['# ' + payload['title'], '', '**Historical evidence report; not a new submission paper.**', '']
    claims = {claim['claim_id']: claim for claim in payload['claims']}
    for section in payload['sections']:
        lines.extend(['## ' + section['name'], '', section['text'], ''])
        if section['name'] == 'Results':
            lines.extend(['| Method | Correct / tasks | Accuracy | API calls | API tokens |',
                          '|---|---:|---:|---:|---:|---:|'])
            policies = list(dict.fromkeys(c['policy'] for c in payload['claims']))
            for policy in policies:
                values = {key: claims[f'{policy}.{key}']['value'] for key in CLAIM_FIELDS}
                lines.append(f'| {policy} | {values["correct"]}/{values["tasks"]} | '
                             f'{values["exact_accuracy"]:.1%} | {values["api_calls"]} | {values["total_tokens"]} |')
            lines.extend(['', '### Claim-to-evidence links', ''])
            for claim_id in section['claim_ids']:
                lines.append(f'- `{claim_id}` → `{payload["evidence_id"]}` → policy metric row → run and raw call IDs.')
            lines.append('')
    lines.extend(['## Generation disclosure', '',
                  'A deterministic local template generated this report from independently rescored saved outputs. '
                  'No new LLM writing or external assessment was performed.', ''])
    return '\n'.join(lines)
