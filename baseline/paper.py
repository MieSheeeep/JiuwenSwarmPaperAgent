"""Generate an evidence-bound English draft using the configured model."""
import argparse
import asyncio
import json
from pathlib import Path
import re
import shutil

from baseline.runtime import ModelRuntime, read_model_config

REFERENCES = [
    {'key':'liu2023','title':'Lost in the Middle: How Language Models Use Long Contexts',
     'authors':'Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, and Percy Liang',
     'year':2023,'url':'https://arxiv.org/abs/2307.03172',
     'finding':'The authors evaluate multi-document question answering and key-value retrieval and report sensitivity to relevant-information position.'},
    {'key':'packer2023','title':'MemGPT: Towards LLMs as Operating Systems',
     'authors':'Charles Packer, Sarah Wooders, Kevin Lin, Vivian Fang, Shishir G. Patil, Ion Stoica, and Joseph E. Gonzalez',
     'year':2023,'url':'https://arxiv.org/abs/2310.08560',
     'finding':'The authors introduce virtual context management inspired by hierarchical memory and evaluate document analysis and multi-session chat.'},
    {'key':'yao2022','title':'ReAct: Synergizing Reasoning and Acting in Language Models',
     'authors':'Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, and Yuan Cao',
     'year':2022,'url':'https://arxiv.org/abs/2210.03629',
     'finding':'The authors interleave reasoning and actions on language and interactive tasks. This pilot uses the framework ReActAgent class but disables tools and does not evaluate action planning.'},
]
SECTIONS = ['abstract','introduction','related_work','methods','discussion','conclusion']


