"""All-condition aggregation, row-clustered paired intervals and measured plots."""
from collections import defaultdict
from pathlib import Path
import csv
import json
import numpy as np
from research.artifacts import save_json,file_digest
from .missingness_study import POLICIES,CONDITIONS,SPLITS

LABELS={'clean':'Clean validation','mc_average3':'Sampled average (3)',
        'mc_worst1':'Sampled worst (1)','mc_worst3':'Sampled worst (3)','mc_worst9':'Sampled worst (9)',
        'analytic_grid':'Integrated grid','analytic_minimax':'Integrated interval',
        'known_p':'Known-rate selector','oracle':'Test-label pool oracle','knn_ridge':'KNN + Ridge','native_hist':'Native HistGB'}
METHODS=[*POLICIES,'known_p','oracle','knn_ridge','native_hist']


def cluster_interval(study,dataset):
    groups=defaultdict(lambda:np.zeros(3))
    ai=METHODS.index('analytic_minimax');bi=METHODS.index('clean')
    for seed in SPLITS:
        arrays=np.load(study.root/dataset/str(seed)/'mcar_0.5.npz',allow_pickle=False)
        for i,row_id in enumerate(arrays['test_indices']):
            groups[int(row_id)]+=np.array([arrays['losses'][i,ai],arrays['losses'][i,bi],1.])
    values=np.array(list(groups.values()));rng=np.random.default_rng(20261107)
    sample=rng.integers(0,len(values),size=(1000,len(values)))
    sums=values[sample].sum(axis=1)
    differences=np.sqrt(sums[:,0]/sums[:,2])-np.sqrt(sums[:,1]/sums[:,2])
    point=np.sqrt(values[:,0].sum()/values[:,2].sum())-np.sqrt(values[:,1].sum()/values[:,2].sum())
    lo,hi=np.quantile(differences,[.025,.975])
    return {'dataset':dataset,'condition':'mcar_0.5','contrast':'analytic_minimax minus clean',
        'delta_normalized_rmse':float(point),'conditional_cluster_percentile_95':[float(lo),float(hi)],
        'unique_row_clusters':len(values),'bootstrap_draws':1000,
        'scope':'Conditional on fitted models, fixed repeated splits and masks; original row IDs are resampling clusters. Not retraining uncertainty, not a familywise test.'}


def summarize(study,design):
    audit=study.audit(design)
    raw=json.loads((study.root/'results.json').read_text(encoding='utf-8'))
    groups=defaultdict(list)
    for r in raw['rows']:groups[(r['dataset'],r['condition'],r['method'])].append(r)
    metrics=[]
    for (dataset,condition,method),rows in groups.items():
        nrmse=[r['normalized_rmse'] for r in rows];regret=[r['regret_pool_mse'] for r in rows]
        metrics.append({'dataset':dataset,'condition':condition,'method':method,
            'nrmse_mean':float(np.mean(nrmse)),'nrmse_split_sd':float(np.std(nrmse,ddof=1)),
            'regret_mse_mean':float(np.mean(regret)),'actual_missing_fraction':float(np.mean([r['actual_missing_fraction'] for r in rows]))})
    intervals=[cluster_interval(study,d['name']) for d in design['datasets']]
    selections=[]
    for s in raw['selections']:
        choices=s['selected'];selections.append({'dataset':s['dataset'],'split_seed':s['split_seed'],
            'clean_candidate':s['names'][choices['clean']],'integrated_candidate':s['names'][choices['analytic_minimax']],
            'sampled_worst9_candidate':s['names'][choices['mc_worst9']],
            'integrated_and_sampled9_agree':choices['analytic_minimax']==choices['mc_worst9'],
            'split_counts':[s['train_rows'],s['validation_rows'],s['test_rows']],
            'sampled27_ms':1000*s['mc_27_draw_evaluation_seconds'],
            'integrated_with_coefficients_ms':1000*s['analytic_with_coefficients_seconds']})
    out=study.directory/'analysis';out.mkdir(exist_ok=True)
    with (out/'all_metrics.csv').open('w',encoding='utf-8',newline='') as f:
        fields=list(raw['rows'][0]);writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(raw['rows'])
    value={'metrics':metrics,'paired_intervals':intervals,'selection_records':selections,'audit':audit,
        'dataset_facts':design['datasets'],'resources':raw['resources'],'environment':raw['environment'],
        'claims':[{'status':'SUPPORTED','kind':'observed','evidence':raw['rows_sha256'],
                   'claim':'All prespecified selection policies evaluated on common held-out missing masks; direction and size of effects are reported without requiring improvement.'}],
        'limitations':['Four small UCI regression datasets from three families; red and white wine are related.',
            'Exact feature duplicates are grouped across split partitions; unseen physical-configuration generalization is not established.',
            'Analytic mask integration applies to fixed affine predictors with constant fills and independent MCAR masks; not to KNN or nonlinear models.',
            'Training is artificially MCAR at 10%; complete validation data is assumed available.',
            'Block and anchor-dependent stress tests are synthetic and outside the analytic MCAR assumption.',
            'Repeated feature-group splits overlap. Split SD is dispersion, not an independent-data confidence interval.',
            'Paired intervals condition on fitted models, split memberships and masks; four per-dataset intervals are not simultaneous guarantees.',
            'Native HistGB and KNN references lie outside the 12-candidate pool; oracle and known-rate selectors have extra information.',
            'Validation timing is one local measurement excluding fitting; not an end-to-end deployment speed benchmark.',
            'Related dropout and missingness-shift work predates this application; algorithm novelty remains unverified.'],
        'rows_hash':raw['rows_sha256'],'theory':theory_text()}
    value['figures']=figures(study,metrics,selections,intervals)
    value['tables']=tables(metrics,intervals)
    save_json(out/'summary.json',value);return value


