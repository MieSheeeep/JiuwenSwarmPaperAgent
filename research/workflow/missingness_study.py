"""Frozen mask-integrated validation study; all experiment operations are local."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
from urllib.request import Request,urlopen
import json
import time
import numpy as np
import sklearn
from sklearn.linear_model import Ridge
from sklearn.impute import KNNImputer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupShuffleSplit
from threadpoolctl import threadpool_limits
from research.artifacts import save_json,digest,file_digest

SPLITS=(101,211,307,401,503)
RATES=(.1,.3,.5)
POLICIES=('clean','mc_average3','mc_worst1','mc_worst3','mc_worst9','analytic_grid','analytic_minimax')
CONDITIONS=('clean','mcar_0.1','mcar_0.3','mcar_0.5','block_0.3','mar_0.3')
DATASETS={'wine_red':(186,'wine+quality.zip','winequality-red.csv',1599,11),
          'wine_white':(186,'wine+quality.zip','winequality-white.csv',4898,11),
          'airfoil':(291,'airfoil+self+noise.zip','airfoil_self_noise.dat',1503,5),
          'yacht':(243,'yacht+hydrodynamics.zip','yacht_hydrodynamics.data',308,6)}


def expected_losses(x,y,a,b,fill,c,p):
    e=b+x@a-y;d=a*(fill-x)+c;s=d.sum(axis=1)
    return (e+p*s)**2+p*(1-p)*(d*d).sum(axis=1)


def risk_coefficients(x,y,a,b,fill,c):
    e=b+x@a-y;d=a*(fill-x)+c;s=d.sum(axis=1);v=(d*d).sum(axis=1)
    return np.array([np.mean(s*s-v),np.mean(2*e*s+v),np.mean(e*e)])


def worst_quadratic(coefficients,lo=.1,hi=.5):
    a,b,c=coefficients;points=[lo,hi]
    if a<0 and lo < -b/(2*a) < hi:points.append(-b/(2*a))
    values=[a*p*p+b*p+c for p in points];i=int(np.argmax(values))
    return float(values[i]),float(points[i])


def select_policy(name,coefficients,sampled,p=None):
    if name=='clean':loss=coefficients[:,2]
    elif name=='analytic_minimax':loss=np.array([worst_quadratic(c)[0] for c in coefficients])
    elif name=='analytic_grid':loss=np.array([max(np.polyval(c,r) for r in RATES) for c in coefficients])
    elif name=='known_p':loss=np.array([np.polyval(c,p) for c in coefficients])
    elif name=='mc_average3':loss=np.mean(sampled[:,:3,:],axis=(0,1))
    elif name.startswith('mc_worst'):
        k=int(name[len('mc_worst'):]);loss=np.max(np.mean(sampled[:,:k,:],axis=1),axis=0)
    else:raise ValueError('Unknown validation selector')
    return int(np.argmin(loss))


def masks(shape,condition,seed,repeats):
    rng=np.random.default_rng(seed)
    if condition=='clean':return np.zeros((1,*shape),dtype=bool)
    kind,value=condition.split('_');p=float(value)
    if kind=='mcar':return rng.random((repeats,*shape))<p
    if kind=='block':return np.repeat(rng.random((repeats,shape[0],1))<p,shape[1],axis=2)
    raise ValueError('MAR masks require anchor values')


def predict_pool(x,mask,model):
    return model['b']+np.einsum('ndc,nd->nc',model['a'][None,:,:]*(model['fill'][None,:,:]-x[:,:,None])+model['c'][None,:,:],mask)+x@model['a']


class MissingnessStudy:
    name='mask-integrated-linear-v1';version='1'

    def __init__(self,directory):
        self.directory=Path(directory).resolve();self.root=self.directory/'experiments/missingness'

    def prepare(self):
        folder=self.directory/'data';folder.mkdir(exist_ok=True,parents=True)
        manifest=folder/'manifest.json'
        if manifest.exists():
            value=json.loads(manifest.read_text(encoding='utf-8'))
            for item in value['datasets']:
                if file_digest(self.directory/item['path'])!=item['sha256']:raise ValueError('Frozen dataset changed')
            return value
        items=[]
        for name,(identifier,archive,filename,n,d) in DATASETS.items():
            archive_path=folder/archive
            url=f'https://archive.ics.uci.edu/static/public/{identifier}/{archive}'
            if not archive_path.exists():
                with urlopen(Request(url,headers={'User-Agent':'JiuwenResearch/1.0'}),timeout=45) as response:raw=response.read(8_000_000)
                archive_path.write_bytes(raw)
            with ZipFile(archive_path) as zipfile:
                matching=[k for k in zipfile.namelist() if k.endswith(filename)]
                if len(matching)!=1:raise ValueError('Dataset member missing or ambiguous')
                raw=zipfile.read(matching[0])
            array=np.loadtxt(BytesIO(raw),delimiter=';' if name.startswith('wine') else None,skiprows=1 if name.startswith('wine') else 0)
            if array.shape!=(n,d+1) or not np.isfinite(array).all():raise ValueError('Dataset shape or finite-value check failed')
            _,first=np.unique(array,axis=0,return_index=True);kept=np.sort(first);array=array[kept]
            _,groups=np.unique(array[:,:-1],axis=0,return_inverse=True)
            path=folder/(name+'.npz');np.savez_compressed(path,x=array[:,:-1],y=array[:,-1],row_ids=kept,groups=groups)
            items.append({'name':name,'path':path.relative_to(self.directory).as_posix(),'sha256':file_digest(path),
                'source':url,'source_sha256':file_digest(archive_path),'raw_rows':n,'rows':len(array),'features':d,
                'exact_duplicate_rows_removed':n-len(array),'feature_groups':len(np.unique(groups)),
                'license':'UCI CC BY 4.0; retain source attribution and verify dataset landing metadata.'})
        value={'datasets':items,'dataset':digest(items),'split_seeds':list(SPLITS),'rates':list(RATES),
            'policies':list(POLICIES),'candidate_count':12,'conditions':list(CONDITIONS),
            'model_pool':'mean/median fixed fill x indicators on/off x Ridge alpha 0.1/1/10',
            'train_missing_rate':.1,'test_mcar_draws':9,'test_stress_draws':3,'validation_draws_per_rate':9,
            'reference_models':['KNN5 imputer + Ridge alpha1','native HistGradientBoosting 100 iterations 15 leaves l2=1 no early stopping'],
            'normalization':'Observed training feature mean/std; training target mean/std. No hidden training cell used for fitting.',
            'evaluation':'Common held-out masks for all methods. sqrt(mean normalized squared loss). Pool oracle is label-informed diagnostic only.',
            'bootstrap':'1000 paired resamples of original row-ID clusters across test split memberships, conditional on fixed fitted models/splits/masks.',
            'novelty':'Application of standard expected squared-loss/dropout algebra; no first-of-kind or population-robustness claim.'}
        save_json(manifest,value);return value

    def split(self,data,seed):
        ids=np.arange(len(data['y']))
        remaining,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=seed).split(ids,groups=data['groups']))
        a,b=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=seed+1).split(remaining,groups=data['groups'][remaining]))
        train,val=remaining[a],remaining[b]
        if any(set(data['groups'][u])&set(data['groups'][v]) for u,v in ((train,val),(val,test),(train,test))):raise ValueError('Feature-group leakage')
        return train,val,test

    def check(self,design):
        if design['dataset']!=self.prepare()['dataset']:raise ValueError('Frozen source manifest mismatch')
        if design['code_sha256']!=file_digest(Path(__file__)):raise ValueError('Frozen experiment implementation changed')

    def fit(self,data,seed):
        train,val,test=self.split(data,seed);rng=np.random.default_rng(seed+7000)
        observed=np.array(data['x'][train],copy=True);missing=rng.random(observed.shape)<.1;observed[missing]=np.nan
        mu=np.nanmean(observed,axis=0);scale=np.nanstd(observed,axis=0);scale=np.where(scale>0,scale,1.)
        z=(observed-mu)/scale;ymu=data['y'][train].mean();yscale=data['y'][train].std();target=(data['y'][train]-ymu)/yscale
        fields={'mu':mu,'scale':scale,'ymu':ymu,'yscale':yscale,'train':train,'val':val,'test':test,
                'observed_train':z,'train_y':target}
        names=[];aa=[];bb=[];cc=[];ff=[]
        for imputation in ('mean','median'):
            fill=np.nanmean(z,axis=0) if imputation=='mean' else np.nanmedian(z,axis=0)
            if not np.isfinite(fill).all():raise ValueError('All-missing training feature')
            filled=np.where(np.isnan(z),fill,z)
            for indicators in (False,True):
                features=np.column_stack([filled,missing.astype(float)]) if indicators else filled
                for alpha in (.1,1.,10.):
                    fitted=Ridge(alpha=alpha).fit(features,target)
                    names.append(f'{imputation}_{"indicator" if indicators else "plain"}_ridge{alpha:g}')
                    aa.append(fitted.coef_[:z.shape[1]]);bb.append(fitted.intercept_)
                    cc.append(fitted.coef_[z.shape[1]:] if indicators else np.zeros(z.shape[1]));ff.append(fill)
        fields.update(a=np.array(aa).T,b=np.array(bb),c=np.array(cc).T,fill=np.array(ff).T)
        xv=(data['x'][val]-mu)/scale;yv=(data['y'][val]-ymu)/yscale
        analytic_started=time.perf_counter()
        coefficients=np.array([risk_coefficients(xv,yv,fields['a'][:,i],fields['b'][i],fields['fill'][:,i],fields['c'][:,i]) for i in range(12)])
        coefficient_seconds=time.perf_counter()-analytic_started
        sampled=np.zeros((3,9,12));started=time.perf_counter()
        for ri,p in enumerate(RATES):
            for j,mask in enumerate(masks(xv.shape,'mcar_'+str(p),seed+ri+9000,9)):
                sampled[ri,j]=np.mean((predict_pool(xv,mask,fields)-yv[:,None])**2,axis=0)
        mc_seconds=time.perf_counter()-started
        started=time.perf_counter();analytic=[worst_quadratic(c)[0] for c in coefficients];analytic_seconds=time.perf_counter()-started
        selected={policy:select_policy(policy,coefficients,sampled) for policy in POLICIES}
        selected.update({f'known_p_{p}':select_policy('known_p',coefficients,sampled,p=p) for p in (0.,*RATES)})
        return fields,{'names':names,'selected':selected,'validation_coefficients':coefficients.tolist(),
            'sampled_validation_losses':sampled.tolist(),'mc_27_draw_evaluation_seconds':mc_seconds,
            'analytic_envelope_only_seconds':analytic_seconds,'analytic_with_coefficients_seconds':analytic_seconds+coefficient_seconds,'analytic_worst_values':analytic,
            'protocol_note':'Selections made from validation only, before test scores; timing excludes fitting and is one run, not an end-to-end speed benchmark.'}

    def pilot(self,design):
        self.check(design);item=design['datasets'][-1];data=np.load(self.directory/item['path'],allow_pickle=False)
        fields,selection=self.fit(data,SPLITS[0])
        return {'passed':bool(np.isfinite(fields['a']).all()),'diagnostics':{'scope':'Yacht train/validation-only affine fit and selector probe; no held-out scoring',
                'candidates':len(selection['names']),'train_rows':len(fields['train']),'validation_rows':len(fields['val'])}}

    def run(self,design):
        self.check(design);self.root.mkdir(parents=True,exist_ok=True)
        cache=self.root/'results.json'
        if cache.exists():
            value=json.loads(cache.read_text(encoding='utf-8'));self.verify(value,design);return value
        save_json(self.root/'protocol.json',{'design_sha256':digest(design),'code_sha256':design['code_sha256']})
        rows=[];files={};all_selections=[];started=time.monotonic()
        for item in design['datasets']:
            data=np.load(self.directory/item['path'],allow_pickle=False)
            for seed in SPLITS:
                folder=self.root/item['name']/str(seed);folder.mkdir(parents=True,exist_ok=True)
                with threadpool_limits(limits=2):
                    fields,selection=self.fit(data,seed)
                    np.savez_compressed(folder/'affine.npz',**fields)
                    save_json(folder/'selection_before_test.json',selection)
                    # Only now are test inputs/labels projected for prediction and scoring.
                    xt=(data['x'][fields['test']]-fields['mu'])/fields['scale']
                    yt=(data['y'][fields['test']]-fields['ymu'])/fields['yscale']
                    imputer=KNNImputer(n_neighbors=5);ztrain=fields['observed_train']
                    knn=Ridge(alpha=1.).fit(imputer.fit_transform(ztrain),fields['train_y'])
                    native=HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=15,l2_regularization=1.,early_stopping=False,random_state=seed).fit(ztrain,fields['train_y'])
                    for ci,condition in enumerate(CONDITIONS):
                        repeats=1 if condition=='clean' else 9 if condition.startswith('mcar') else 3
                        if condition.startswith('mar'):
                            rng=np.random.default_rng(seed+13000+ci);prob=.3*(.5+1/(1+np.exp(-np.clip(xt[:,0],-30,30))))
                            masked=rng.random((repeats,*xt.shape))<prob[None,:,None];masked[:,:,0]=False
                        else:masked=masks(xt.shape,condition,seed+13000+ci,repeats)
                        predictions=[];references=[]
                        for mask in masked:
                            predictions.append(predict_pool(xt,mask,fields))
                            corrupted=np.where(mask,np.nan,xt)
                            references.append(np.column_stack([knn.predict(imputer.transform(corrupted)),native.predict(corrupted)]))
                        prediction=np.array(predictions);reference=np.array(references)
                        losses=((prediction-yt[None,:,None])**2).mean(axis=0)
                        reference_losses=((reference-yt[None,:,None])**2).mean(axis=0)
                        oracle=int(np.argmin(losses.mean(axis=0)))
                        p=0. if condition=='clean' else float(condition.split('_')[1])
                        choices={**{policy:selection['selected'][policy] for policy in POLICIES},
                                 'known_p':selection['selected'][f'known_p_{p}'],'oracle':oracle}
                        methods=[*choices,'knn_ridge','native_hist']
                        per_method=np.column_stack([losses[:,choices[method]] if method in choices else reference_losses[:,0 if method=='knn_ridge' else 1] for method in methods])
                        expected=np.column_stack([expected_losses(xt,yt,fields['a'][:,i],fields['b'][i],fields['fill'][:,i],fields['c'][:,i],p) for i in range(12)]) if condition=='clean' or condition.startswith('mcar') else np.empty((len(yt),0))
                        np.savez_compressed(folder/(condition+'.npz'),test_indices=data['row_ids'][fields['test']],masks=masked,
                            prediction=prediction,reference=reference,y=yt,losses=per_method,expected_pool_losses=expected)
                        for i,method in enumerate(methods):
                            mse=float(per_method[:,i].mean())
                            rows.append({'dataset':item['name'],'split_seed':seed,'condition':condition,'method':method,
                                'selected':selection['names'][choices[method]] if method in choices else method,
                                'normalized_mse':mse,'normalized_rmse':float(np.sqrt(mse)),
                                'regret_pool_mse':mse-float(losses[:,oracle].mean()),'test_rows':len(yt),
                                'mask_draws':repeats,'actual_missing_fraction':float(masked.mean())})
                for path in folder.iterdir():
                    if path.is_file():files[path.relative_to(self.directory).as_posix()]=file_digest(path)
                all_selections.append({'dataset':item['name'],'split_seed':seed,**selection,
                    'train_rows':len(fields['train']),'validation_rows':len(fields['val']),'test_rows':len(fields['test'])})
                print(json.dumps({'dataset':item['name'],'split':seed,'cells':len(rows)}),flush=True)
        value={'rows':rows,'rows_sha256':digest(rows),'design_sha256':digest(design),'files':files,
            'selections':all_selections,'resources':{'api_calls':0,'seconds':time.monotonic()-started,'fitted_models':280},
            'environment':{'numpy':np.__version__,'sklearn':sklearn.__version__,'blas_threads':2}}
        save_json(cache,value);return value

    def verify(self,value,design):
        self.check(design)
        if value['design_sha256']!=digest(design) or digest(value['rows'])!=value['rows_sha256']:raise ValueError('Raw results changed')
        for relative,sha in value['files'].items():
            path=(self.directory/relative).resolve()
            if not path.is_relative_to(self.directory) or file_digest(path)!=sha:raise ValueError('Saved prediction artifact changed')

    def audit(self,design):
        value=json.loads((self.root/'results.json').read_text(encoding='utf-8'));self.verify(value,design)
        methods=[*POLICIES,'known_p','oracle','knn_ridge','native_hist'];checked=0
        expected={(d['name'],s,c,m) for d in design['datasets'] for s in SPLITS for c in CONDITIONS for m in methods}
        if len(value['rows'])!=len(expected):raise ValueError('Missing or extra experiment rows')
        for item in design['datasets']:
            data=np.load(self.directory/item['path'],allow_pickle=False)
            for seed in SPLITS:
                folder=self.root/item['name']/str(seed);fields=np.load(folder/'affine.npz',allow_pickle=False)
                selection=json.loads((folder/'selection_before_test.json').read_text(encoding='utf-8'))
                coefficients=np.array(selection['validation_coefficients']);sampled=np.array(selection['sampled_validation_losses'])
                for policy in POLICIES:
                    if select_policy(policy,coefficients,sampled)!=selection['selected'][policy]:raise ValueError('Validation selection mismatch')
                xt=(data['x'][fields['test']]-fields['mu'])/fields['scale']
                for condition in CONDITIONS:
                    saved=np.load(folder/(condition+'.npz'),allow_pickle=False)
                    predictions=np.array([predict_pool(xt,mask,fields) for mask in saved['masks']])
                    np.testing.assert_allclose(predictions,saved['prediction'],atol=1e-10)
                    pool=((predictions-saved['y'][None,:,None])**2).mean(axis=0);oracle=int(np.argmin(pool.mean(axis=0)))
                    p=0. if condition=='clean' else float(condition.split('_')[1])
                    if saved['expected_pool_losses'].shape[1]:
                        exact=np.column_stack([expected_losses(xt,saved['y'],fields['a'][:,i],fields['b'][i],fields['fill'][:,i],fields['c'][:,i],p) for i in range(12)])
                        np.testing.assert_allclose(exact,saved['expected_pool_losses'],atol=1e-10)
                    for i,method in enumerate(methods):
                        ident=(item['name'],seed,condition,method)
                        matching=[r for r in value['rows'] if (r['dataset'],r['split_seed'],r['condition'],r['method'])==ident]
                        if len(matching)!=1:raise ValueError('Duplicated or missing method condition')
                        if method in POLICIES:loss=pool[:,selection['selected'][method]]
                        elif method=='known_p':loss=pool[:,selection['selected'][f'known_p_{p}']]
                        elif method=='oracle':loss=pool[:,oracle]
                        else:loss=((saved['reference'][:,:,0 if method=='knn_ridge' else 1]-saved['y'][None,:])**2).mean(axis=0)
                        np.testing.assert_allclose(loss,saved['losses'][:,i],atol=1e-10)
                        if abs(float(loss.mean())-matching[0]['normalized_mse'])>1e-10:raise ValueError('Metric replay mismatch')
                        checked+=1
        report={'status':'verified','cells':checked,'scope':'Recompute affine test predictions, analytic risk diagnostics, validation choices, and all metrics. Nonlinear reference predictions are replayed for metrics, not independently refitted.',
                'code_sha256':design['code_sha256']}
        save_json(self.root/'audit.json',report);return report
