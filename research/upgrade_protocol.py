"""Predeclared upgrade protocol, new data and non-causal paired analysis."""
import hashlib
import json
from pathlib import Path
import random
import statistics

from research.artifacts import digest, file_digest, save_json
from research.memory_dataset import generate_tasks, reference_gold
from research.memory_run import answer_messages

ROOT=Path(__file__).resolve().parents[1]
READERS=('baseline','conflict_aware','reflection')
VARIANTS=(('full','rank_first'),('recent','rank_first'),('bm25','rank_first'),('dense','rank_first'),
          ('hybrid','rank_first'),('versioned','smaller_first'),('versioned','utility_dp'),
          ('versioned','diverse'),('no_time','smaller_first'),('no_conflict','smaller_first'))


def build_dataset():
    tasks=generate_tasks(2,(4901,4902),'dev')+generate_tasks(12,(61001,61002,61003),'test')
    for split,n,offset in [('dev',4,490100),('test',12,610100)]:
        for i in range(n):
            rng=random.Random(offset+i);entity=f'packing-project-{offset+i}'
            attributes=[f'field_{j:02}' for j in range(8)]
            records=[]
            for a,attribute in enumerate(attributes):
                for version in range(3):
                    records.append({'id':f'r{len(records):03}','entity':entity,'attribute':attribute,
                                    'value':f'value-{rng.randrange(10000,99999)}'+(' descriptive'*((a+i)%5)),
                                    'valid_at':version+1,'observed_at':version+2,'operation':'set'})
                if (a+i)%3==0:
                    records.append({**records[-1],'id':f'r{len(records):03}','value':f'competing-{rng.randrange(10000,99999)}','observed_at':8})
            rng.shuffle(records)
            for j,r in enumerate(records):r['id']=f'r{j:03}'
            query={'entity':entity,'attributes':attributes,'as_of':5,'known_at':10}
            gold,evidence=reference_gold(records,query)
            tasks.append({'id':f'{split}-packing-{offset+i}','split':split,'family':'packing_stress',
                          'source_seed':offset+i,'seed':offset+i,'records':records,'query':query,
                          'question':'Report every requested field from visible maximal-time evidence. Unresolved conflicts require null.',
                          'gold':gold,'gold_evidence':evidence,'stale_values':{}})
    return tasks


def synthetic_messages(task,text,reader):
    if reader not in READERS:raise ValueError('Unknown reader')
    messages=answer_messages(task,text)
    if reader!='baseline':
        messages[0]['content']+=(' Before returning JSON, internally check each requested attribute: filter entity and both cutoffs; '
            'identify maximal valid_at; compare ALL records at that time. Different values, or simultaneous set/delete, '
            'are unresolved: return null. Do not break ties by observed_at or source order. If records at maximum time '
            'are all deletion, return null. Do not infer a value from omitted evidence. Keep reasoning internal; final JSON only.')
    return messages


def code_hashes():
    files=['research/upgrade_protocol.py','research/review_upgrade.py','research/advanced_retrieval.py',
           'research/external_benchmark.py','research/model_gateway.py','research/memory_dataset.py',
           'research/memory_run.py','baseline/runtime.py',
           'research/agent_invocation.py','research/upgrade_analysis.py',
           'research/retrieval_audit.py',
           'research/jsonl_ledger.py','research/spend_reservation.py','research/proxy_tokenizer.py',
           'upstream/jiuwenswarm/agents/harness/common/rails/frozen_messages_rail.py',
           'upstream/jiuwenswarm/agents/harness/common/versioned_memory.py']
    return {name:file_digest(ROOT/name) for name in files if (ROOT/name).is_file()}


def freeze_protocol(directory,*,models,token_limit,encoder_identity=None,external_sha256=None,provider='unconfigured',endpoint_hash=None):
    if not models or not all(isinstance(m,str) and m for m in models):raise ValueError('Models required')
    if type(token_limit) is not int or token_limit<=0:raise ValueError('Explicit positive token cap required')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    tasks=build_dataset()
    protocol={'schema_version':3,'models':models,'token_limit':token_limit,'max_calls':6000,'wall_seconds':14400,
              'dataset_sha256':digest(tasks),'seeds':{'dev':[4901,4902],'test':[61001,61002,61003]},
              'variants':[list(v) for v in VARIANTS],'readers':list(READERS),'budgets':[128,256,512],
              'external_budgets':[512,1024],'external_passage_tokens':192,'answer_max_tokens':160,'stress_max_tokens':320,'external_max_tokens':192,
              'encoder':encoder_identity,'external_sha256':external_sha256,'code_hashes':code_hashes(),
              'provider':provider,'endpoint_hash':endpoint_hash,
              'tokenizer':'tiktoken cl100k_base; arbitrary source reserved strings encoded literally with disallowed_special=(); installed runtime version captured separately',
              'repeat_note':'Repeated zero-temperature invocations; provider sampling seed is not exposed.',
              'offline_scope':'Full frozen synthetic grid and external retrieval; paid grid separately registered.',
              'sampling':'Balanced family/seed coverage in factorial core, then extended held-out coverage. No outcome-based tuning.',
              'external_metrics':'Normalized exact/F1 proxies and optional DeepSeek semantic judge; not official benchmark scores.',
              'cohort_plan':{'synthetic_controlled':72,'synthetic_packing':12,'external_matched':70,'external_main':500},
              'primary_contrasts':['reader conflict-aware vs baseline','versioned vs no-conflict','BM25 vs dense/hybrid',
                                   'current vs alternative atomic packer','Flash vs Pro','matched budget sensitivity'],
              'old_scores_inherited':False,'novelty_status':'Established temporal modeling; engineering mechanisms need empirical validation.'}
    if (directory/'admission_reserves.json').exists():
        protocol['admission_reserves_sha256']=file_digest(directory/'admission_reserves.json')
    path=directory/'protocol.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=protocol:raise ValueError('Frozen protocol changed; choose a new directory')
    if not path.exists():save_json(path,protocol)
    dataset=directory/'dataset.json'
    if dataset.exists() and json.loads(dataset.read_text(encoding='utf-8'))!=tasks:raise ValueError('Dataset changed')
    if not dataset.exists():save_json(dataset,tasks)
    return protocol,tasks


