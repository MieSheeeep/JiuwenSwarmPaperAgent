"""Frozen local image classification study. No model API calls or QA inputs."""
from pathlib import Path
import json
import platform
import time
import warnings
import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from threadpoolctl import threadpool_limits
import sklearn
from research.artifacts import digest, file_digest, save_json

SEEDS=(11,23,37,51,71)
CONDITIONS=('clean','gaussian_0.15','gaussian_0.30','gaussian_0.45',
            'dropout_0.10','dropout_0.30','dropout_0.50')
METHODS=('msp','temperature_msp','logit_margin','negative_entropy')
TARGETS=(.8,.9)


def softmax(z):
    z=np.asarray(z,dtype=float);e=np.exp(z-z.max(axis=1,keepdims=True))
    return e/e.sum(axis=1,keepdims=True)


def forward_logits(weights,biases,x):
    h=np.asarray(x,dtype=float)
    for i,(weight,bias) in enumerate(zip(weights,biases)):
        h=h@weight+bias
        if i<len(weights)-1:h=np.maximum(h,0)
    return h


def confidence_scores(z,temperature):
    p=softmax(z);scaled=softmax(z/temperature);ordered=np.sort(z,axis=1)
    return {'msp':p.max(axis=1),'temperature_msp':scaled.max(axis=1),
        'logit_margin':ordered[:,-1]-ordered[:,-2],
        'negative_entropy':np.sum(p*np.log(np.clip(p,1e-15,1)),axis=1)}


def fit_temperature(z,y):
    def loss(logt):
        p=softmax(z/np.exp(logt))
        return float(-np.log(np.clip(p[np.arange(len(y)),y],1e-15,1)).mean())
    result=minimize_scalar(loss,bounds=(np.log(.05),np.log(20)),method='bounded',options={'xatol':1e-8})
    if not result.success:raise ValueError('Temperature fit failed')
    return float(np.exp(result.x))


def corrupt(x,condition):
    if condition not in CONDITIONS:raise ValueError('Unknown frozen corruption')
    if condition=='clean':return np.array(x,copy=True)
    kind,level=condition.split('_');level=float(level)
    rng=np.random.default_rng(20261107+CONDITIONS.index(condition))
    if kind=='gaussian':return np.clip(x+rng.normal(0,level,size=x.shape),0,1)
    return x*(rng.random(x.shape)>=level)


def selective_metrics(z,y,scores,threshold,temperature=1.):
    probabilities=softmax(z/temperature);prediction=z.argmax(axis=1)
    errors=(prediction!=y).astype(float);keep=scores>=threshold
    accepted=int(keep.sum());n=len(y)
    order=np.argsort(-scores,kind='stable')
    aurc=float(np.mean(np.cumsum(errors[order])/np.arange(1,n+1)))
    confidence=probabilities.max(axis=1);ece=0.
    for b in range(15):
        mask=(confidence>=b/15)&(confidence<(b+1)/15 if b<14 else confidence<=1)
        if mask.any():ece+=mask.mean()*abs((1-errors[mask]).mean()-confidence[mask].mean())
    return {'accepted':accepted,'total':n,'coverage':accepted/n,
        'selective_risk':float(errors[keep].mean()) if accepted else None,
        'overall_accuracy':float(1-errors.mean()),'aurc':aurc,'ece15':float(ece),
        'nll':float(-np.log(np.clip(probabilities[np.arange(n),y],1e-15,1)).mean())}


