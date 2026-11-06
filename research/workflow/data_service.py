"""Dataset discovery/preparation with explicit providers and frozen provenance."""
import json
from pathlib import Path
import random
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from research.artifacts import save_json,file_digest,digest


def download_json(url):
    request=Request(url,headers={'User-Agent':'JiuwenSwarmResearch/1.0'})
    with urlopen(request,timeout=60) as response:
        if response.status!=200:raise ValueError('Dataset download failed')
        raw=response.read(8_000_001)
    if len(raw)>8_000_000:raise ValueError('Dataset response exceeds limit')
    return json.loads(raw)


class DataService:
    def __init__(self,directory,fetch=download_json):
        self.directory=Path(directory);self.fetch=fetch

    def catalog(self):
        return [{'id':'hotpotqa-distractor','task':'multi-hop QA','source':'https://hotpotqa.github.io/',
                 'license':'CC BY-SA 4.0','scope':'public validation subset'},
                {'id':'local-json','task':'QA','source':'user-provided file'}]

    def prepare(self,constraints):
        cache=self.directory/'data';cache.mkdir(parents=True,exist_ok=True)
        request={k:constraints.get(k) for k in ('dataset_path','dataset_provider','dataset_rows','dataset_seed')}
        manifest=cache/'manifest.json';dataset=cache/'tasks.json'
        if manifest.exists():
            prior=json.loads(manifest.read_text(encoding='utf-8'))
            if prior['request']!=request or file_digest(dataset)!=prior['dataset_sha256']:
                raise ValueError('Dataset configuration or cached data changed')
            if prior.get('local_source') and file_digest(Path(prior['local_source']))!=prior['local_source_sha256']:
                raise ValueError('Local source changed')
            return dataset
        if constraints.get('dataset_path'):
            source=Path(constraints['dataset_path']).resolve()
            tasks=json.loads(source.read_text(encoding='utf-8'))
            origin={'provider':'local-json','local_source':str(source),'local_source_sha256':file_digest(source)}
        else:
            if constraints.get('dataset_provider')!='hotpotqa-distractor':
                raise ValueError('Choose a dataset from the provider catalog')
            count=constraints.get('dataset_rows',40)
            seed=constraints.get('dataset_seed',20261107)
            if type(count) is not int or not 4<=count<=100 or type(seed) is not int:
                raise ValueError('Dataset rows 4..100 and integer seed required')
            url='https://datasets-server.huggingface.co/rows?'+urlencode({
                'dataset':'hotpotqa/hotpot_qa','config':'distractor','split':'validation','offset':0,'length':count})
            raw=self.fetch(url);save_json(cache/'source.json',raw)
            rows=[r['row'] for r in raw['rows']]
            if len(rows)!=count or len({r['id'] for r in rows})!=count:raise ValueError('Incomplete dataset response')
            rng=random.Random(seed);rng.shuffle(rows)
            dev=max(2,count//5);tasks=[]
            for i,row in enumerate(rows):
                tasks.append({'id':row['id'],'split':'dev' if i<dev else 'test',
                    'question':row['question'],'answer':row['answer'],
                    'passages':[{'id':f'p{j}','title':title,'text':' '.join(sentences)}
                        for j,(title,sentences) in enumerate(zip(row['context']['title'],row['context']['sentences']))]})
            origin={'provider':'hotpotqa-distractor','url':url,'source_sha256':digest(raw),
                    'license':'CC BY-SA 4.0','scope':'subset of public validation; dev/test are local split names'}
        if not isinstance(tasks,list) or {t.get('split') for t in tasks}!={'dev','test'}:
            raise ValueError('Dataset requires explicit disjoint dev/test tasks')
        save_json(dataset,tasks)
        save_json(manifest,{'request':request,**origin,'dataset_sha256':file_digest(dataset)})
        return dataset
