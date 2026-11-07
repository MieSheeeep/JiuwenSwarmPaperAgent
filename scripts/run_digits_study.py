"""Run a fresh digits experiment and Flash-authored manuscript; no old study inputs."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.workflow import Workflow
from research.workflow.digits_profile import DigitsProfile
from research.artifacts import save_json


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',default='output/framework_digits_20261107')
    parser.add_argument('--enable-model',action='store_true')
    parser.add_argument('--until',default='export')
    args=parser.parse_args()
    if not args.enable_model:parser.error('Use --enable-model to authorize Flash calls; local training has no API cost')
    project=Path(args.project).resolve()
    w=Workflow(project) if (project/'workflow.json').exists() else Workflow.create(project,
        'Clean-validation rejection thresholds under handwritten-digit image corruption',
        constraints={'study':'digits-selective-v1','model':'deepseek-flash','fresh_experiment':True},
        max_tokens=100000,max_calls=16,max_revisions=2)
    profile=DigitsProfile(project)
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):await w.run(profile.registry(),until=args.until)
    save_json(project/'run_status.json',w.status())
    print(json.dumps(w.status()),flush=True)
    if w.state['stages']['writing']['status']=='completed' and w.state['status']!='completed':
        manuscript=w.artifact('writing')['payload']
        status='requires_revision' if w.state['stages']['review']['status']=='completed' else 'pending_review'
        compiled=profile.compiler({**manuscript,'draft_status':status})
        from research.workflow.delivery import inspect_pdf
        pdf=next(name for name in compiled['files'] if name.endswith('.pdf'))
        inspection=inspect_pdf(project/pdf,project/'workspace/paper/previews')
        save_json(project/'preview_status.json',{'compilation':compiled,'inspection':inspection,'status':w.status()})


if __name__=='__main__':asyncio.run(main())
