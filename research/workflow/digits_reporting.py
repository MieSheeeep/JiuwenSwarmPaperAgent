"""Source-derived study tables and figures; no LLM-generated measurements."""
from collections import defaultdict
import csv
import json
from pathlib import Path
import numpy as np
from research.artifacts import save_json,file_digest,digest
from .digits_study import CONDITIONS,METHODS,SEEDS,softmax,selective_metrics

LABELS={'always_answer':'Always answer','msp':'Max probability','temperature_msp':'Temperature + max prob.',
        'logit_margin':'Logit margin','negative_entropy':'Negative entropy'}


def analyze(study,design):
    audit=study.audit(design)
    saved=json.loads((study.root/'results.json').read_text(encoding='utf-8'))
    groups=defaultdict(list)
    for row in saved['rows']:groups[(row['condition'],row['method'],row['target_coverage'])].append(row)
    summary=[]
    for (condition,method,target),rows in groups.items():
        values={}
        for key in ('coverage','selective_risk','overall_accuracy','aurc','nll','ece15'):
            numbers=[r[key] for r in rows if r[key] is not None]
            values[key]={'mean':float(np.mean(numbers)) if numbers else None,
                'sd':float(np.std(numbers,ddof=1)) if len(numbers)>1 else None,'defined_seeds':len(numbers)}
        summary.append({'condition':condition,'method':method,'target':target,'seeds':len(rows),
                        'min_accepted':min(r['accepted'] for r in rows),'metrics':values})
    out=study.directory/'analysis';out.mkdir(exist_ok=True)
    with (out/'all_metrics.csv').open('w',encoding='utf-8',newline='') as f:
        fieldnames=sorted({k for r in saved['rows'] for k in r});writer=csv.DictWriter(f,fieldnames=fieldnames)
        writer.writeheader();writer.writerows(saved['rows'])
    primary=[r for r in summary if r['target']==.8]
    drift=[{'condition':r['condition'],'method':r['method'],
            'mean_coverage_minus_target':r['metrics']['coverage']['mean']-.8} for r in primary]
    value={'metrics':summary,'claims':[{'status':'SUPPORTED','kind':'observed',
        'claim':'Frozen-threshold coverage, risk and calibration values recorded for every predeclared cell.',
        'evidence':saved['rows_sha256']}],
        'limitations':['One small 8x8 dataset, one split, shallow MLP, synthetic corruptions; no state-of-the-art or algorithm novelty claim.',
            'Five seeds share the same data and corruption realizations; seed SD is not independent-data uncertainty.',
            'Coverage targets are validation-derived thresholds, not guarantees under shift. No significance tests.',
            'Extreme corruption may remove digit identity while nominal labels remain unchanged.',
            'AURC uses stable sample-index tie breaking and all test ranks; it is not an operating-point error guarantee.'],
        'coverage_drift':drift,'audit':audit,'rows_hash':saved['rows_sha256'],
        'environment':saved['environment'],'resources':saved['resources'],
        'split_counts':{k:len(v) for k,v in design['split'].items()},
        'definition':'Selective risk = errors among accepted / number accepted; coverage = accepted / 360. Empty acceptance risk is undefined.',
        'temperature':[json.loads((study.root/str(seed)/'calibration.json').read_text(encoding='utf-8'))['temperature'] for seed in SEEDS]}
    value['figures']=make_figures(study,summary)
    value['tables']=make_tables(summary)
    save_json(out/'summary.json',value)
    return value


def make_tables(summary):
    rows=[]
    for condition in ('clean','gaussian_0.30','dropout_0.30'):
        for method in ('always_answer',*METHODS):
            row=next(r for r in summary if r['condition']==condition and r['method']==method and r['target']==(1. if method=='always_answer' else .8))
            cov=row['metrics']['coverage'];risk=row['metrics']['selective_risk']
            def fmt(v):
                return 'undefined' if v['mean'] is None else f"{100*v['mean']:.1f} ({100*v['sd']:.1f})"
            rows.append([condition.replace('_',' '),LABELS[method],fmt(cov),fmt(risk)])
    return [{'section':'Results','columns':['Condition','Rule','Coverage %','Error %'],
             'rows':rows,'caption':'Primary 80% validation-coverage threshold. Mean (sample SD) across five initializations on the same 360 test images. Always-answer has 100% coverage. Error is among accepted images; conditions shown here are predeclared display examples. All cells are in all_metrics.csv.'}]


def make_figures(study,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    directory=study.directory/'figures';directory.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    def select(condition,method):
        return next(r for r in summary if r['condition']==condition and r['method']==method and r['target']==.8)
    fig,axes=plt.subplots(2,2,figsize=(7.0,5.2),layout='constrained')
    for col,kind in enumerate(('gaussian','dropout')):
        conditions=['clean',*[c for c in CONDITIONS if c.startswith(kind)]]
        x=[0.,*[float(c.split('_')[1]) for c in conditions[1:]]]
        for method in METHODS:
            for row,metric in enumerate(('coverage','selective_risk')):
                points=[select(c,method)['metrics'][metric] for c in conditions]
                means=[100*p['mean'] if p['mean'] is not None else np.nan for p in points]
                sd=[100*p['sd'] if p['sd'] is not None else 0 for p in points]
                axes[row,col].errorbar(x,means,yerr=sd,marker='o',capsize=2,label=LABELS[method],linewidth=1.1,markersize=3)
        axes[0,col].axhline(80,color='gray',linestyle='--',linewidth=1)
        axes[0,col].set_title('Gaussian noise' if kind=='gaussian' else 'Pixel dropout')
        axes[1,col].set_xlabel('Noise standard deviation' if kind=='gaussian' else 'Drop probability')
        axes[0,col].set_ylabel('Realized coverage (%)');axes[1,col].set_ylabel('Accepted-sample error (%)')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=2,fontsize=8)
    path=directory/'coverage_risk.png';fig.savefig(path);plt.close(fig)
    figures=[{'section':'Results','path':path.relative_to(study.directory).as_posix(),'sha256':file_digest(path),
        'caption':'Frozen clean-validation thresholds at target coverage 80%. Error bars are sample SD over five initializations sharing the same data and corruption realizations, not confidence intervals. Coverage and error are distinct outcomes.'}]
    data=np.load(study.data,allow_pickle=False);x=data['x'][data['test']]
    fig,axes=plt.subplots(3,7,figsize=(7.,3.0),layout='constrained')
    for j,condition in enumerate(CONDITIONS):
        images=__import__('research.workflow.digits_study',fromlist=['corrupt']).corrupt(x,condition)
        for i in range(3):
            axes[i,j].imshow(images[i].reshape(8,8),cmap='gray',vmin=0,vmax=1);axes[i,j].axis('off')
        axes[0,j].set_title(condition.replace('gaussian_','G ').replace('dropout_','D '),fontsize=8)
    path=directory/'corruption_examples.png';fig.savefig(path);plt.close(fig)
    figures.insert(0,{'section':'Experimental Setup','path':path.relative_to(study.directory).as_posix(),'sha256':file_digest(path),
        'caption':'First three frozen test indices under every predeclared condition; not selected by model success or failure. G: clipped additive Gaussian noise. D: independent pixel dropout. Images are 8x8; strong corruption may obscure digit identity.'})
    return figures
