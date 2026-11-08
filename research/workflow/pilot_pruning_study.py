"""Fixed-look paired pilot audit. Classical bounds; no model API calls.

Counts are (-1, 0, +1). Replay weights describe a conditional finite benchmark,
not population truth. Every n is a separate fixed-budget design.
"""
from functools import lru_cache
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
from urllib.request import Request, urlopen
import json
import hashlib
import platform
import time
import warnings
import numpy as np
from scipy.special import gammaln, xlogy
from scipy.stats import beta, norm
import sklearn
from sklearn.datasets import load_breast_cancer, load_wine, load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.dummy import DummyClassifier
from threadpoolctl import threadpool_limits
from research.artifacts import digest, file_digest, save_json

SEEDS=(68101,68102,68103)
NS=(16,32,64,128,256)
GAINS=(-.08,-.04,0.,.01,.02,.04,.08,.16)
DISCORDANCES=(.05,.1,.2,.4)
DELTAS=(0.,.02,.05)
INTERVALS=('paired_normal','exact_joint')
POLICIES=('legacy_binary','delta_binary','tri_state','always_go','always_reject','always_defer')
MIXTURES=('equal','futile3x','useful3x')
PAIRS=(('logistic','dummy'),('hgb','logistic'),('rf','hgb'))
TOL=1e-12


@lru_cache(maxsize=None)
def count_grid(n):
    if not isinstance(n,int) or n<1:raise ValueError('n must be a positive integer')
    result=np.array([(minus,n-minus-plus,plus) for minus in range(n+1) for plus in range(n-minus+1)],dtype=int)
    result.setflags(write=False)
    return result


def probabilities(counts,g,q):
    if not 0<=q<=1 or abs(g)>q+TOL:raise ValueError('invalid gain/discordance')
    c=np.asarray(counts); p=np.array([(q-g)/2,1-q,(q+g)/2]); p=np.clip(p,0,1)
    n=c.sum(axis=1)
    logs=gammaln(n+1)-gammaln(c+1).sum(axis=1)+xlogy(c,p).sum(axis=1)
    result=np.exp(logs)
    if not np.isclose(result.sum(),1,atol=1e-10):raise ValueError('enumeration probability mass failed')
    return result/result.sum()


@lru_cache(maxsize=64)
def _interval_grid(n,method,alpha):
    c=count_grid(n); minus=c[:,0]; plus=c[:,2]; gain=(plus-minus)/n
    if method=='paired_normal':
        # Unbiased sample variance of paired differences; n=1 lacks a variance estimate.
        variance=((plus+minus)-n*gain**2)/(n-1) if n>1 else np.ones(len(c))
        radius=norm.ppf(1-alpha/2)*np.sqrt(np.maximum(variance,0)/n)
        return np.maximum(-1,gain-radius),np.minimum(1,gain+radius)
    if method!='exact_joint':raise ValueError('unknown interval')
    # Each marginal CP interval has error alpha/2, hence tail alpha/4.
    def cp(k):
        lower=np.zeros(len(k)); upper=np.ones(len(k)); mask=k>0
        lower[mask]=beta.ppf(alpha/4,k[mask],n-k[mask]+1)
        mask=k<n;upper[mask]=beta.ppf(1-alpha/4,k[mask]+1,n-k[mask])
        return lower,upper
    lm,um=cp(minus);lp,up=cp(plus)
    return lp-um,up-lm


def intervals(counts,method,alpha=.05):
    if not 0<alpha<1:raise ValueError('invalid alpha')
    c=np.asarray(counts,dtype=int)
    if c.ndim!=2 or c.shape[1]!=3 or (c<0).any():raise ValueError('invalid counts')
    n=int(c[0].sum())
    if n<1 or not (c.sum(axis=1)==n).all():raise ValueError('counts require common positive n')
    lo,hi=_interval_grid(n,method,float(alpha))
    # Index of (minus, zero, plus) in triangular enumeration.
    k=c[:,0]*(n+1)-c[:,0]*(c[:,0]-1)//2+c[:,2]
    return lo[k].copy(),hi[k].copy()


def decide(lower,upper,gain,delta,policy):
    lower,upper,gain=np.broadcast_arrays(lower,upper,gain)
    out=np.full(lower.shape,'no_go',dtype='<U6')
    if policy=='legacy_binary':out[(lower>0)&(gain>=delta)]='go'
    elif policy=='delta_binary':out[lower>delta]='go'
    elif policy=='tri_state':
        out[...]='defer';out[lower>delta]='go';out[upper<delta]='no_go'
    elif policy=='always_go':out[...]='go'
    elif policy=='always_reject':pass
    elif policy=='always_defer':out[...]='defer'
    else:raise ValueError('unknown policy')
    return out


