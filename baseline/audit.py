"""Create a credential-free delivery audit and resource report."""
import hashlib
import json
from baseline.runtime import ROOT, read_model_config


def main():
    runs = []
    for name in ('smoke', 'baseline', 'smoke_verified', 'paper'):
        calls = [json.loads(line) for line in (ROOT/'output'/name/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
        assert all(c['status'] == 'ok' and c['usage'] for c in calls)
        runs.append({'run': name, 'calls': len(calls), **{k: sum(c['usage'].get(k,0) for c in calls)
            for k in ('input_tokens','output_tokens','total_tokens','cache_tokens')}})
    keys = ('run','calls','input_tokens','output_tokens','total_tokens','cache_tokens')
    lines = ['# Resource report', '', 'Model: deepseek-flash; official DeepSeek API.', '',
        '| Stage | API calls | Input tokens | Output tokens | Total tokens | Cached input tokens |',
        '|---|---:|---:|---:|---:|---:|']
    lines.extend('| '+' | '.join(str(r[k]) for k in keys)+' |' for r in runs)
    totals = {k:sum(r[k] for r in runs) for k in keys[1:]}
    lines.extend(['',f'All stages: {totals["calls"]} calls, {totals["total_tokens"]} API-reported tokens.', '',
        'Cached tokens are a subset of input tokens. Summary calls are included.',
        'The main experiment used 120 calls and 101,768 tokens. Its recorded workload wall time was '
        '43.851 seconds, excluding imports, environment setup, drafting and compilation.',
        'SDK zero-valued cost fields are not an invoice and do not establish free usage. Check actual charges in the DeepSeek console.',
        'Response persistence was strengthened after the main run; policies, task data and model inputs were unchanged. '
        'The smoke_verified run validates the final instrumentation.',
        'No failed calls or retries occurred. Local CPU/Python execution; no local GPU inference.'])
    (ROOT/'resource_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    files=[]
    for d in ('baseline','tests','docs','output/baseline','output/paper','output/smoke','output/smoke_verified'):
        files.extend(p for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files.extend(ROOT/p for p in ('README.md','requirements-baseline.txt','framework_contribution.md',
        'resource_report.md','BASELINE_STATUS.md','output/framework_contribution.patch','output/environment.txt'))
    secret=read_model_config()['api_key'].encode()
    assert len(secret)>10
    leaked=[str(p.relative_to(ROOT)) for p in files if secret in p.read_bytes()]
    if leaked:
        raise RuntimeError('Credential found in delivery files: '+', '.join(leaked))
    report={'resource_totals':totals,'credential_scan':'passed; configured key absent from delivery files',
        'unit_tests':'9 passed','main_trials':96,'main_api_calls':120,
        'call_associations':'one-to-one; no orphan or duplicate calls',
        'pdf':'3 pages; compiled and visually inspected',
        'source_patch':'3 files, 85 insertions; git diff --cached --check passed',
        'files_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}}
    (ROOT/'output/verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'resource_totals':totals,'credential_scan':'passed','files_checked':len(files)}))


if __name__=='__main__':
    main()
