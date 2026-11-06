"""Finite scientific workflow over curated sources and a frozen experiment."""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess

from research.artifacts import create_artifact, digest, save_json
from research.memory_paper import REFERENCES, write_memory_paper
from research.memory_run import prepare_run, run_memory


def record_research_plan(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    brief = create_artifact('ResearchBrief', {
        'question':'Which source-evidence mechanisms preserve bitemporal query answers under equal context budgets?',
        'hypothesis':'Valid-time filtering can avoid late stale evidence; atomic conflict groups may help but must be tested against their removal.',
        'closest_work':[r['title'] for r in REFERENCES], 'source_ids':[r['url'] for r in REFERENCES],
        'falsification':'No benefit over the no-time/no-conflict variants or lexical baselines weakens the corresponding mechanism claim.',
        'feasibility':'Structured records, CPU selectors, fixed answering model, bounded API ledger.',
        'source':'Curated research from the approved design, not autonomous novelty discovery.',
    })
    save_json(directory/'research_brief.json',brief)
    plan = create_artifact('ExperimentPlan', {
        'dataset_version':manifest['dataset_sha256'],'split':{'dev':6,'test':24},
        'methods':sorted({r['policy'] for r in manifest['grid']}),
        'budget_policy':{'main_proxy_tokens':256,'sensitivity_proxy_tokens':512,
                         'total_admission_tokens':manifest['max_total_tokens'], 'full_reference':'unbounded'},
        'metrics':['exact_accuracy','micro_field_accuracy','stale_fields','context_evidence_recall','provider_tokens'],
        'acceptance':'Report every frozen condition including null/negative ablations; no heldout tuning or significance claim.',
        'commands':['python -m research.orchestrator --run-dir '+str(directory)+' --max-total-tokens '+str(manifest['max_total_tokens'])],
        'frozen_manifest_hash':digest(manifest), 'grid':manifest['grid'],
        'provenance_note':'Structured projection of the frozen manifest. The manifest, not this later artifact timestamp, proves the pre-call protocol.',
    },[brief['artifact_id']])
    save_json(directory/'experiment_plan.json',plan)


async def execute(run_dir, paper_dir, max_total_tokens, config_dir=None, analyze_existing=False, discovery_dir=None):
    run_dir, paper_dir = Path(run_dir), Path(paper_dir)
    run_dir.mkdir(parents=True,exist_ok=True)
    stage = 'experiment'
    try:
        research_pair = None
        if discovery_dir:
            from research.discovery import research_artifacts
            research_pair = research_artifacts(discovery_dir)
            if max_total_tokens != research_pair[1]['payload']['budget_policy']['max_total_tokens']:
                raise ValueError('Execution token ceiling must match the literature-derived experiment plan')
            # An old run cannot acquire a new, post-hoc research rationale.
            if (run_dir/'manifest.json').exists():
                expected = research_pair[0]['payload']['discovery_manifest_sha256']
                existing = run_dir/'research_brief.json'
                if not existing.exists() or json.loads(existing.read_text(encoding='utf-8'))['payload'].get('discovery_manifest_sha256') != expected:
                    raise ValueError('Discovery handoff requires a fresh or identically bound run directory')
        if not analyze_existing:
            from baseline.runtime import read_model_config
            config = read_model_config(config_dir)
            prepare_run(run_dir,max_total_tokens=max_total_tokens, model=config['model'],
                        provider=config['provider'],endpoint_hash=digest(config['api_base']))
            if research_pair:
                for name, artifact in zip(('research_brief.json', 'experiment_plan.json'), research_pair):
                    save_json(run_dir/name, artifact)
            else:
                record_research_plan(run_dir)
            await run_memory(run_dir,max_total_tokens=max_total_tokens,config_dir=config_dir)
        else:
            if not research_pair: record_research_plan(run_dir)
        stage = 'evidence_and_writing'
        result = await write_memory_paper(run_dir,paper_dir,max_total_tokens=max_total_tokens,config_dir=config_dir)
        stage = 'compilation'
        compilation = subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-disable-installer','paper.tex'],
                                     cwd=paper_dir,capture_output=True,text=True,timeout=90)
        (paper_dir/'compile_diagnostics.txt').write_text(compilation.stdout+compilation.stderr,encoding='utf-8')
        if compilation.returncode:
            raise ValueError('PDF compilation failed; diagnostics and source preserved')
        compilation = subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-disable-installer','paper.tex'],
                                     cwd=paper_dir,capture_output=True,text=True,timeout=90)
        (paper_dir/'compile_diagnostics.txt').write_text(compilation.stdout+compilation.stderr,encoding='utf-8')
        if compilation.returncode:
            raise ValueError('PDF reference pass failed')
        state = {'status':'succeeded','stage':'complete','paper':str(paper_dir/'paper.pdf'),
                 'official_scores':{'stanford':None,'paper_agent':None},'resources':result['resources']}
        save_json(run_dir/'workflow_state.json',state)
        return state
    except Exception as error:
        save_json(run_dir/'workflow_state.json',{'status':'failed','stage':stage,'error_type':type(error).__name__,'error':str(error)})
        raise


def main():
    parser = argparse.ArgumentParser(description='Bounded evidence-driven memory research release')
    parser.add_argument('--run-dir',default='output/memory_live_20261016')
    parser.add_argument('--paper-dir',default='output/memory_paper_20261016')
    parser.add_argument('--max-total-tokens',type=int,required=True)
    parser.add_argument('--config-dir')
    parser.add_argument('--analyze-existing',action='store_true')
    parser.add_argument('--discovery-dir', help='Validated literature-derived design for the registered memory protocol')
    args=parser.parse_args()
    try:
        result=asyncio.run(execute(args.run_dir,args.paper_dir,args.max_total_tokens,args.config_dir,args.analyze_existing,args.discovery_dir))
    except Exception as error:
        print(json.dumps({'status':'stopped','error_type':type(error).__name__,'reason':str(error)},ensure_ascii=False),flush=True)
        raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