def truth_label(g,delta):
    return 'useful' if g>delta+TOL else 'futile' if g<delta-TOL else 'boundary'


def integrate_case(n,g,q,delta,alpha=.05,**metadata):
    c=count_grid(int(n));p=probabilities(c,g,q); gain=(c[:,2]-c[:,0])/n
    truth=truth_label(g,delta);rows=[]
    base={'kind':'synthetic','dataset':None,'seed':None,'pair':None,
          'case_id':f'n{n}:g{g}:q{q}:d{delta}',**metadata,'n':n,'gain':float(g),'discordance':float(q),'delta':delta,'truth':truth}
    for interval in INTERVALS:
        lo,hi=intervals(c,interval,alpha);coverage=float(p[(lo<=g)&(hi>=g)].sum())
        for policy in POLICIES:
            actions=decide(lo,hi,gain,delta,policy)
            go=float(p[actions=='go'].sum());reject=float(p[actions=='no_go'].sum());defer=float(p[actions=='defer'].sum())
            rows.append({**base,'interval':interval,'policy':policy,'p_go':go,'p_no_go':reject,'p_defer':defer,
                         'automatic_coverage':go+reject,'ci_coverage':coverage,
                         'false_go_probability':go if truth=='futile' else 0.,
                         'false_prune_probability':reject if truth=='useful' else 0.})
    return rows


def mixture_summary(rows,mixture='equal'):
    """Aggregate regimes within kind/n/delta/interval; random defer is independent of regime.

    Favor mixtures assign weight 3 to the named strict truth and 1 otherwise.
    Boundary regimes stay in denominators but have neither error direction.
    """
    if mixture not in MIXTURES:raise ValueError('unknown mixture')
    groups={}
    for row in rows:
        key=(row['kind'],row['n'],row['delta'],row['interval'])
        groups.setdefault(key,{}).setdefault(row['policy'],[]).append(row)
    result=[];metrics=('p_go','p_no_go','p_defer','automatic_coverage','ci_coverage','false_go_probability','false_prune_probability')
    for key,policies in groups.items():
        aggregate={}
        for policy,items in policies.items():
            favored='futile' if mixture=='futile3x' else 'useful' if mixture=='useful3x' else None
            weights=np.array([3. if r['truth']==favored else 1. for r in items]);weights/=weights.sum()
            out={'kind':key[0],'n':key[1],'delta':key[2],'interval':key[3],'policy':policy,'mixture':mixture,'regimes':len(items)}
            out.update({metric:float(np.dot(weights,[r[metric] for r in items])) for metric in metrics})
            aggregate[policy]=out;result.append(out)
        rate=aggregate['tri_state']['p_defer']
        for policy in ('legacy_binary','delta_binary'):
            out={**aggregate[policy],'policy':'matched_random_'+policy,'p_defer':rate}
            for metric in ('p_go','p_no_go','false_go_probability','false_prune_probability'):
                out[metric]*=1-rate
            out['automatic_coverage']=1-rate;result.append(out)
    return result


