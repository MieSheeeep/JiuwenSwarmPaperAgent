"""Run the frozen local pilot audit and source-bound Flash manuscript."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.workflow import Workflow
from research.workflow.pilot_pruning_profile import PilotPruningProfile
from research.artifacts import save_json


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',default='output/framework_idea_gate_20261108')
    parser.add_argument('--until',default='export')
    parser.add_argument('--enable-model',action='store_true')
    args=parser.parse_args()
    if args.until in ('writing','review','export') and not args.enable_model:parser.error('--enable-model required for manuscript/review API calls')
    project=Path(args.project).resolve();w=Workflow(project);profile=PilotPruningProfile(project)
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):await w.run(profile.registry(),until=args.until)
    save_json(project/'run_status.json',w.status());print(json.dumps(w.status()),flush=True)
    if w.state['stages']['writing']['status']=='completed' and w.state['status']!='completed':
        manuscript={**w.artifact('writing')['payload'],'draft_status':'requires_revision' if w.state['stages']['review']['status']=='completed' else 'pending_review'}
        result=profile.compile_report(manuscript)
        from research.workflow.delivery import inspect_pdf
        result['inspection']=inspect_pdf(project/'workspace/paper/paper.pdf',project/'workspace/paper/previews')
        save_json(project/'preview_status.json',result)


if __name__=='__main__':asyncio.run(main())