def theory_text():
    return {'assumptions':'Fixed fitted coefficients and fills; complete validation rows; squared loss; missing indicators independent across features with common rate p. Missing-indicator coefficients may be zero.',
        'prediction':'prediction = b + sum_j a_j*((1-M_j)*x_j+M_j*f_j) + sum_j c_j*M_j.',
        'definitions':'e=b+a^T x-y; d_j=a_j(f_j-x_j)+c_j; M_j is 1 for missing and Bernoulli(p).',
        'identity':'E[(prediction-y)^2|x,y] = (e+p*sum_j d_j)^2 + p*(1-p)*sum_j d_j^2.',
        'quadratic_coefficients':'Validation mean gives A=mean[(sum d)^2-sum d^2], B=mean[2e sum d+sum d^2], C=mean[e^2]. R(p)=A p^2+B p+C.',
        'envelope':'Maximum over [0.1,0.5] occurs at an endpoint or p*=-B/(2A) if A<0 and p* is interior. Choose the candidate with smallest such finite-validation maximum.',
        'proof':'Prediction error equals e+sum_j M_j*d_j. Conditional mean is e+p sum d. Independence gives variance p(1-p) sum d^2. Mean square = squared mean + variance. Average over rows and maximize the quadratic.',
        'boundary':'This integrates artificial masks exactly on the finite validation sample. It does not guarantee population risk, validity for correlated/MAR masks, or superiority on test data. The expected-loss algebra is related to existing dropout theory; no first-of-kind theorem claim.'}


def tables(metrics,intervals):
    main=[]
    for dataset in ('wine_red','wine_white','airfoil','yacht'):
        for method in ('clean','mc_worst9','analytic_minimax','known_p','knn_ridge','native_hist'):
            r=next(r for r in metrics if (r['dataset'],r['condition'],r['method'])==(dataset,'mcar_0.5',method))
            main.append([dataset.replace('_',' '),LABELS[method],f"{r['nrmse_mean']:.3f} ({r['nrmse_split_sd']:.3f})"])
    uncertainty=[[r['dataset'].replace('_',' '),f"{r['delta_normalized_rmse']:+.4f}",
                  '['+', '.join(f'{v:+.4f}' for v in r['conditional_cluster_percentile_95'])+']'] for r in intervals]
    return [{'section':'Results','columns':['Dataset','Selection / reference','Normalized RMSE'], 'rows':main,
        'caption':'50% independent missingness. Mean (sample SD) of split-level normalized RMSE across five overlapping feature-group splits. All methods use the same nine test masks per split. Known-rate selection has the declared p; KNN and HistGB are references outside the shared 12-candidate pool.'},
        {'section':'Results','columns':['Dataset','Paired delta','Conditional 95% interval'],'rows':uncertainty,
        'caption':'Integrated-interval selector minus clean-validation selector at MCAR p=0.5. Delta uses root pooled mean losses; it need not equal the difference of split-mean RMSE in Table 1. Paired bootstrap clusters original row IDs across repeated test memberships, conditions on fitted models/splits/masks, and is not simultaneous across datasets.'}]


