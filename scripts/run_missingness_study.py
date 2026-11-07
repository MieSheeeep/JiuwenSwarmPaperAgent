"""Fresh mask-integrated validation research, CPU experiments and Flash authoring."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.workflow import Workflow
from research.workflow.missingness_profile import MissingnessProfile
from research.artifacts import save_json


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',default='output/framework_missingness_20261107')
    parser.add_argument('--enable-model',action='store_true');parser.add_argument('--until',default='export')
    args=parser.parse_args()
    if not args.enable_model:parser.error('Explicit --enable-model required for Flash authoring')
    project=Path(args.project).resolve()
    w=Workflow(project) if (project/'workflow.json').exists() else Workflow.create(project,
        'Mask-integrated validation for selecting linear predictors under missingness-rate shift',
        constraints={'study':'mask-integrated-linear-v1','fresh_experiment':True,'model':'deepseek-flash'},max_tokens=100000,max_calls=16,max_revisions=2)
    profile=MissingnessProfile(project)
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):await w.run(profile.registry(),until=args.until)
    save_json(project/'run_status.json',w.status());print(json.dumps(w.status()),flush=True)
    if w.state['stages']['writing']['status']=='completed' and w.state['status']!='completed':
        m=w.artifact('writing')['payload'];m={**m,'draft_status':'requires_revision' if w.state['stages']['review']['status']=='completed' else 'pending_review'}
        result=profile.compiler(m)
        from research.workflow.delivery import inspect_pdf
        pdf=next(k for k in result['files'] if k.endswith('.pdf'))
        inspection=inspect_pdf(project/pdf,project/'workspace/paper/previews')
        save_json(project/'preview_status.json',{'compilation':result,'inspection':inspection,'status':w.status()})


if __name__=='__main__':asyncio.run(main())
