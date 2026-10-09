"""Offline analysis of paired tasks; all counts derive from saved records."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics

from baseline.run import POLICIES


def wilson(k,n):
    if not n:
        return [0,1]
    z=1.95996398454
    p=k/n
    denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    return [max(0,center-half),min(1,center+half)]


def analyze(directory):
    directory=Path(directory)
    rows=[json.loads(line) for line in (directory/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    calls=[json.loads(line) for line in (directory/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    pairs={(r['task_id'],r['policy']):r for r in rows}
    if len(pairs)!=len(rows) or len(rows)!=manifest['tasks']*len(POLICIES):
        raise ValueError('Run is incomplete or has duplicate results')
    associated=[call_id for row in rows for call_id in row['call_ids']]
    recorded=[c['id'] for c in calls]
    if len(set(recorded))!=len(recorded) or len(set(associated))!=len(associated) or set(associated)!=set(recorded):
        raise ValueError('Orphan, duplicate, or missing call associations; reconcile the interrupted run before analysis')
    summary=[]
    groups=[]
    for policy in POLICIES:
        selected=[r for r in rows if r['policy']==policy]
        used=[c for c in calls if c['tag'].split('/')[1]==policy]
        successful=[r for r in selected if r['status']=='ok']
        correct=sum(r['score']['exact'] for r in selected)
        if any(c['usage'] is None for c in used):
            raise ValueError('API usage metadata is missing')
        token_sums={field:sum(c['usage'].get(field,0) for c in used)
                    for field in ['input_tokens','output_tokens','total_tokens','cache_tokens','reasoning_tokens']}
        summary.append({'policy':policy,'tasks':len(selected),'correct':correct,
            'exact_accuracy':correct/len(selected),'wilson_95':wilson(correct,len(selected)),
            'field_accuracy':sum(sum(r['score']['fields'].values()) for r in selected)/(3*len(selected)),
            'api_failures':len(selected)-len(successful),'api_calls':len(used),**token_sums,
            'mean_tokens_per_task':token_sums['total_tokens']/len(selected),
            'mean_seconds_per_task':statistics.mean(r['elapsed_seconds'] for r in successful) if successful else None,
            'mean_history_proxy_tokens':statistics.mean(r['history_estimated_tokens'] for r in successful) if successful else None})
        for group_key in ['family','position']:
            for group in sorted({r[group_key] for r in selected}):
                rr=[r for r in selected if r[group_key]==group]
                groups.append({'policy':policy,'group_key':group_key,'group':group,
                               'n':len(rr),'correct':sum(r['score']['exact'] for r in rr)})
    paired=[]
    for policy in POLICIES[1:]:
        b=c=both=neither=0
        for task_id in sorted({r['task_id'] for r in rows}):
            reference=pairs[(task_id,'full')]['score']['exact']
            candidate=pairs[(task_id,policy)]['score']['exact']
            b+=int(reference and not candidate)
            c+=int(candidate and not reference)
            both+=int(reference and candidate)
            neither+=int(not reference and not candidate)
        discordant=b+c
        p=min(1,2*sum(math.comb(discordant,i) for i in range(min(b,c)+1))/2**discordant) if discordant else 1.0
        paired.append({'reference':'full','candidate':policy,'reference_only':b,
                       'candidate_only':c,'both_correct':both,'both_wrong':neither,
                       'exact_mcnemar_p_exploratory':p})
    result={'manifest':manifest,'methods':summary,'groups':groups,'paired':paired,
            'total_api_calls':len(calls),'total_api_tokens':sum(s['total_tokens'] for s in summary),
            'interpretation':'Synthetic convenience sample; Wilson intervals are descriptive. '
                             'Paired tests are exploratory, not corrected for multiple comparisons. '
                             'No equivalence or generalization claim.'}
    (directory/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (directory/'summary.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summary[0]))
        writer.writeheader(); writer.writerows(summary)
    report=['# Baseline results','',f'Model: `{manifest["model"]}`. Tasks: {manifest["tasks"]}; deterministic seed: {manifest["seed"]}.',
            '', '| Method | Correct | Exact accuracy | API tokens including summary | Mean seconds |',
            '|---|---:|---:|---:|---:|']
    for s in summary:
        report.append(f'| {s["policy"]} | {s["correct"]}/{s["tasks"]} | {s["exact_accuracy"]:.1%} | {s["total_tokens"]:,} | {s["mean_seconds_per_task"]:.2f} |')
    report.extend(['','These are actual API-backed results, not a competition score.',
                   'The full-history method is an unbounded reference. Recent and retrieval methods share a 512 cl100k_base-token history budget; this tokenizer is a proxy, not DeepSeek billing.',
                   'Retrieval explicitly matches the project identifier in the question and retains updates in chronological order. This easy lexical structure favors retrieval; it is not an evaluation of semantic retrieval.',
                   'Summary performs one extra model call on retrieved records; all its input/output tokens are included. The returned summary is capped at 256 proxy tokens.',
                   'One run per case, one model, synthetic data, no real tool execution, no held-out generalization test, and no assertion of new scientific novelty.'])
    (directory/'RESULTS.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    return result


def plot(directory,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    directory=Path(directory)
    labels=['Full history','Recent window','Project retrieval','Retrieval + summary']
    methods=summary['methods']
    accuracy=np.array([s['exact_accuracy']*100 for s in methods])
    lower=accuracy-np.array([s['wilson_95'][0]*100 for s in methods])
    upper=np.array([s['wilson_95'][1]*100 for s in methods])-accuracy
    colors=['#0072B2','#D55E00','#009E73','#CC79A7']
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'ps.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(7.0,3.0),layout='constrained')
    x=np.arange(4)
    axes[0].bar(x,accuracy,color=colors,yerr=np.vstack([lower,upper]),capsize=4)
    axes[0].set_ylim(0,110); axes[0].set_ylabel('Exact-match accuracy (%)')
    axes[0].set_title('(a) 24 synthetic tasks\n95% Wilson intervals',fontsize=10)
    axes[1].bar(x,[s['mean_tokens_per_task'] for s in methods],color=colors)
    axes[1].set_ylabel('API tokens per task (input + output)')
    axes[1].set_title('(b) API token usage\nSummary overhead included',fontsize=10)
    for ax in axes:
        ax.set_xticks(x,labels,rotation=24,ha='right')
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    fig.savefig(directory/'results_figure.pdf',bbox_inches='tight')
    fig.savefig(directory/'results_figure.png',dpi=300,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='output/baseline')
    args=parser.parse_args();result=analyze(args.output);plot(args.output,result)
    print(json.dumps(result['methods'],indent=2))