def figures(study,metrics,selections,intervals):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=study.directory/'figures';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    records=[]
    fig,axes=plt.subplots(2,2,figsize=(7.,5.0),layout='constrained')
    for ax,dataset in zip(axes.flat,('wine_red','wine_white','airfoil','yacht')):
        for method in ('clean','mc_worst9','analytic_minimax','native_hist'):
            series=[next(r for r in metrics if (r['dataset'],r['condition'],r['method'])==(dataset,condition,method)) for condition in ('clean','mcar_0.1','mcar_0.3','mcar_0.5')]
            ax.plot([0,.1,.3,.5],[r['nrmse_mean'] for r in series],marker='o',markersize=3,label=LABELS[method])
        ax.set_title(dataset.replace('_',' '));ax.set_xlabel('MCAR rate');ax.set_ylabel('Normalized RMSE')
    handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=2,fontsize=8)
    path=out/'mcar_risk.png';fig.savefig(path,dpi=190);plt.close(fig)
    records.append({'section':'Results','path':path.relative_to(study.directory).as_posix(),'sha256':file_digest(path),
        'caption':'Held-out normalized RMSE under independent missingness, averaged over five feature-group splits. Shared test masks are used across methods. Native HistGB is an external model-class reference, not eligible for the linear selectors.'})
    fig,axes=plt.subplots(1,2,figsize=(7.,3.),layout='constrained')
    x=np.arange(4)
    axes[0].errorbar(x,[r['delta_normalized_rmse'] for r in intervals],
        yerr=np.array([[r['delta_normalized_rmse']-r['conditional_cluster_percentile_95'][0] for r in intervals],
                       [r['conditional_cluster_percentile_95'][1]-r['delta_normalized_rmse'] for r in intervals]]),fmt='o',capsize=4)
    axes[0].axhline(0,color='gray',linestyle='--');axes[0].set_xticks(x,[r['dataset'].replace('_','\n') for r in intervals]);axes[0].set_ylabel('Paired normalized RMSE delta');axes[0].set_title('Integrated minus clean, p=0.5')
    means=[]
    for condition in ('mcar_0.3','block_0.3','mar_0.3'):
        differences=[]
        for dataset in ('wine_red','wine_white','airfoil','yacht'):
            a=next(r for r in metrics if (r['dataset'],r['condition'],r['method'])==(dataset,condition,'analytic_minimax'))
            b=next(r for r in metrics if (r['dataset'],r['condition'],r['method'])==(dataset,condition,'clean'))
            differences.append(a['nrmse_mean']-b['nrmse_mean'])
        means.append(differences)
    for i,dataset in enumerate(('wine red','wine white','airfoil','yacht')):
        axes[1].plot(np.arange(3),[v[i] for v in means],marker='o',label=dataset)
    axes[1].axhline(0,color='gray',linestyle='--');axes[1].set_xticks(np.arange(3),['MCAR','Block','Anchor MAR']);axes[1].set_ylabel('Split-mean RMSE delta');axes[1].set_title('Assumption stress test');axes[1].legend(fontsize=7)
    path=out/'paired_and_stress.png';fig.savefig(path,dpi=190);plt.close(fig)
    records.append({'section':'Discussion','path':path.relative_to(study.directory).as_posix(),'sha256':file_digest(path),
        'caption':'Left: conditional row-clustered paired intervals at p=0.5, with no model refitting. Right: split-mean normalized RMSE difference versus clean-validation selection under independent, correlated-block and anchor-dependent masks at nominal p=0.3. The analytic model does not cover the latter two mechanisms; actual missing fractions are reported separately.'})
    return records
