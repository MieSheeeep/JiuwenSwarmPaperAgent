"""Run with: .venv/Scripts/python -m baseline.run --tasks 24 --output output/baseline"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import random
import time

from baseline.dataset import generate_tasks
from baseline.runtime import ModelRuntime, read_model_config

POLICIES = ['full','recent','retrieve','retrieve_summary']


async def run(args):
    directory = Path(args.output)
    directory.mkdir(parents=True,exist_ok=True)
    tasks = generate_tasks(args.tasks,args.seed)
    dataset = json.dumps(tasks,ensure_ascii=False,indent=2)
    dataset_path = directory/'dataset.json'
    if dataset_path.exists() and dataset_path.read_text(encoding='utf-8') != dataset:
        raise ValueError('Existing run has a different dataset; choose a new output directory')
    dataset_path.write_text(dataset,encoding='utf-8')
    config = read_model_config(args.config_dir)
    manifest = {'model':config['model'],'provider':config['provider'],
                'api_base':config['api_base'],'seed':args.seed,'tasks':args.tasks,
                'policies':POLICIES,'history_budget_proxy_tokens':512,
                'summary_budget_proxy_tokens':256,'tokenizer_proxy':'cl100k_base',
                'temperature':0,'top_p':1,'thinking':'disabled',
                'answer_max_tokens':160,'summary_max_tokens':384,'concurrency':args.concurrency,
                'dataset_sha256':hashlib.sha256(dataset.encode()).hexdigest(),
                'note':'Synthetic pilot; full-history reference is unbounded. '
                       'No held-out benchmark or novelty claim. Summary overhead is included.'}
    manifest_path = directory/'manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text(encoding='utf-8')) != manifest:
        raise ValueError('Existing run has different settings; choose a new output directory')
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    runtime = ModelRuntime(config,directory)
    results_path = directory/'results.jsonl'
    existing = [json.loads(line) for line in results_path.read_text(encoding='utf-8').splitlines()] if results_path.exists() else []
    done = {(r['task_id'],r['policy']) for r in existing}
    sem = asyncio.Semaphore(args.concurrency)
    count = len(existing)
    started = time.perf_counter()
    async def execute(task,policy):
        nonlocal count
        async with sem:
            try:
                row = await runtime.answer(task,policy)
            except Exception as error:
                # Do not expose third-party exception text or private configuration.
                row = {'task_id':task['id'],'policy':policy,'family':task['family'],
                       'position':task['position'],'status':'error','error_type':type(error).__name__,
                       'score':{'exact':False,'fields':{}},
                       'call_ids':[c['id'] for c in runtime.calls
                                   if c['tag'].startswith(f'{task["id"]}/{policy}/')]}
            with results_path.open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(row,ensure_ascii=False)+'\n')
            count += 1
            print(f'{count}/{args.tasks*4} {task["id"]} {policy}: {row["status"]}, exact={row["score"]["exact"]}',flush=True)
            return row
    rng = random.Random(args.seed)
    pending = []
    for task in tasks:
        policies = POLICIES.copy()
        rng.shuffle(policies)
        pending.extend(execute(task,p) for p in policies if (task['id'],p) not in done)
    await asyncio.gather(*pending)
    (directory/'wall_time.json').write_text(json.dumps({'this_invocation_seconds':time.perf_counter()-started}),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tasks',type=int,default=24)
    parser.add_argument('--seed',type=int,default=20261008)
    parser.add_argument('--output',default='output/baseline')
    parser.add_argument('--concurrency',type=int,default=2)
    parser.add_argument('--config-dir')
    args=parser.parse_args()
    asyncio.run(run(args))


if __name__=='__main__':
    main()
