"""Offline-first project CLI; no implicit model calls."""
import argparse
import asyncio
import json
from pathlib import Path
from .engine import Workflow, StageResult, STAGES, REQUIRED
from .registry import Registry


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',required=True)
    subs=parser.add_subparsers(dest='command',required=True)
    init=subs.add_parser('init');init.add_argument('--topic',required=True)
    init.add_argument('--constraints',help='JSON constraints file, including dataset_path and literature_query')
    init.add_argument('--max-tokens',type=int,default=250000);init.add_argument('--max-calls',type=int,default=500)
    for command in ('status','pause','resume','schema'):subs.add_parser(command)
    ingest=subs.add_parser('import');ingest.add_argument('--stage',choices=STAGES,required=True);ingest.add_argument('--file',required=True)
    invalidate=subs.add_parser('invalidate');invalidate.add_argument('--stage',choices=STAGES,required=True);invalidate.add_argument('--reason',required=True)
    run=subs.add_parser('advance');run.add_argument('--until',choices=STAGES)
    connected=subs.add_parser('run')
    connected.add_argument('--until',choices=STAGES)
    connected.add_argument('--enable-model',action='store_true',help='Explicitly enable configured model calls')
    connected.add_argument('--config-dir')
    review=subs.add_parser('attach-review')
    review.add_argument('--pdf',required=True);review.add_argument('--token-file',required=True)
    review.add_argument('--receipt',required=True)
    inspect=subs.add_parser('inspect-paper');inspect.add_argument('--pdf',required=True)
    approve=subs.add_parser('approve-paper');approve.add_argument('--pdf',required=True);approve.add_argument('--note',required=True)
    subs.add_parser('release')
    args=parser.parse_args()
    workflow=(Workflow.create(args.project,args.topic,
              constraints=json.loads(Path(args.constraints).read_text(encoding='utf-8')) if args.constraints else {},
              max_calls=args.max_calls,max_tokens=args.max_tokens)
              if args.command=='init' else Workflow(args.project))
    if args.command=='schema':print(json.dumps(REQUIRED,ensure_ascii=False,indent=2));return
    if args.command=='attach-review':
        from .delivery import bind_review
        print(json.dumps(bind_review(workflow.directory,args.pdf,args.token_file,args.receipt),indent=2));return
    if args.command=='inspect-paper':
        from .delivery import inspect_pdf
        print(json.dumps(inspect_pdf(args.pdf,workflow.directory/'workspace/paper/previews'),indent=2));return
    if args.command=='approve-paper':
        from .delivery import approve_visual
        print(json.dumps(approve_visual(workflow.directory,args.pdf,args.note),indent=2));return
    if args.command=='release':
        from .delivery import build_release
        print(json.dumps(build_release(workflow.directory,workflow.artifact('export')['payload']),indent=2));return
    if args.command=='import':
        workflow.accept(args.stage,StageResult(json.loads(Path(args.file).read_text(encoding='utf-8'))))
    elif args.command=='pause':workflow.pause()
    elif args.command=='resume':workflow.resume()
    elif args.command=='invalidate':workflow.invalidate(args.stage,reason=args.reason)
    elif args.command=='advance':asyncio.run(workflow.run(Registry(),until=args.until))
    elif args.command=='run':
        if not args.enable_model:
            parser.error('run requires --enable-model; use status/advance for offline inspection')
        from .profile import ConnectedProfile
        profile=ConnectedProfile(workflow.directory,config_dir=args.config_dir)
        asyncio.run(workflow.run(profile.registry(),until=args.until))
    workflow.verify();print(json.dumps(workflow.status(),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