def tex_escape(text):
    mapping={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$',
             '#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    return ''.join(mapping.get(c,c) for c in text).replace('—','--').replace('–','--').replace('’',"'").replace('“','"').replace('”','"')


async def write(args):
    source=Path(args.results); out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    result=json.loads((source/'summary.json').read_text(encoding='utf-8'))
    outline={
        'abstract':'Scope, paired comparison, observed scores, and explicitly synthetic-pilot conclusion.',
        'introduction':'Question: which history policy preserves configuration state while reducing API tokens?',
        'related_work':'Position sensitivity, virtual context management, and ReAct; use only the provided verified references.',
        'methods':'24 deterministic synthetic histories, 60 records, 8 tasks in each family, early/middle/late placements, field-wise overwrites; lexical retrieval, proxy budgets, isolated sessions, paired scoring, all-call token accounting.',
        'discussion':'Explain recent-window failures by omitted evidence; no accuracy gain from extra summaries; easy identifier matching favors retrieval; no novelty, equivalence, real-world agent, or long-context robustness claim.',
        'conclusion':'Reusable opt-in JiuwenSwarm rail and verified experiment pipeline, requiring broader evaluation before research claims.'}
    (out/'outline.json').write_text(json.dumps(outline,indent=2),encoding='utf-8')
    (out/'references.json').write_text(json.dumps(REFERENCES,indent=2),encoding='utf-8')
    evidence={'results':result,'outline':outline,'references':REFERENCES,
              'execution':'openJiuwen ReActAgent with a new opt-in rail located in JiuwenSwarm source, not the GUI app or full Swarm assembler. No tools. History selection is applied in before_invoke, actual calls captured in after_model_call.',
              'chronology':'The agent processes a supplied static history in a single answering call; these are not observed multi-turn interactions.',
              'sampling':'Synthetic fixed-seed convenience sample, no training or task-specific tuning on model outputs. One run per case. 9 early, 9 middle, 6 late cases.',
              'publication_status':'Local baseline draft; not submitted to ICLR and not peer reviewed.'}
    (out/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    sections_path=out/'model_sections.json'
    if not sections_path.exists():
        runtime=ModelRuntime(read_model_config(args.config_dir),out)
        text=await runtime.model_call([
            {'role':'system','content':'Write a cautious scientific baseline draft in English using only the evidence supplied. '
             'Return valid JSON with exactly six string keys: abstract, introduction, related_work, methods, discussion, conclusion. '
             'Each value is flowing prose, not a list. Total 850-1100 words. '
             'Use author-year textual citations only from the reference list. Do not invent datasets, experiments, references, or novelty. '
             'Say local synthetic pilot, not benchmark validation. Do not call 100% accuracy equivalence. '
             'Do not claim full-history failed. Summaries here are applied after retrieval, not over full history. '
             'Mention tokenizer proxy and unbounded reference, same model and isolated sessions, summary costs included. '
             'Do not describe nominal confidence intervals as guarantees.'},
            {'role':'user','content':json.dumps(evidence,ensure_ascii=False)}
        ],'paper/draft',2400)
        (out/'raw_model_response.txt').write_text(text,encoding='utf-8')
        clean=re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip())
        sections=json.loads(clean)
        if set(sections)!=set(SECTIONS) or not all(isinstance(v,str) and v.strip() for v in sections.values()):
            raise ValueError('Model did not return the required draft sections')
        sections_path.write_text(json.dumps(sections,indent=2),encoding='utf-8')
    reviewed_path=out/'reviewed_sections.json'
    sections=json.loads((reviewed_path if reviewed_path.exists() else sections_path).read_text(encoding='utf-8'))
    methods=result['methods']
    title='Context Selection for Configuration History: A Reproducible JiuwenSwarm Pilot'
    markdown=[f'# {title}','', '**Local baseline draft; not submitted or peer reviewed.**','']
    for key in SECTIONS:
        markdown.extend([f'## {key.replace("_"," ").title()}','',sections[key],''])
        if key=='methods':
            markdown.extend(['## Measured results','',(source/'RESULTS.md').read_text(encoding='utf-8'),''])
    markdown.extend(['## References','']+[f'{r["authors"]} ({r["year"]}). {r["title"]}. {r["url"]}' for r in REFERENCES])
    markdown.extend(['','## Generation disclosure','',
                     'Research question, generator, policies, execution, and scoring were implemented with Codex assistance. '
                     'DeepSeek generated compressed contexts and the initial prose from a fixed evidence bundle; '
                     'the authoring script inserts measured tables and verified reference metadata. '
                     'Literature metadata and the final draft were checked by the coding assistant; no independent human review has occurred.'])
    (out/'paper.md').write_text('\n'.join(markdown),encoding='utf-8')
    table_rows=[]
    names={'full':'Full history','recent':'Recent window','retrieve':'Project retrieval','retrieve_summary':'Retrieval + summary'}
    for s in methods:
        lo,hi=s['wilson_95']
        table_rows.append(f'{names[s["policy"]]} & {s["correct"]}/{s["tasks"]} & '
                          f'{100*s["exact_accuracy"]:.1f} & [{100*lo:.1f}, {100*hi:.1f}] & '
                          f'{s["mean_tokens_per_task"]:.1f} & {s["mean_seconds_per_task"]:.2f} '+r'\\')
    tex=[r'\documentclass{article}',r'\usepackage{iclr2026_conference,times}',
         r'\usepackage{graphicx,booktabs,hyperref}',r'\iclrfinalcopy',
         r'\author{Local baseline project\\AI-assisted draft; not peer reviewed}',
         r'\title{'+tex_escape(title)+'}',
         r'\begin{document}',r'\maketitle',r'\fancyhead[L]{Local baseline draft -- not submitted}',
         r'\begin{abstract}',tex_escape(sections['abstract']),r'\end{abstract}']
    for key in SECTIONS[1:]:
        tex.extend([r'\section{'+key.replace('_',' ').title()+'}',tex_escape(sections[key])])
        if key=='methods':
            tex.extend([r'\section{Measured Results}',
                'Table~1 reports the saved paired run. Confidence intervals are descriptive Wilson intervals on a synthetic convenience sample. They do not establish generalization or equivalence.',
                'All '+str(result['total_api_calls'])+' experiment API calls succeeded, using '+str(result['total_api_tokens'])+
                ' API-reported tokens. Draft-writing and smoke-test usage are separately logged and excluded from the experiment table.',
                r'\begin{table}[ht]\centering\small',r'\begin{tabular}{lrrrrr}\toprule',
                r'Method & Correct & Acc. (\%) & 95\% CI & Tokens/task & Sec./task \\ \midrule',
                *table_rows,r'\bottomrule\end{tabular}',
                r'\caption{Measured results. Tokens include input, output, and summary overhead. Full history is an unbounded reference.}\end{table}',
                r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{results_figure.pdf}',
                r'\caption{Exact-match accuracy with descriptive Wilson intervals, and API tokens per task.}\end{figure}'])
    tex.extend([r'\section{Generation and Reproducibility Disclosure}',
        tex_escape('Codex assisted with question selection, code, dataset generation, execution, and draft review. DeepSeek produced compressed contexts and the initial manuscript prose from the saved evidence bundle. Measured tables are inserted programmatically. No independent human review or Stanford Agentic Reviewer assessment has been performed. The new rail is loaded directly from the JiuwenSwarm source checkout and registered on openJiuwen ReActAgent; the full JiuwenSwarm GUI/Swarm assembly is not part of this experiment. Source patch, generator, logs, and reproduction commands accompany this draft.'),
        r'\begin{thebibliography}{9}'])
    for r in REFERENCES:
        short={'liu2023':'Liu et al.','packer2023':'Packer et al.','yao2022':'Yao et al.'}[r['key']]
        tex.append(r'\bibitem['+short+'('+str(r['year'])+')]{'+r['key']+'} '+tex_escape(r['authors'])+'. '+tex_escape(r['title'])+'. '+str(r['year'])+'. '+r'\url{'+r['url']+'}.')
    tex.extend([r'\end{thebibliography}',r'\end{document}'])
    (out/'paper.tex').write_text('\n'.join(tex),encoding='utf-8')
    shutil.copy2(source/'results_figure.pdf',out/'results_figure.pdf')
    print('Draft sections and ICLR-template source saved.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',default='output/baseline')
    parser.add_argument('--output',default='output/paper');parser.add_argument('--config-dir')
    asyncio.run(write(parser.parse_args()))
