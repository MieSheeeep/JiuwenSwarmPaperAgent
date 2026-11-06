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
    init.add_argument('--max-tokens',type=int,default=250000);init.add_argument('--max-calls',type=int,default=200)
    for command in ('status','pause','resume','schema'):subs.add_parser(command)
    ingest=subs.add_parser('import');ingest.add_argument('--stage',choices=STAGES,required=True);ingest.add_argument('--file',required=True)
    invalidate=subs.add_parser('invalidate');invalidate.add_argument('--stage',choices=STAGES,required=True);invalidate.add_argument('--reason',required=True)
    run=subs.add_parser('advance');run.add_argument('--until',choices=STAGES)
    args=parser.parse_args()
    workflow=(Workflow.create(args.project,args.topic,max_calls=args.max_calls,max_tokens=args.max_tokens)
              if args.command=='init' else Workflow(args.project))
    if args.command=='schema':print(json.dumps(REQUIRED,ensure_ascii=False,indent=2));return
    if args.command=='import':
        workflow.accept(args.stage,StageResult(json.loads(Path(args.file).read_text(encoding='utf-8'))))
    elif args.command=='pause':workflow.pause()
    elif args.command=='resume':workflow.resume()
    elif args.command=='invalidate':workflow.invalidate(args.stage,reason=args.reason)
    elif args.command=='advance':asyncio.run(workflow.run(Registry(),until=args.until))
    workflow.verify();print(json.dumps(workflow.status(),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