def core_tasks(tasks):
    chosen=[]
    families=sorted({t['family'] for t in tasks if t['split']=='test' and t['family']!='packing_stress'})
    for i,family in enumerate(families):
        group=[t for t in tasks if t['split']=='test' and t['family']==family]
        chosen.extend(group)
    return chosen


def live_grid(tasks,external_tasks,models):
    core=core_tasks(tasks);diagnostic=[]
    for family in sorted({t['family'] for t in core}):
        diagnostic.extend([t for t in core if t['family']==family][:4])
    rows=[]
    def add(task,model,policy,packer,reader='baseline',budget=256,repeat=0,kind='synthetic',phase='mechanism'):
        item=dict(kind=kind,task_id=task['id'],split=task.get('split','test'),family=task['family'],model=model,
                  policy=policy,packer=packer,reader=reader,budget=budget,repeat=repeat,phase=phase)
        item['cohort']=('synthetic_packing' if task['family']=='packing_stress' else 'synthetic_controlled') if kind=='synthetic' else task.get('evaluation_cohort','external_unassigned')
        item['id']=digest(item)[:24]
        if item['id'] not in {r['id'] for r in rows}:rows.append(item)
    # Phase groups are interleaved so budget stops preserve coverage of every gap.
    groups=[]
    mechanism=[]
    for task in core:
        for model in models:
            for policy in ('versioned','no_conflict'):
                for reader in ('baseline','conflict_aware'):add(task,model,policy,'smaller_first',reader)
    groups.append(rows[:]);rows=[]
    for task in core:
        for model in models:
            for policy in ('bm25','dense','hybrid'):add(task,model,policy,'rank_first',phase='retrieval')
    groups.append(rows[:]);rows=[]
    stress=[t for t in tasks if t['split']=='test' and t['family']=='packing_stress']
    for task in stress:
        for model in models:
            for packer in ('smaller_first','utility_dp','diverse'):
                for reader in ('baseline','conflict_aware'):
                    for budget in (128,256,512):add(task,model,'versioned',packer,reader,budget,phase='packing')
    groups.append(rows[:]);rows=[]
    for task in diagnostic:
        for budget in (128,512):
            for policy in ('versioned','no_conflict'):add(task,models[0],policy,'smaller_first','conflict_aware',budget,phase='budget')
    groups.append(rows[:]);rows=[]
    for task in diagnostic:
        for model in models:
            for policy in ('versioned','no_conflict'):
                for reader in ('baseline','conflict_aware'):add(task,model,policy,'smaller_first',reader,repeat=1,phase='repeat')
    groups.append(rows[:]);rows=[]
    for task in diagnostic:
        for model in models:add(task,model,'versioned','smaller_first','reflection',phase='reflection')
    groups.append(rows[:]);rows=[]
    for task in diagnostic:
        for model in models:
            for policy in ('full','recent','no_time'):add(task,model,policy,'rank_first',phase='controls')
    groups.append(rows[:]);rows=[]
    for index,task in enumerate(external_tasks):
        task={**task,'evaluation_cohort':'external_matched' if index<70 else 'external_extension'}
        for model in (models if index<70 else models[:1]):
            for policy in (('bm25','dense','hybrid') if index<70 else ('hybrid',)):
                add(task,model,policy,'rank_first','baseline',1024,kind='external',phase='external')
    groups.append(rows[:]);rows=[]
    result=[];maximum=max(map(len,groups),default=0)
    for i in range(maximum):
        for group in groups:
            if i<len(group):result.append(group[i])
    covered={r['task_id'] for r in result if r['kind']=='synthetic' and r['policy']=='versioned' and r['reader']=='conflict_aware' and r['model']==models[0] and r['budget']==256}
    rows=[]
    for task in tasks:
        if task['split']=='test' and task['id'] not in covered:add(task,models[0],'versioned','smaller_first','conflict_aware',phase='extended_coverage')
    return result+rows


def paired_intervals(rows):
    valid=[r for r in rows if r.get('status')=='ok' and r.get('kind')=='synthetic' and r.get('split')=='test']
    grouped={}
    for row in valid:
        key=tuple(row.get(k) for k in ('model','policy','packer','budget'))
        grouped.setdefault(key,[]).append(row)
    output=[]
    for key,group in sorted(grouped.items()):
        clusters={}
        for row in group:clusters.setdefault(row['task_id'],{}).setdefault(row['reader'],[]).append(float(row['score']['exact']))
        differences=[statistics.mean(values['conflict_aware'])-statistics.mean(values['baseline']) for values in clusters.values() if 'baseline' in values and 'conflict_aware' in values]
        if not differences:continue
        mean=statistics.mean(differences);se=statistics.stdev(differences)/(len(differences)**.5) if len(differences)>1 else None
        output.append({'model':key[0],'policy':key[1],'packer':key[2],'budget':key[3],
                       'contrast':'conflict_aware minus baseline','task_clusters':len(differences),'mean':mean,
                       'descriptive_interval_95':[max(-1,mean-1.96*se),min(1,mean+1.96*se)] if se is not None else None,
                       'limitations':'Task-cluster descriptive normal interval; related synthetic families, repeated requests and multiple comparisons preclude significance claims.'})
    return output