class PilotPruningStudy:
    name='pilot-pruning-audit-v1';version='1'

    def __init__(self,directory):
        self.directory=Path(directory).resolve();self.root=self.directory/'experiments/pilot_pruning'
        self.data=self.directory/'data/pilot_pruning';self.manifest_path=self.data/'manifest.json'

    def freeze_files(self,paths):
        return {str(Path(path).resolve()):file_digest(path) for path in paths}

    def verify_files(self,frozen):
        for path,sha in frozen.items():
            if not Path(path).is_file() or file_digest(path)!=sha:raise ValueError('Frozen artifact changed: '+path)

    def prepare(self):
        if self.manifest_path.exists():
            manifest=json.loads(self.manifest_path.read_text(encoding='utf-8'));self.verify_files(manifest['files']);return manifest
        self.data.mkdir(parents=True,exist_ok=True);items=[];paths=[]
        for name,loader in [('breast_cancer',load_breast_cancer),('wine',load_wine)]:
            d=loader();path=self.data/(name+'.npz');np.savez_compressed(path,x=d.data,y=d.target)
            paths.append(path);items.append({'name':name,'path':str(path),'source':'sklearn bundled '+name,'shape':list(d.data.shape)})
        for name,identifier,archive,member,shape in [('spambase',94,'spambase.zip','spambase.data',(4601,57)),('magic',159,'magic+gamma+telescope.zip','magic04.data',(19020,10))]:
            url=f'https://archive.ics.uci.edu/static/public/{identifier}/{archive}';raw_path=self.data/archive
            if not raw_path.exists():
                with urlopen(Request(url,headers={'User-Agent':'JiuwenResearch/1.0'}),timeout=90) as response:raw=response.read(20000000)
                raw_path.write_bytes(raw)
            with ZipFile(BytesIO(raw_path.read_bytes())) as z:
                text=z.read(member).decode('utf-8')
            a=np.genfromtxt(BytesIO(text.encode()),delimiter=',',dtype=str);x=a[:,:-1].astype(float)
            y=(a[:,-1]=='g').astype(int) if name=='magic' else a[:,-1].astype(int)
            if x.shape!=shape or not np.isfinite(x).all():raise ValueError('Unexpected public dataset: '+name)
            path=self.data/(name+'.npz');np.savez_compressed(path,x=x,y=y);paths.extend([raw_path,path])
            items.append({'name':name,'path':str(path),'source':url,'raw_path':str(raw_path),'raw_sha256':file_digest(raw_path),'shape':list(x.shape)})
        manifest={'datasets':items,'files':self.freeze_files(paths),'sklearn_version':sklearn.__version__,
          'seeds':list(SEEDS),'split':{'train':.6,'test':.4,'stratified':True,'seeds':list(SEEDS)},
          'methods':list(POLICIES),'metrics':['p_go','p_no_go','p_defer','ci_coverage','false_go_probability','false_prune_probability'],
          'model':{'logistic':{'C':1,'max_iter':1000,'preprocessing':'train-only StandardScaler'},'hgb':{'max_iter':100,'max_depth':3},'rf':{'n_estimators':100,'n_jobs':2},'dummy':'most_frequent'},
          'pairs':[list(p) for p in PAIRS],'mixtures':list(MIXTURES),'mixture_rule':'equal=1 each; futile3x=3 if gain<delta-1e-12 else1; useful3x=3 if gain>delta+1e-12 else1; normalize',
          'acceptance':'Conditional finite-benchmark audit; no universal safety or novelty claim.'}
        manifest['dataset']=digest(manifest['files']);save_json(self.manifest_path,manifest);return manifest

    def _check(self,protocol):
        if not protocol.get('source_hashes') or not protocol.get('manifest_sha256'):raise ValueError('source and manifest freeze required')
        self.verify_files(protocol['source_hashes'])
        if protocol['manifest_sha256']!=file_digest(self.manifest_path):raise ValueError('Frozen manifest changed')
        return self.prepare()

    def _predictions(self,name,x,y,seeds):
        paths=[];replays=[];notes=[]
        input_hash=digest({'x':hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest(),'y':hashlib.sha256(np.ascontiguousarray(y).tobytes()).hexdigest(),'shape':list(x.shape)})
        implementation_hash=file_digest(Path(__file__))
        for seed in seeds:
            path=self.root/'predictions'/f'{name}_{seed}.npz';side=path.with_suffix('.json')
            if path.exists() or side.exists():
                if not path.exists() or not side.exists():raise ValueError('Incomplete prediction artifact')
                record=json.loads(side.read_text(encoding='utf-8'));self.verify_files(record['files'])
                if record.get('input_hash')!=input_hash or record.get('implementation_hash')!=implementation_hash:raise ValueError('Frozen prediction input or implementation changed')
                data=np.load(path,allow_pickle=False)
            else:
                train,test=train_test_split(np.arange(len(y)),test_size=.4,random_state=seed,stratify=y)
                models={'logistic':make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=1000,random_state=seed)),
                    'hgb':HistGradientBoostingClassifier(max_iter=100,max_depth=3,random_state=seed),
                    'rf':RandomForestClassifier(n_estimators=100,n_jobs=2,random_state=seed),'dummy':DummyClassifier(strategy='most_frequent')}
                prediction={}
                with warnings.catch_warnings(record=True) as caught,threadpool_limits(limits=2):
                    warnings.simplefilter('always')
                    for method,model in models.items():model.fit(x[train],y[train]);prediction[method]=model.predict(x[test])
                notes.extend(str(w.message) for w in caught);path.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(path,y=y[test],train=train,test=test,**prediction)
                save_json(side,{'files':self.freeze_files([path]),'input_hash':input_hash,'implementation_hash':implementation_hash,'dataset':name,'seed':seed,'n_train':len(train),'n_test':len(test)})
                data=np.load(path,allow_pickle=False)
            for candidate,baseline in PAIRS:
                difference=(data[candidate]==data['y']).astype(int)-(data[baseline]==data['y']).astype(int)
                replays.append({'dataset':name,'seed':seed,'pair':candidate+'_vs_'+baseline,
                    'gain':float(difference.mean()),'discordance':float(np.mean(difference!=0)),'test_count':len(difference)})
            paths.extend([path,side])
        return replays,paths,notes

    def pilot(self,protocol):
        self._check(protocol);start=time.perf_counter();iris=load_iris()
        replay,paths,notes=self._predictions('iris_health_only',iris.data,iris.target,SEEDS[:1])
        rows=integrate_case(4,0,.2,.02)
        passed=all(abs(r['p_go']+r['p_no_go']+r['p_defer']-1)<1e-10 for r in rows)
        return {'passed':passed,'rows':rows,'files':[str(p) for p in paths],
          'resources':{'wall_seconds':time.perf_counter()-start,'warnings':notes},
          'diagnostics':{'scope':'Iris only and tiny synthetic execution health; not final outcomes','iris_pairs':len(replay),'probability_mass_ok':passed,'warnings':notes}}

    def run(self,protocol):
        manifest=self._check(protocol);start=time.perf_counter();rows=[];files=[];notes=[]
        for n in NS:
            for q in DISCORDANCES:
                for g in GAINS:
                    if abs(g)>q+TOL:continue
                    for delta in DELTAS:rows.extend(integrate_case(n,g,q,delta))
        for item in manifest['datasets']:
            with np.load(item['path'],allow_pickle=False) as data:
                replay,paths,warnings_=self._predictions(item['name'],data['x'],data['y'],SEEDS)
            files.extend(paths);notes.extend(warnings_)
            for case in replay:
                for n in NS:
                    for delta in DELTAS:
                        meta={k:case[k] for k in ('dataset','seed','pair','test_count')}
                        meta.update(kind='empirical',case_id=f"{case['dataset']}:{case['seed']}:{case['pair']}:n{n}:d{delta}")
                        rows.extend(integrate_case(n,case['gain'],case['discordance'],delta,**meta))
        self.root.mkdir(parents=True,exist_ok=True);result_path=self.root/'rows.json';save_json(result_path,rows);files.append(result_path)
        resources={'wall_seconds':time.perf_counter()-start,'python':platform.python_version(),'sklearn':sklearn.__version__,'warnings':notes,'fits':48,'independent_datasets':4}
        results_path=self.root/'results.json';save_json(results_path,{'rows':rows,'rows_sha256':digest(rows),'resources':resources});files.append(results_path)
        freeze_path=self.root/'artifact_manifest.json';save_json(freeze_path,{'files':self.freeze_files(files),'rows_sha256':digest(rows)});files.append(freeze_path)
        return {'rows':rows,'rows_sha256':digest(rows),'files':[str(p) for p in files],
                'resources':{'wall_seconds':time.perf_counter()-start,'python':platform.python_version(),'sklearn':sklearn.__version__,'warnings':notes,'fits':48,'independent_datasets':4}}


    def audit(self,protocol):
        """Read-only provenance and probability checks of saved results."""
        findings=[]
        try:
            manifest=self._check(protocol) if protocol else None
            result=json.loads((self.root/'results.json').read_text(encoding='utf-8'))
            if digest(result['rows'])!=result['rows_sha256']:raise ValueError('Saved row hash changed')
            if manifest is not None:
                expected=set()
                for n in NS:
                    for delta in DELTAS:
                        for method in INTERVALS:
                            for policy in POLICIES:
                                for q in DISCORDANCES:
                                    for g in GAINS:
                                        if abs(g)<=q+TOL:expected.add(('synthetic',n,delta,method,policy,g,q))
                                for item in manifest['datasets']:
                                    for seed in SEEDS:
                                        for candidate,baseline in PAIRS:
                                            expected.add(('empirical',n,delta,method,policy,item['name'],seed,candidate+'_vs_'+baseline))
                observed=[]
                for row in result['rows']:
                    prefix=(row['kind'],row['n'],row['delta'],row['interval'],row['policy'])
                    suffix=(row['gain'],row['discordance']) if row['kind']=='synthetic' else (row['dataset'],row['seed'],row['pair'])
                    observed.append(prefix+suffix)
                    if row['truth']!=truth_label(row['gain'],row['delta']):raise ValueError('Saved truth label changed')
                if len(observed)!=len(expected) or set(observed)!=expected:raise ValueError('Registered grid incomplete, duplicated or unexpected')
            frozen=self.root/'artifact_manifest.json'
            if frozen.exists():self.verify_files(json.loads(frozen.read_text(encoding='utf-8'))['files'])
            for row in result['rows']:
                values=[row[k] for k in ('p_go','p_no_go','p_defer')]
                if not np.isfinite(values).all() or min(values)<-TOL or abs(sum(values)-1)>1e-10:
                    raise ValueError('Saved probability mass invalid')
            findings.append('Saved row hashes, prediction artifacts and probability masses verified')
        except (ValueError,OSError,KeyError) as exc:
            return {'passed':False,'findings':[str(exc)]}
        return {'passed':True,'findings':findings,'rows':len(result['rows']),'rows_sha256':result['rows_sha256']}
