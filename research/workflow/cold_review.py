"""Fresh-context review lenses over an allowlisted, recorded manuscript artifact."""
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid
from research.artifacts import file_digest, save_json

LENSES = ('claim_support','method_correctness','comparison_fairness','reproducibility','significance')


def validate_adjudication(value, reports):
    findings = {f['id']:f for report in reports for f in report['findings']}
    decisions = value.get('adjudications', [])
    ids = [d['id'] for d in decisions]
    if len(ids) != len(set(ids)) or set(ids) != set(findings):
        raise ValueError('Meta-review must adjudicate every finding exactly once')
    for decision in decisions:
        if decision.get('status') not in ('confirmed','unsupported','underdetermined') or not decision.get('reason'):
            raise ValueError('Invalid finding adjudication')
        if decision['status'] != 'unsupported' and not all(decision.get(k) for k in ('repair','cost')):
            raise ValueError('Unresolved finding requires a repair and cost')
    if value.get('decision') not in ('accept','revise','stop') or not isinstance(value.get('issues'),list):
        raise ValueError('Invalid panel decision')
    unresolved = [d for d in decisions if d['status'] != 'unsupported' and findings[d['id']]['severity'] == 'major']
    if value['decision'] == 'accept' and unresolved:
        raise ValueError('Cannot accept with unresolved major findings')
    if value['decision'] == 'revise':
        if not value['issues'] or value.get('target') not in ('writing','analysis'):
            raise ValueError('Revision requires issues and a supported target')


async def cold_review(project, material, ask):
    project = Path(project)
    round_dir = project/'cold_reviews'/uuid.uuid4().hex
    artifact = round_dir/'artifact'
    artifact.mkdir(parents=True)
    # Only a public manuscript and its explicit supporting analysis enter the model context.
    public = {k:material[k] for k in ('manuscript','design','results','metrics','dataset')}
    public['manuscript']={k:public['manuscript'][k] for k in ('title','sections','references') if k in public['manuscript']}
    save_json(round_dir/'manuscript.json', public['manuscript'])
    save_json(artifact/'evidence.json', {k:v for k,v in public.items() if k != 'manuscript'})
    (artifact/'replay.py').write_bytes(Path(__file__).with_name('replay_review.py').read_bytes())
    (artifact/'README.txt').write_text('Run python -I replay.py. This rescoring artifact checks saved answers and aggregate metrics; '
        'it does not rerun the language model, validate retrieval or reproduce the full installation.\n', encoding='utf-8')
    manifest = {'context_boundary':'Fresh messages per lens; no author plans, history, feedback or ledger.',
        'model_diversity':'Single configured backend; different lenses are not independent model families.',
        'files':{p.relative_to(round_dir).as_posix():{'bytes':p.stat().st_size,
                 'modified_ns':p.stat().st_mtime_ns, 'sha256':file_digest(p)}
                 for p in sorted(round_dir.rglob('*')) if p.is_file()}}
    save_json(round_dir/'isolation.json', manifest)
    started = time.monotonic()
    command = [sys.executable, '-I', 'replay.py']
    try:
        proc = subprocess.run(command,cwd=artifact,capture_output=True,text=True,encoding='utf-8',timeout=30)
        execution = {'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}
    except subprocess.TimeoutExpired as exc:
        execution = {'exit_code':None,'stdout':str(exc.stdout or ''),'stderr':str(exc.stderr or ''),'timed_out':True}
    execution.update(command=command, platform=platform.platform(), python=platform.python_version(),
        seconds=time.monotonic()-started, scope='Offline saved-answer rescoring; no model rerun or clean-room install.')
    save_json(round_dir/'execution.json', execution)
    reports = []
    for lens in LENSES:
        report = await ask('Read as a cold reviewer with lens '+lens+'. Return findings (list of '
            '{issue, severity:major|minor, evidence, repair}). Evidence must locate text or numeric rows in '
            'supplied material. Read the manuscript and released analysis artifact only. A negative result '
            'is valid. Distinguish missing evidence from demonstrated error. No acceptance predictions. '
            'Artifact execution covers saved-answer rescoring only; explicitly state the remaining gaps.',
            {'lens':lens,'released_material':public,'isolation':manifest,'artifact_execution':execution},
            'review/cold/'+lens)
        if not isinstance(report.get('findings'),list):
            raise ValueError('Reviewer must return findings')
        for i,finding in enumerate(report['findings']):
            if not all(finding.get(k) for k in ('issue','evidence','repair')) or finding.get('severity') not in ('major','minor'):
                raise ValueError('Invalid review finding')
            finding['id'] = lens+'-'+str(i+1)
        reports.append({'lens':lens, **report})
        save_json(round_dir/(lens+'.json'), reports[-1])
    value = await ask('Adjudicate every finding independently. Return decision (accept|revise|stop), '
        'issues (list of actionable unresolved issues), target (writing|analysis if revise), '
        'adjudications (list of {id,status:confirmed|unsupported|underdetermined,reason,repair,cost}). '
        'Do not average votes. Accept only with no unresolved major findings. Negative results are valid; '
        'no official review score or acceptance prediction. New experiments require a later author decision.',
        {'released_material':public,'reports':reports,'artifact_execution':execution},'review/cold/meta')
    save_json(round_dir/'meta_capture.json', value)
    validate_adjudication(value, reports)
    if execution['exit_code'] != 0:
        value.update(decision='revise',target='analysis',issues=[*value['issues'],'Released saved-answer rescoring failed; inspect execution.json.'])
    value.update(round=round_dir.relative_to(project).as_posix(),
                 review_scope='Single-backend cold lenses; saved-answer artifact execution only.')
    save_json(round_dir/'decision.json', value)
    return value