class DigitsStudy:
    name='digits-selective-v1'
    version='1'

    def __init__(self,directory):
        self.directory=Path(directory).resolve();self.data=self.directory/'data/digits.npz'
        self.root=self.directory/'experiments/digits'

    def prepare(self):
        manifest=self.directory/'data/digits_manifest.json'
        if manifest.exists():
            value=json.loads(manifest.read_text(encoding='utf-8'))
            if file_digest(self.data)!=value['dataset']:raise ValueError('Frozen digits data changed')
            return value
        self.data.parent.mkdir(parents=True,exist_ok=True)
        data=load_digits();indices=np.arange(len(data.target))
        fitting,test=train_test_split(indices,test_size=.2,random_state=20261107,stratify=data.target)
        train,validation=train_test_split(fitting,test_size=.25,random_state=20261107,stratify=data.target[fitting])
        np.savez_compressed(self.data,x=data.data/16.,y=data.target,train=train,validation=validation,test=test)
        value={'dataset':file_digest(self.data),'dataset_name':'sklearn bundled UCI optical digits, 8x8',
            'source':'https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html',
            'split':{k:v.tolist() for k,v in [('train',train),('validation',validation),('test',test)]},
            'methods':['always_answer',*METHODS],'metrics':['coverage','selective_risk','overall_accuracy','aurc','nll','ece15'],
            'model':{'hidden_layers':[64,32],'solver':'adam','activation':'relu','batch_size':64,
                'learning_rate_init':.001,'alpha':.0001,'epochs':200,'early_stopping':False},
            'seeds':list(SEEDS),'conditions':list(CONDITIONS),'target_coverages':list(TARGETS),
            'calibration':'Validation NLL temperature; validation 1-target score quantile with linear interpolation; accept score>=threshold.',
            'acceptance':'Descriptive threshold-transfer study; no new algorithm or universal error guarantee.',
            'independence':'Five initializations share train/validation/test splits and corruption realizations. Seed SD is not an independent-data confidence interval.'}
        save_json(manifest,value);return value

    def _check(self,design):
        prepared=self.prepare()
        if design.get('code_sha256') and design['code_sha256']!=file_digest(Path(__file__)):
            raise ValueError('Frozen digits implementation changed')
        for key in ('dataset','split','model','seeds','conditions','methods','target_coverages'):
            if design[key]!=prepared[key]:raise ValueError('Frozen digits design changed: '+key)

    def _fit(self,seed,epochs):
        data=np.load(self.data,allow_pickle=False)
        model=MLPClassifier(hidden_layer_sizes=(64,32),solver='adam',activation='relu',batch_size=64,
            learning_rate_init=.001,alpha=.0001,max_iter=epochs,tol=0.,n_iter_no_change=epochs+1,
            early_stopping=False,random_state=seed)
        with warnings.catch_warnings(record=True) as caught,threadpool_limits(limits=2):
            warnings.simplefilter('always');model.fit(data['x'][data['train']],data['y'][data['train']])
        validation=forward_logits(model.coefs_,model.intercepts_,data['x'][data['validation']])
        np.testing.assert_allclose(softmax(validation),model.predict_proba(data['x'][data['validation']]),atol=1e-10)
        return model,validation,[str(w.message) for w in caught]

    def pilot(self,design):
        self._check(design)
        model,z,notes=self._fit(SEEDS[0],3)
        return {'passed':bool(np.isfinite(z).all()),'diagnostics':{'scope':'3-epoch train/validation-only plumbing probe; no held-out scoring',
            'validation_tasks':len(z),'classes':z.shape[1],'epochs':model.n_iter_,'warnings':notes}}

    def run(self,design):
        self._check(design);self.root.mkdir(parents=True,exist_ok=True)
        identity=digest(design);protocol=self.root/'protocol.json'
        if protocol.exists() and json.loads(protocol.read_text(encoding='utf-8'))['design_sha256']!=identity:
            raise ValueError('Experiment belongs to another design')
        save_json(protocol,{'design_sha256':identity,'code_sha256':file_digest(Path(__file__))})
        cache=self.root/'results.json'
        if cache.exists():
            value=json.loads(cache.read_text(encoding='utf-8'));self._verify_saved(value,identity);return value
        data=np.load(self.data,allow_pickle=False);rows=[];files={};started=time.monotonic()
        for seed in SEEDS:
            folder=self.root/str(seed);folder.mkdir(exist_ok=True)
            model_file=folder/'weights.npz';validation_file=folder/'validation.npz';calibration=folder/'calibration.json'
            if not all(p.exists() for p in (model_file,validation_file,calibration)):
                model,z,notes=self._fit(seed,200)
                np.savez_compressed(model_file,**{f'w{i}':w for i,w in enumerate(model.coefs_)},
                                    **{f'b{i}':b for i,b in enumerate(model.intercepts_)})
                vy=data['y'][data['validation']];temperature=fit_temperature(z,vy)
                scores=confidence_scores(z,temperature)
                thresholds={method:{str(target):float(np.quantile(score,1-target)) for target in TARGETS}
                            for method,score in scores.items()}
                np.savez_compressed(validation_file,logits=z,y=vy,indices=data['validation'])
                save_json(calibration,{'temperature':temperature,'thresholds':thresholds,
                    'fitted_using':'validation only, before test inference','epochs':model.n_iter_,'warnings':notes,
                    'weights_sha256':file_digest(model_file),'validation_sha256':file_digest(validation_file)})
            info=json.loads(calibration.read_text(encoding='utf-8'))
            if file_digest(model_file)!=info['weights_sha256'] or file_digest(validation_file)!=info['validation_sha256']:
                raise ValueError('Saved trained model or validation logits changed')
            weights=np.load(model_file,allow_pickle=False)
            w=[weights[f'w{i}'] for i in range(3)];b=[weights[f'b{i}'] for i in range(3)]
            # No test input or label is used above to fit a model, temperature or threshold.
            for condition in CONDITIONS:
                x=corrupt(data['x'][data['test']],condition);y=data['y'][data['test']]
                z=forward_logits(w,b,x);temperature=info['temperature'];scores=confidence_scores(z,temperature)
                logits_file=folder/(condition+'.npz')
                np.savez_compressed(logits_file,logits=z,y=y,indices=data['test'])
                rows.append({'seed':seed,'condition':condition,'method':'always_answer','target_coverage':1.,
                    **selective_metrics(z,y,scores['msp'],threshold=0)})
                for method in METHODS:
                    for target in TARGETS:
                        threshold=info['thresholds'][method][str(target)]
                        rows.append({'seed':seed,'condition':condition,'method':method,'target_coverage':target,
                            'threshold':threshold,'temperature':temperature,
                            **selective_metrics(z,y,scores[method],threshold,temperature if method=='temperature_msp' else 1.)})
            for path in folder.iterdir():
                if path.is_file():files[path.relative_to(self.directory).as_posix()]=file_digest(path)
            print(json.dumps({'trained_seed':seed,'epochs':info['epochs'],'temperature':info['temperature'],'rows':len(rows)}),flush=True)
        value={'rows':rows,'rows_sha256':digest(rows),'design_sha256':identity,'files':files,
            'resources':{'api_calls':0,'seconds':time.monotonic()-started,'training_seeds':len(SEEDS)},
            'environment':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__,'threads':2}}
        save_json(cache,value);return value

    def _verify_saved(self,value,identity):
        if value['design_sha256']!=identity or digest(value['rows'])!=value['rows_sha256']:
            raise ValueError('Saved digits result identity mismatch')
        for path,sha in value['files'].items():
            full=(self.directory/path).resolve()
            if not full.is_relative_to(self.directory) or file_digest(full)!=sha:raise ValueError('Digits artifact changed: '+path)

    def audit(self,design):
        self._check(design)
        value=json.loads((self.root/'results.json').read_text(encoding='utf-8'));self._verify_saved(value,digest(design))
        data=np.load(self.data,allow_pickle=False);expected=set()
        for seed in SEEDS:
            folder=self.root/str(seed);weights=np.load(folder/'weights.npz',allow_pickle=False)
            info=json.loads((folder/'calibration.json').read_text(encoding='utf-8'))
            validation=np.load(folder/'validation.npz',allow_pickle=False)
            v_scores=confidence_scores(validation['logits'],info['temperature'])
            for method in METHODS:
                for target in TARGETS:
                    if float(np.quantile(v_scores[method],1-target))!=info['thresholds'][method][str(target)]:
                        raise ValueError('Threshold differs from validation quantile')
            for condition in CONDITIONS:
                saved=np.load(folder/(condition+'.npz'),allow_pickle=False)
                logits=forward_logits([weights[f'w{i}'] for i in range(3)],[weights[f'b{i}'] for i in range(3)],corrupt(data['x'][data['test']],condition))
                np.testing.assert_allclose(logits,saved['logits'],atol=1e-10)
                np.testing.assert_array_equal(saved['y'],data['y'][data['test']])
                scores=confidence_scores(logits,info['temperature'])
                for method,target in [('always_answer',1.),*[(m,t) for m in METHODS for t in TARGETS]]:
                    expected.add((seed,condition,method,target))
                    found=[r for r in value['rows'] if (r['seed'],r['condition'],r['method'],r['target_coverage'])==(seed,condition,method,target)]
                    if len(found)!=1:raise ValueError('Missing or duplicated evaluation cell')
                    row=found[0];threshold=0 if method=='always_answer' else info['thresholds'][method][str(target)]
                    result=selective_metrics(logits,saved['y'],scores['msp' if method=='always_answer' else method],threshold,
                                             info['temperature'] if method=='temperature_msp' else 1.)
                    for key,actual in result.items():
                        if row[key]!=actual:raise ValueError('Recomputed metric differs: '+key)
        actual={(r['seed'],r['condition'],r['method'],r['target_coverage']) for r in value['rows']}
        if len(value['rows'])!=len(expected) or actual!=expected:raise ValueError('Invalid experiment grid')
        report={'status':'verified','cells':len(expected),'test_tasks':len(data['test']),
            'checks':['saved weight inference reproduces all 35 test-logit arrays','thresholds reproduce validation quantiles',
                      'all 315 metric cells recomputed','file hashes and disjoint frozen split checked'],
            'scope':'CPU saved-weight inference and metric replay; no retraining in audit, no API calls.'}
        save_json(self.root/'audit.json',report);return report
