"""Chapter-level English writing from the new evidence, with a separate bounded ledger."""
import argparse
import asyncio
import json
from pathlib import Path
import re
import shutil
import subprocess

from research.artifacts import digest, file_digest, save_json
from research.jsonl_ledger import read_jsonl,configure_gateway_ledger
from research.model_gateway import ModelGateway
from research.memory_paper import REFERENCES,tex_escape

SECTIONS=('methods','related_work','introduction','discussion','conclusion','abstract')
TITLE='Separating Evidence Retrieval, Temporal Packing and Conflict-Aware Reading in Agent Memory'
configure_gateway_ledger()


def parse_json_object(value):
    value=value.strip()
    fenced=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```',value,re.S|re.I)
    if fenced:value=fenced.group(1)
    result=json.loads(value)
    if not isinstance(result,dict):raise ValueError('Require a JSON object')
    return result


def check_sections(sections,reference_keys):
    if not isinstance(sections,dict) or set(sections)!=set(SECTIONS):return ['Require exactly six manuscript sections']
    issues=[]
    for name,text in sections.items():
        if not isinstance(text,str) or not text.strip():issues.append(name+': empty');continue
        stripped=re.sub(r'\b(?:BM25|Mem0|cl100k_base|(?:all-)?MiniLM-L6-v2|MiniLM-L6|V4(?:\.1)?)\b','KnownName',text,flags=re.I)
        if re.search(r'\d|%',stripped):issues.append(name+': measured numbers belong in generated evidence tables')
        cited=[key.strip().lower() for group in re.findall(r'\[([^\]]+)\]',text) for key in re.split('[,;]',group)]
        if set(cited)-set(reference_keys):issues.append(name+': unverified citation')
        if re.search(r'[\u3400-\u9fff]',text):issues.append(name+': English required')
        if re.search(r'we (?:propose|introduce|demonstrate|achieve).{0,50}(?:novel|state.of.the.art|statistically significant)',text,re.I):issues.append(name+': unsupported strength or novelty claim')
    return issues


def implementation_contract():
    return {
        'versioned_selection':'Structured records are filtered by entity, attributes, valid_at <= as_of and observed_at <= known_at. Per attribute, every record tied at maximal valid_at forms an indivisible group, including conflicts and deletions. No interval-overlap model is implemented.',
        'packing':'The current packer prefers smaller groups. Dynamic programming optimizes an additive surrogate: unit attribute-group utility for versioned records, reciprocal-rank utility for retrieval-ranked records. It is not learned downstream utility and not guaranteed optimal under the actual nonadditive tokenizer. Joined text is recounted.',
        'rail':'The exact-message Rail checks the already selected and packed system/user messages at final model transport. It does not bypass retrieval or packing and does not send all history. Reflection preserves the explicit multi-turn draft/audit history.',
        'reader':'The baseline already requires conflict handling and null for unresolved maximal-time claims. Conflict-aware reading is an additional prompt instructing internal verification of both cutoffs, maximal valid_at, competing values and set/delete ties, with null for unresolved conflicts/deletion. No graph extraction, support propagation, evidential fusion or learned uncertainty calibration was implemented.',
        'external':'Raw LongMemEval sessions are split into fixed proxy-token passages. BM25, compact local MiniLM and equal-weight RRF rank passages; source dates/session IDs are preserved. Structured temporal filtering is not applied to raw dialogue, and successful bitemporal fact extraction is not demonstrated.',
        'workflow':'A fresh real ReActAgent executes each frozen invocation without tools or streaming. This is an auditable evaluation/writing workflow, not an evaluated autonomous hypothesis-discovery system.',
        'completion':'answer_conditions_complete reports completion of all planned answers and adapted judgments. evaluation_complete remains false solely because historical failed requests lack provider usage; conservative admission holds retain that uncertainty. Full-corpus main arm and matched diagnostic comparison have distinct denominators.'}


def compact_evidence(summary,analysis):
    rows=[]
    for row in summary.get('methods',[]):
        if row.get('repeat',0)!=0:continue
        if row.get('phase') not in ('mechanism','retrieval','packing','external','controls','budget'):continue
        if row.get('phase')=='packing' and row.get('budget')!=512:continue
        rows.append({k:row.get(k) for k in ('kind','cohort','phase','model','policy','packer','reader','budget','tasks','planned_tasks','exact_correct','exact_accuracy','judge_correct','judge_scored','judge_accuracy','actual_total_tokens')})
    return {'evaluation_complete':summary.get('evaluation_complete',False),'answer_conditions_complete':summary.get('answer_conditions_complete',False),'completed':summary.get('completed'),
            'planned':summary.get('planned'),'terminal_reason':summary.get('terminal_reason'),'comparisons':rows,
            'resources':summary.get('resources',{}),'limitations':summary.get('limitations',[]),
            'paired_contrasts':[dict(family=c['family'],left=c['left'],right=c['right'],n=c['n_paired'],difference=c['difference_left_minus_right'],condition=c['condition'])
                                for c in analysis.get('contrasts',[]) if c.get('n_paired') and
                                (c['condition'].get('phase')=='mechanism' and c['condition'].get('budget')==256 or
                                 c['metric']=='external_judge_proxy' or
                                 c['family']=='packing' and c['condition'].get('budget')==512 or
                                 c['family']=='budget' and c['condition'].get('cohort')=='synthetic_controlled')],
            'full_external_main':external_full_summary(summary),'significance_claim_permitted':False,'implementation_contract':implementation_contract()}


def external_full_summary(summary):
    selected=[m for m in summary.get('methods',[]) if m.get('kind')=='external' and 'flash' in m.get('model','').lower()
              and m.get('policy')=='hybrid' and m.get('reader')=='baseline' and m.get('repeat',0)==0 and m.get('budget')==1024]
    return {'policy':'hybrid','model':'deepseek-flash','planned_tasks':sum(m.get('planned_tasks',0) for m in selected),
            'completed_tasks':sum(m.get('successes',0) for m in selected),'exact_correct':sum(m.get('exact_correct',0) for m in selected),
            'judge_correct':sum(m.get('judge_correct',0) for m in selected),'judge_scored':sum(m.get('judge_scored',0) for m in selected),
            'scope':'Full-corpus main arm only; never a matched-retriever or model comparison.'}


def load_references(root):
    refs=[dict(r) for r in REFERENCES]
    for ref in refs:
        if ref['key']=='longmemeval':
            ref['finding']='The cleaned original LongMemEval corpus was evaluated here using passage retrieval and lexical/adapted-judge proxies. Official evaluator reproduction and interactive online-memory validation remain future work.'
    path=root/'sources/review_related_work_20261106.json'
    if path.exists():
        value=json.loads(path.read_text(encoding='utf-8'))
        entries=value if isinstance(value,list) else value.get('entries',value.get('references',[]))
        for ref in entries:
            key=re.sub('[^a-z_]','',ref['key'].lower())
            if ref.get('verification_status')=='verified' and key not in {r['key'] for r in refs} and ref['url'] not in {r['url'] for r in refs}:
                refs.append({**ref,'key':key})
    return refs


def _tex_prose(text,keys):
    parts=re.split(r'(\[[A-Za-z_,;\s]+\])',text)
    output=[]
    for part in parts:
        if re.fullmatch(r'\[[A-Za-z_,;\s]+\]',part):
            cited=[x.strip().lower() for x in re.split('[,;]',part[1:-1])]
            if set(cited)<=keys:output.append(r'\citep{'+','.join(cited)+'}');continue
        output.append(tex_escape(part))
    return ''.join(output)


def _figures(run,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from research.review_upgrade import combine_judgments
    rows=combine_judgments(run)
    models=json.loads((run/'protocol.json').read_text(encoding='utf-8'))['models']
    specs=[('bm25','baseline'),('dense','baseline'),('hybrid','baseline'),('versioned','baseline'),('no_conflict','baseline'),('versioned','conflict_aware'),('no_conflict','conflict_aware')]
    mapping={}
    for model in models:
        for policy,reader in specs:
            mapping[(model,policy,reader)]={r['task_id']:r for r in rows if r['kind']=='synthetic' and r['cohort']=='synthetic_controlled' and r['model']==model and r['policy']==policy and r['reader']==reader and r['budget']==256 and r['repeat']==0 and r['status']=='ok' and r['phase'] in ('mechanism','retrieval')}
    common=set.intersection(*(set(v) for v in mapping.values())) if mapping else set()
    descriptions={}
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False}):
        from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
        fig,ax=plt.subplots(figsize=(6.5,3.4));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
        nodes=[(.03,.69,'Frozen input','Structured records / dialogues'),(.365,.69,'Evidence selection','Temporal / lexical / neural'),
               (.70,.69,'Budgeted packing','Atomic groups + token recheck'),(.70,.34,'Fresh ReActAgent','Baseline / verify / reflect'),
               (.365,.34,'Matched evaluation','Exact / adapted model judge'),(.03,.34,'Evidence-linked writing','English LaTeX + critique')]
        for x,y,title,detail in nodes:
            ax.add_patch(FancyBboxPatch((x,y),.27,.20,boxstyle='round,pad=0.012',linewidth=.9,edgecolor='#0072B2',facecolor='#EDF6FB'))
            ax.text(x+.135,y+.135,title,ha='center',va='center',fontsize=8,fontweight='bold')
            ax.text(x+.135,y+.063,detail,ha='center',va='center',fontsize=6.5)
        for start,end in [((.31,.79),(.345,.79)),((.645,.79),(.68,.79)),((.835,.665),(.835,.565)),
                          ((.68,.44),(.655,.44)),((.345,.44),(.32,.44))]:
            ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=11,linewidth=1,color='#0072B2'))
        ax.add_patch(FancyBboxPatch((.03,.115),.94,.12,boxstyle='round,pad=0.012',linewidth=.8,edgecolor='#009E73',facecolor='#EAF7F1'))
        ax.text(.5,.175,'Durable request / usage ledger · shared API budget · explicit unknown-spend holds',ha='center',va='center',fontsize=7)
        ax.text(.5,.035,'Temporal filtering and atomic conflict groups apply to structured records; raw-dialogue retrieval is a separate scope.',ha='center',va='center',fontsize=6)
        fig.tight_layout(pad=.3)
        for suffix in ('pdf','png','svg'):fig.savefig(output/f'architecture.{suffix}',dpi=220)
        plt.close(fig)
        descriptions['architecture']={'scope':'Implemented workflow only; diagram does not establish scientific novelty or efficacy.',
                                      'source_protocol_sha256':file_digest(run/'protocol.json')}
        fig,axes=plt.subplots(1,len(models),figsize=(6.5,3.2),squeeze=False,layout='constrained')
        for ax,model in zip(axes[0],models):
            if common:
                values=[sum(mapping[(model,p,r)][task]['score']['exact'] for task in common)/len(common)*100 for p,r in specs]
                ax.barh(range(len(specs)),values,color=['#0072B2']*5+['#009E73']*2)
                ax.set_yticks(range(len(specs)),[p.replace('_',' ') + (' + verify' if r=='conflict_aware' else '') for p,r in specs],fontsize=7)
                ax.invert_yaxis();ax.set_xlim(0,105);ax.set_xlabel('Strict exact accuracy (%)')
                ax.set_title(model+f' (matched n={len(common)})',fontsize=8)
            else:ax.text(.5,.5,'Matched comparison pending',ha='center',va='center');ax.axis('off')
        fig.savefig(output/'comparison.pdf');fig.savefig(output/'comparison.png',dpi=220);fig.savefig(output/'comparison.svg');plt.close(fig)
        descriptions['comparison']={'task_ids_sha256':digest(sorted(common)),'matched_tasks':len(common),'scope':'Common repeat-zero normal synthetic tasks across all displayed models/policies/readers.'}
        extmap={(model,policy):{r['task_id']:r for r in rows if r['kind']=='external' and r['cohort']=='external_matched' and r['model']==model and r['policy']==policy and isinstance(r.get('judge',{}).get('correct'),bool)} for model in models for policy in ('bm25','dense','hybrid')}
        extcommon=set.intersection(*(set(v) for v in extmap.values())) if extmap else set()
        fig,ax=plt.subplots(figsize=(6.5,2.7),layout='constrained')
        if extcommon:
            positions=list(range(3));width=.32
            for index,model in enumerate(models):
                values=[sum(extmap[(model,p)][t]['judge']['correct'] for t in extcommon)/len(extcommon)*100 for p in ('bm25','dense','hybrid')]
                ax.bar([x+(index-.5)*width for x in positions],values,width,label=model,color=('#0072B2','#009E73')[index%2])
            ax.set_xticks(positions,['BM25','Dense','Hybrid RRF']);ax.set_ylim(0,105);ax.set_ylabel('Adapted judge correct (%)');ax.legend(frameon=False,fontsize=7)
            ax.set_title(f'LongMemEval matched subset (n={len(extcommon)}); not an official benchmark score',fontsize=8)
        else:ax.text(.5,.5,'Matched external semantic evaluations pending',ha='center',va='center');ax.axis('off')
        for suffix in ('pdf','png','svg'):fig.savefig(output/f'external.{suffix}',dpi=220)
        plt.close(fig)
        descriptions['external']={'task_ids_sha256':digest(sorted(extcommon)),'matched_tasks':len(extcommon),'scope':'Common valid adapted-judge outcomes; model-judge bias and shared histories remain limitations.'}
    save_json(output/'figure_manifest.json',{'skills':['scientific-visualization','matplotlib'],'source_files':{name:file_digest(run/name) for name in ('results.jsonl','judgments.jsonl','summary.json') if (run/name).exists()},'figures':descriptions,'rules':['English labels','vector PDF/SVG','colorblind-safe palette','common tasks only','no invented error bars']})


def render(sections,summary,analysis,protocol,refs,output):
    keys={r['key'] for r in refs}
    if check_sections(sections,keys):raise ValueError('Cannot render unchecked chapter prose')
    tex=[r'\documentclass{article}',r'\usepackage{iclr2026_conference,times}',r'\usepackage{graphicx,booktabs,hyperref}',r'\hypersetup{hidelinks}',r'\iclrfinalcopy',
         r'\title{'+tex_escape(TITLE)+'}',r'\author{Anonymous Competition Research System}',r'\begin{document}',r'\maketitle',
         r'\lhead{Competition research manuscript -- no conference submission}',
         r'\noindent\textbf{Unreviewed research revision. Previous external scores do not apply.}',r'\begin{abstract}',_tex_prose(sections['abstract'],keys),r'\end{abstract}']
    md=['# '+TITLE,'','Unreviewed research revision. Previous external scores do not apply.','','## Abstract','',sections['abstract']]
    tex += [r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{architecture.pdf}\caption{Implemented research workflow. Temporal filtering and atomic conflict grouping operate on structured records; dialogue passages use a separate retrieval interface. The ledger covers paid answering, adapted judging and writing.}\end{figure}']
    for name in ('introduction','related_work','methods'):
        title=name.replace('_',' ').title();tex += [r'\section{'+title+'}',_tex_prose(sections[name],keys)];md += ['', '## '+title,'',sections[name]]
    protocol_text=(f"The frozen protocol defines 100 synthetic tasks: 16 development tasks and 84 held-out tasks, including 72 controlled cases across three new seed namespaces and 12 packing-stress cases. "
                   f"It registers {summary['planned']} answer conditions across the requested model aliases. The external corpus contains 500 verified-source LongMemEval questions. "
                   "A fixed stratified 70-question subset supports matched retrieval and backbone comparisons; a separate hybrid-Flash arm covers the full corpus. "
                   "External histories are split into 192 cl100k_base-token passages, while the dense encoder truncates at 256 wordpieces. Selected external contexts are bounded by 1024 proxy tokens. "
                   "Context budgets differ from billed provider tokens. Responses, reflection and adapted-judge calls are charged to one experiment ledger. Repeated zero-temperature calls are consistency checks, not independent provider sampling seeds.")
    tex += [r'\subsection{Frozen Protocol}',tex_escape(protocol_text),r'\section{Evaluation}'];md += ['', '### Frozen protocol','',protocol_text,'','## Evaluation']
    completion=f"The run completed {summary['completed']} of {summary['planned']} planned answer conditions. The experiment ledger records {summary['resources']['total_calls']} calls and {summary['resources']['total_tokens']} provider tokens. "
    if summary.get('answer_conditions_complete'):
        completion+='All planned answer conditions completed with valid adapted judgments. '
        if not summary['evaluation_complete']:
            completion+=(f"Billing reconciliation remains incomplete: {summary['resources']['unknown_usage_calls']} historical failed attempts have unknown provider usage. "
                         f"A conservative {summary['resources'].get('reserved_unknown_tokens',0)}-token admission hold was retained; this is an estimate, not measured usage. ")
    else:completion+='The protocol is incomplete; unrun, failed or invalid judgments remain explicitly excluded, and no full-grid success is claimed.'
    full=external_full_summary(summary)
    completion+=(f" The separate full-corpus hybrid-Flash arm completed {full['completed_tasks']} of {full['planned_tasks']} questions: normalized exact {full['exact_correct']}/{full['completed_tasks']}, adapted judge {full['judge_correct']}/{full['judge_scored']}. These are proxy diagnostics, not official benchmark scores.")
    tex += [tex_escape(completion),r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{comparison.pdf}\caption{Common-task synthetic comparison. Exact denominators and task hashes are in the figure manifest.}\end{figure}',
            r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{external.pdf}\caption{Matched external comparison using an adapted DeepSeek judge. This is not an official LongMemEval result.}\end{figure}'];md += ['',completion]
    for cohort,title in [('synthetic_controlled','Controlled main conditions'),('external_matched','Matched external subset')]:
        phases=('packing',) if cohort=='synthetic_packing' else ('mechanism','retrieval','external')
        budgets=(512,) if cohort=='synthetic_packing' else (256,1024)
        selected=[m for m in summary['methods'] if m['cohort']==cohort and m['repeat']==0 and m['phase'] in phases and m['budget'] in budgets]
        tex += [r'\begin{table}[ht]\centering\footnotesize\begin{tabular}{lllrr}\toprule',r'Model & Policy & Reader & Exact & Judge \\ \midrule']
        md += ['', '### '+title,'','| Model | Policy | Reader | Exact / completed | Judge / scored |','|---|---|---|---:|---:|']
        for row in selected:
            model='Pro' if 'pro' in row['model'].lower() else 'Flash';policy=row['packer' if cohort=='synthetic_packing' else 'policy'].replace('_',' ');reader=row['reader'].replace('_',' ')
            exact=f"{row['exact_correct']}/{row['successes']}";judge=f"{row['judge_correct']}/{row['judge_scored']}" if row['judge_scored'] else '--'
            tex.append(' & '.join([tex_escape(model),tex_escape(policy),tex_escape(reader),exact,judge])+r' \\')
            md.append(f'| {model} | {policy} | {reader} | {exact} | {judge} |')
        tex += [r'\bottomrule\end{tabular}\caption{'+tex_escape(title)+r'. Exact task sets and missingness are retained in the report; only matched intersections support paired contrasts.}\end{table}']
    packed={}
    for row in summary['methods']:
        if row['cohort']=='synthetic_packing' and row['phase']=='packing' and row['repeat']==0:
            packed.setdefault((row['model'],row['packer'],row['reader']),{})[row['budget']]=row
    tex += [r'\begin{table}[ht]\centering\footnotesize\begin{tabular}{lllrrr}\toprule',r'Model & Packer & Reader & Budget 128 & Budget 256 & Budget 512 \\ \midrule']
    md += ['', '### Packing stress across source budgets','', '| Model | Packer | Reader | Budget 128 | Budget 256 | Budget 512 |','|---|---|---|---:|---:|---:|']
    for (model,packer,reader),values in sorted(packed.items()):
        model='Pro' if 'pro' in model.lower() else 'Flash'
        cells=[f"{values[b]['exact_correct']}/{values[b]['successes']}" if b in values else '--' for b in (128,256,512)]
        labels=[model,packer.replace('_',' '),reader.replace('_',' ')]
        tex.append(' & '.join([tex_escape(x) for x in labels]+cells)+r' \\')
        md.append('| '+' | '.join(labels+cells)+' |')
    tex += [r'\bottomrule\end{tabular}\caption{Packing-stress outcomes across source budgets. Cells show exact-correct/completed on the same registered stress tasks; budgets do not create independent task samples.}\end{table}']
    tex += [r'\section{Uncertainty and Reproducibility}',tex_escape('Primary comparisons use repeat-zero shared tasks. Repeated answers never inflate task counts. Task bootstrap intervals, exact paired binomial diagnostics and Holm family adjustments are reported as descriptive diagnostics. Shared generators, task families and external conversations leave independence assumptions unverified; no significance or generalization claim is granted.')]
    tex += [r'\begin{table}[ht]\centering\footnotesize\begin{tabular}{p{0.46\linewidth}lrrl}\toprule',r'Contrast and condition & Model & Paired & $\Delta$ pp & Descriptive interval \\ \midrule']
    md += ['', '### Selected matched contrasts','', '| Contrast and condition | Model | Paired tasks | Difference (pp) | Descriptive interval (pp) |','|---|---|---:|---:|---|']
    for c in analysis.get('contrasts',[]):
        condition=c['condition'];family=c['family'];cohort=condition.get('cohort');budget=condition.get('budget');phase=condition.get('phase')
        keep=(family=='reader' and phase=='mechanism' and condition.get('policy')=='versioned' and budget==256 or
              family=='conflict_selection' and phase=='mechanism' and condition.get('reader')=='conflict_aware' and budget==256 or
              family=='retrieval' and cohort=='external_matched' and c['metric']=='external_judge_proxy' or
              family=='packing' and condition.get('reader')=='baseline' or
              family=='budget' and cohort=='synthetic_controlled' and condition.get('policy')=='versioned')
        if not keep or not c['n_paired']:continue
        label=(str(c['left'])+' vs '+str(c['right'])).replace('_',' ')
        scope='external judge' if c['metric']=='external_judge_proxy' else 'exact'
        label+=f" ({scope}, "+(f"B{budget}" if budget else 'source budgets')+')'
        model='Pro' if 'pro' in condition.get('model','').lower() else 'Flash'
        delta=f"{100*c['difference_left_minus_right']:+.1f}"
        interval=c.get('descriptive_task_bootstrap_95');interval_text='--' if interval is None else f'[{100*interval[0]:+.1f}, {100*interval[1]:+.1f}]'
        tex.append(' & '.join([tex_escape(label),model,str(c['n_paired']),delta,interval_text])+r' \\')
        md.append(f"| {label} | {model} | {c['n_paired']} | {delta} | {interval_text} |")
    tex += [r'\bottomrule\end{tabular}\caption{Descriptive paired differences, left minus right, in percentage points. Rows follow fixed condition rules rather than effect size. Task-bootstrap intervals do not establish population coverage or equivalence; full contrasts, task hashes, exclusions and multiplicity diagnostics are in the analysis artifact.}\end{table}']
    for name in ('discussion','conclusion'):
        tex += [r'\section{'+name.title()+'}',_tex_prose(sections[name],keys)];md += ['', '## '+name.title(),'',sections[name]]
    limits=' '.join(summary['limitations'])+' Semantic judgments by a DeepSeek model may favor related-model answers. The compact quantized encoder is a resource-constrained baseline, not a frontier retriever; stronger embeddings, rerankers and external context-budget sweeps remain untested. The bitemporal selector is assessed on explicit structured records; raw external passage retrieval does not establish successful free-text bitemporal extraction. Audited operational repairs handled Unicode JSONL boundaries and literal reserved-token spellings in source text, with original responses and measured usage retained. Previously accepted source text keeps the same tokenization; newly supported reserved spellings are encoded as ordinary text. Local CPU embedding and API usage are separate resource scopes. Scientific novelty and reviewer acceptance remain unestablished.'
    tex += [r'\section{Limitations}',tex_escape(limits),r'\begin{thebibliography}{99}'];md += ['', '## Limitations','',limits,'','## References']
    for ref in refs:
        authors=ref.get('authors','Authors');authors='; '.join(authors) if isinstance(authors,list) else str(authors)
        year=ref.get('year','n.d.');title=ref['title'];url=ref['url']
        author_label=authors.split(';')[0].split(' et al.')[0].split()[-1]+' et al.'
        tex.append(r'\bibitem['+tex_escape(author_label)+f'({year})'+']{'+ref['key']+'} '+tex_escape(f'{authors} ({year}). {title}. ')+r'\url{'+url+'}.')
        md.append(f"[{ref['key']}] {authors} ({year}). {title}. {url}")
    tex += [r'\end{thebibliography}',r'\end{document}']
    (output/'paper.tex').write_text('\n'.join(tex)+'\n',encoding='utf-8');(output/'paper.md').write_text('\n'.join(md)+'\n',encoding='utf-8')


def reconcile_experiment(run,summary):
    """Require quiescent, merged, fully accounted experiment evidence before spending."""
    from research.jsonl_ledger import read_jsonl
    from research.model_gateway import valid_usage
    from research.spend_reservation import load_reserves
    run=Path(run);state=json.loads((run/'run_state.json').read_text(encoding='utf-8'))
    if state.get('status') not in ('complete','stopped') or state.get('active_workers',0):
        raise ValueError('Experiment must stop and merge before writing')
    requests=read_jsonl(run/'requests.jsonl');calls=read_jsonl(run/'calls.jsonl')
    req={r['id']:r for r in requests};responses={c['id']:c for c in calls}
    if len(req)!=len(requests) or len(responses)!=len(calls) or set(req)!=set(responses):
        raise ValueError('Experiment request/response reconciliation failed')
    reserves=load_reserves(run,requests,calls)
    if any(not valid_usage(c.get('usage')) and c['id'] not in reserves for c in calls):raise ValueError('Unknown experiment usage without explicit hold')
    for directory in [run,*sorted(p for s in run.glob('segments*') if s.is_dir() for p in s.iterdir() if p.is_dir())]:
        if any(e.get('spend_uncertain') for e in read_jsonl(directory/'invocation_errors.jsonl')):
            raise ValueError('Uncertain invocation spend')
        if directory==run:continue
        for name,merged in [('requests.jsonl',req),('calls.jsonl',responses)]:
            for row in read_jsonl(directory/name):
                if row['id'] not in merged or row!=merged[row['id']]:raise ValueError('Unmerged or conflicting worker ledger')
    known=sum(c['usage']['total_tokens'] for c in calls if valid_usage(c.get('usage')))
    if known!=summary['resources']['total_tokens'] or len(req)!=summary['resources']['total_calls']:
        raise ValueError('Stale experiment resource summary')
    if len(read_jsonl(run/'results.jsonl'))!=summary['completed']:raise ValueError('Stale experiment result summary')
    return known+sum(reserves.values())


def verify_analysis_sources(run,analysis):
    expected={'grid.json','dataset.json','results.jsonl','judgments.jsonl','calls.jsonl'}
    if set(analysis.get('source_hashes',{}))!=expected:raise ValueError('Analysis source identity is incomplete')
    for name,value in analysis['source_hashes'].items():
        if file_digest(Path(run)/name)!=value:raise ValueError('Analysis describes stale source: '+name)


async def write_manuscript(run,config_dir=None):
    from baseline.runtime import read_model_config
    from research.proxy_tokenizer import token_count
    from research.agent_invocation import invoke_agent
    run=Path(run);output=run/'paper';output.mkdir(exist_ok=True)
    summary=json.loads((run/'summary.json').read_text(encoding='utf-8'));protocol=json.loads((run/'protocol.json').read_text(encoding='utf-8'))
    if summary['resources'].get('unreserved_unknown_usage_calls',summary['resources']['unknown_usage_calls']) or summary['resources'].get('pending_request_ids'):raise ValueError('Reconcile or explicitly hold all experiment usage before writing')
    remaining=protocol['token_limit']-reconcile_experiment(run,summary)
    if remaining<10000:raise ValueError('No safe writing allowance remains')
    analysis=json.loads((run/'analysis.json').read_text(encoding='utf-8'))
    verify_analysis_sources(run,analysis)
    evidence_sources={name:file_digest(run/name) for name in ('summary.json','analysis.json')}
    def check_stable_evidence():
        if any(file_digest(run/name)!=value for name,value in evidence_sources.items()):raise ValueError('Evidence changed during writing; no mixed-version manuscript')
    root=Path(__file__).resolve().parents[1];refs=load_references(root);keys={r['key'] for r in refs}
    evidence=compact_evidence(summary,analysis);save_json(output/'evidence_snapshot.json',evidence);save_json(output/'references.json',refs)
    config=read_model_config(config_dir);config['model']=protocol['models'][-1]
    gateway=ModelGateway(config,run/'writing_ledger',max_total_tokens=min(250000,remaining),max_calls=40,wall_seconds=3600,count_tokens=token_count)
    async def ask(messages,tag,cap):
        check_stable_evidence()
        async def transport(record):return await invoke_agent(dict(gateway.config),messages,cap,record)
        return await gateway.call(messages,tag,cap,invoke=transport)
    sections={};sourcekey=digest({'evidence':evidence,'refs':refs})
    instructions={
        'methods':'Explain frozen-data evaluation, pretrained local semantic retrieval, RRF, bitemporal atomic groups, additive-surrogate dynamic packing, exact-message Rail, baseline/conflict-aware/reflection readers and cost scopes. Do not call temporal modeling or these established components novel.',
        'related_work':'Position against the supplied verified temporal, memory, conflict-aware retrieval, memory-orchestration and benchmark sources. Distinguish implemented dense/RRF components from author frameworks not reproduced. Do not claim comparison to named frameworks without implemented evaluations.',
        'introduction':'Develop the research question and modest reusable engineering contribution. Explain why evidence selection and correct conflict interpretation require separate evaluation.',
        'discussion':'Interpret observed paired outcomes conservatively, including negative/tied packers, costs, incomplete conditions, model/seed stability, real-dialogue transfer and remaining gaps. Do not infer causality from error partitions.',
        'conclusion':'State precisely supported outcomes and remaining limitations; no SOTA, significance or reviewer-score prediction.',
        'abstract':'Summarize problem, implementation and actually observed qualitative evidence. Clearly disclose any incomplete matrix and adapted external judge.'}
    try:
        save_json(output/'writing_status.json',{'status':'running','review_score':None})
        for section in SECTIONS:
            messages=[{'role':'system','content':'Write one English scientific manuscript section as flowing paragraphs, about two hundred words. Return JSON exactly {"text":"..."}. NO digits, numeric words expressing measured sample sizes, percentages, URLs or measured numeric claims: measured facts are inserted by code. Method names BM25, cl100k_base and Mem0 are allowed. Refer to models as Flash and Pro. Citations use only supplied [key] references. Be faithful to evidence. answer_conditions_complete distinguishes a finished answer matrix from unresolved historical billing; conservative holds are not actual usage. Do not imply complete experiments when incomplete, novel established mechanisms, official benchmark scores, proven significance or inherited review scores.'},
                      {'role':'user','content':json.dumps({'section':section,'instructions':instructions[section],'evidence':evidence,'references':[{'key':r['key'],'title':r['title'],'finding':r.get('finding',r.get('relevance',''))} for r in refs]},ensure_ascii=False)}]
            response=await ask(messages,f'chapter/{sourcekey}/{section}',1300)
            for attempt in range(2):
                try:text=parse_json_object(response['output'])['text']
                except (ValueError,TypeError,KeyError):text=''
                candidate={k:text if k==section else 'Pending prose.' for k in SECTIONS};issues=check_sections(candidate,keys)
                if not issues:break
                if attempt:raise ValueError('Chapter failed bounded prose checks: '+section)
                response=await ask([*messages,{'role':'assistant','content':response['output']},{'role':'user','content':'Correct these mechanical violations and return the same JSON schema: '+json.dumps(issues)}],f'chapter/{sourcekey}/{section}/revise',1300)
            sections[section]=text;save_json(output/'model_sections.json',sections)
        implementation=evidence['implementation_contract']
        evidence={**evidence,'implementation_contract':implementation}
        save_json(output/'implementation_evidence.json',{'contract':implementation,'source_hashes':{name:file_digest(root/name) for name in ('research/advanced_retrieval.py','research/upgrade_protocol.py','research/review_upgrade.py','research/agent_invocation.py')}})
        gateway.config={**config,'model':protocol['models'][0]}
        review=await ask([{'role':'system','content':'Audit the English manuscript against supplied measured evidence and authoritative implementation_contract. Return ONLY a compact JSON object {"issues":[{"section":"one of methods, related_work, introduction, discussion, conclusion, abstract","severity":"material","suggestion":"source-backed correction in at most eighty words"}]}. Return at most TWO issues, combine all errors within a chapter. Prioritize factual mechanism errors and unsupported result claims. No long source quotations, minor stylistic issues, score or official-score prediction.'},
                          {'role':'user','content':json.dumps({'sections':sections,'evidence':evidence},ensure_ascii=False)}],f'critique/{sourcekey}',1500)
        (output/'internal_review.txt').write_text(review['output'],encoding='utf-8')
        try:critique=parse_json_object(review['output'])
        except ValueError:raise ValueError('Critique was not complete valid JSON; no manuscript export permitted')
        save_json(output/'internal_review.json',critique)
        revisions=[];changed=set();gateway.config={**config,'model':protocol['models'][-1]}
        for issue in critique.get('issues',[]) if isinstance(critique,dict) else []:
            if not isinstance(issue,dict) or issue.get('severity')!='material' or issue.get('section') not in SECTIONS:continue
            name=issue['section']
            if name in changed or len(changed)>=2:continue
            correction=await ask([{'role':'system','content':'Revise one English scientific section against measured evidence and the critique. Return JSON {"text":"..."}. No digits, percentages, URLs, numeric measured claims, unsupported novelty or significance. Use supplied citation keys only. Preserve limitations and incomplete-run disclosure.'},
                                  {'role':'user','content':json.dumps({'section':name,'previous':sections[name],'critique':issue,'evidence':evidence,'citation_keys':sorted(keys)},ensure_ascii=False)}],f'review-revision/{sourcekey}/{name}',1300)
            try:revised=parse_json_object(correction['output'])['text']
            except (ValueError,KeyError,TypeError):revised=''
            candidate={**sections,name:revised};issues=check_sections(candidate,keys)
            record={'section':name,'previous':sections[name],'candidate':revised,'review_issue':issue,'source_summary_sha256':file_digest(run/'summary.json'),'mechanical_issues':issues,'applied':not bool(issues)}
            revisions.append(record);changed.add(name)
            if not issues:sections[name]=revised
        save_json(output/'review_revisions.json',revisions);save_json(output/'reviewed_sections.json',sections)
        check_stable_evidence()
        _figures(run,output);render(sections,summary,analysis,protocol,refs,output)
        shutil.copy2(root/'output/paper/iclr2026_conference.sty',output/'iclr2026_conference.sty')
        compiler=shutil.which('pdflatex')
        if not compiler:raise ValueError('pdflatex unavailable; sources retained')
        logs=[]
        for _ in range(2):
            result=subprocess.run([compiler,'-interaction=nonstopmode','-halt-on-error','-no-shell-escape','-disable-installer','paper.tex'],cwd=output,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
            logs.append(result.stdout+result.stderr);(output/'compile.log').write_text('\n'.join(logs),encoding='utf-8')
            if result.returncode:raise ValueError('New-paper compilation failed; diagnostics retained')
        save_json(output/'writing_status.json',{'status':'succeeded','review_score':None,'source_summary_sha256':file_digest(run/'summary.json'),'source_analysis_sha256':file_digest(run/'analysis.json'),'paper_sha256':file_digest(output/'paper.pdf'),'review_scope':'Mechanical checks plus unscored model critique; scientific claims still require review.'})
    except Exception as error:
        save_json(output/'writing_status.json',{'status':'failed','error':str(error),'review_score':None});raise
    finally:
        totals=gateway.totals()
        save_json(run/'resources_all_stages.json',{'experiment':summary['resources'],'writing':totals,'known_total_tokens':summary['resources']['total_tokens']+totals['known_api_tokens'],
                                                  'admission_total_tokens':summary['resources']['total_tokens']+totals['known_api_tokens']+summary['resources'].get('reserved_unknown_tokens',0),
                                                  'token_limit':protocol['token_limit'],'currency_cost':None,'scope':'Recorded runtime APIs; excludes local embeddings, coding assistant, browser and whole-machine energy.'})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',default='output/review_upgrade_20261106');parser.add_argument('--config-dir')
    args=parser.parse_args();asyncio.run(write_manuscript(args.run_dir,args.config_dir))


if __name__=='__main__':main()
