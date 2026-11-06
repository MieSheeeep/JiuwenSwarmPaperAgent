"""Evidence-first prose, measured tables and a reproducible LaTeX manuscript."""
import asyncio
import json
from pathlib import Path
import re
import shutil

from research.artifacts import create_artifact, digest, file_digest, save_json, validate_artifact
from research.memory_analysis import analyze_memory
from research.model_gateway import ModelGateway, read_jsonl

SECTIONS = ('methods', 'related_work', 'introduction', 'discussion', 'conclusion', 'abstract')
TITLE = 'Budgeted Bitemporal Source Memory in JiuwenSwarm: A Controlled Study'
REFERENCES = [
    {'key':'temporal', 'authors':'Christian S. Jensen et al.', 'year':1994,
     'title':'A Consensus Glossary of Temporal Database Concepts',
     'url':'https://www2.cs.arizona.edu/~rts/pubs/SIGMODRecordMarch94p52.pdf',
     'finding':'Valid time and transaction time are established temporal database concepts; this study does not invent bitemporal modeling.'},
    {'key':'memgpt', 'authors':'Charles Packer et al.', 'year':2023,
     'title':'MemGPT: Towards LLMs as Operating Systems', 'url':'https://arxiv.org/abs/2310.08560',
     'finding':'MemGPT studies virtual context management with hierarchical memory. It is related work, not an implemented baseline here.'},
    {'key':'memzero', 'authors':'Prateek Chhikara et al.', 'year':2025,
     'title':'Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory', 'url':'https://arxiv.org/abs/2504.19413',
     'finding':'Mem0 extracts, consolidates and retrieves memories and studies a graph extension on LOCOMO; this structured study does not reproduce it.'},
    {'key':'amem', 'authors':'Wujiang Xu et al.', 'year':2025,
     'title':'A-MEM: Agentic Memory for LLM Agents', 'url':'https://arxiv.org/abs/2502.12110',
     'finding':'A-MEM dynamically links structured notes and evolves memory representations; no comparison to its implementation is claimed.'},
    {'key':'longmemeval', 'authors':'Di Wu et al.', 'year':2024,
     'title':'LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory', 'url':'https://arxiv.org/abs/2410.10813',
     'finding':'LongMemEval evaluates long-term interactive memory; it is a needed future external validation, not evaluated here.'},
    {'key':'agentlab', 'authors':'Samuel Schmidgall et al.', 'year':2025,
     'title':'Agent Laboratory: Using LLM Agents as Research Assistants', 'url':'https://arxiv.org/abs/2501.04227',
     'finding':'Agent Laboratory stages literature review, experimentation and report writing. This system borrows workflow design ideas, not source code.'},
    {'key':'airesearcher', 'authors':'Jiabin Tang et al.', 'year':2025,
     'title':'AI-Researcher: Autonomous Scientific Innovation', 'url':'https://arxiv.org/abs/2505.18705',
     'finding':'AI-Researcher orchestrates scientific investigation and manuscript preparation; its research/writing boundary informs our design.'},
]


def measured_rows(summary, budget):
    return [r for r in summary['methods'] if r['split'] == 'test' and r['budget'] == budget]


def check_prose(prose):
    if not isinstance(prose, dict) or set(prose) != set(SECTIONS):
        return ['Missing or unexpected sections']
    issues = []
    keys = {r['key'] for r in REFERENCES}
    for section, text in prose.items():
        if not isinstance(text, str) or not text.strip():
            issues.append(f'{section}: missing prose')
            continue
        without_names = re.sub(r'\b(?:Mem0|BM25|cl100k_base)\b', 'KnownMethod', text, flags=re.I)
        if re.search(r'\d|%', without_names):
            issues.append(f'{section}: numeric prose must use measured programmatic tables')
        cited = [key.strip() for group in re.findall(r'\[([^\]]+)\]',text) for key in re.split(r'[,;]',group)]
        if any(key not in keys for key in cited):
            issues.append(f'{section}: unverified citation')
        if re.search(r'we (?:achieve|demonstrate|obtain) (?:a )?(?:statistically significant|state.of.the.art)|we (?:propose|introduce) (?:a )?novel', text, re.I):
            issues.append(f'{section}: unsupported strength or novelty claim')
    return issues


def _artifact(path, kind, payload, parents=()):
    path = Path(path)
    if path.exists():
        existing = validate_artifact(json.loads(path.read_text(encoding='utf-8')), kind)
        if existing['payload'] == payload and existing['parent_ids'] == list(parents):
            return existing
    value = create_artifact(kind, payload, parents)
    save_json(path, value)
    return value


def capture_evidence(source, output):
    source, output = Path(source), Path(output)
    summary = analyze_memory(source)
    if not summary['evaluation_complete']:
        raise ValueError('Incomplete or uncertain experiment cannot be presented as a completed comparison')
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    snapshot = output / 'evidence_snapshot'
    snapshot.mkdir(parents=True, exist_ok=True)
    results = read_jsonl(source / 'results.jsonl')
    linked = {call_id for r in results for call_id in r['call_ids']}
    for name in ('dataset.json', 'manifest.json', 'results.jsonl'):
        shutil.copy2(source / name, snapshot / name)
    for name in ('calls.jsonl', 'requests.jsonl'):
        from research.artifacts import atomic_write
        selected = [row for row in read_jsonl(source / name) if row['id'] in linked]
        atomic_write(snapshot / name, ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in selected))
    # Reanalysis over an experiment-only snapshot remains stable after writing
    # calls append to the original end-to-end ledger.
    experiment_summary = analyze_memory(snapshot)
    source_files = {p.name: file_digest(p) for p in snapshot.glob('*.json*') if p.name not in ('summary.json',)}
    parents = []
    plan_path = source / 'experiment_plan.json'
    if plan_path.exists():
        parents = [validate_artifact(json.loads(plan_path.read_text(encoding='utf-8')))['artifact_id']]
    run = _artifact(output / 'run_artifact.json', 'RunManifest', {
        'origin': 'live_memory_experiment', 'source_files': source_files,
        'model_id': manifest['model'], 'task_count': len(json.loads((source/'dataset.json').read_text())),
        'policies': sorted({r['policy'] for r in manifest['grid']}), 'call_ids': sorted(linked),
        'code_revision': manifest['code_hashes'], 'condition_hash': digest(manifest),
        'source_directory': str(snapshot.resolve()),
    }, parents)
    payload = {'origin': 'live_memory_experiment', 'metrics': experiment_summary['methods'],
               'total_api_calls': experiment_summary['resources']['total_calls'],
               'total_api_tokens': experiment_summary['resources']['total_tokens'],
               'limitations': manifest['limitations'], 'resource_accounting': experiment_summary['resources'],
               'paired_comparisons': experiment_summary['paired_comparisons'],
               'metric_notes': experiment_summary['metric_notes'], 'manifest': manifest}
    brief_path = source / 'research_brief.json'
    if brief_path.exists():
        brief = validate_artifact(json.loads(brief_path.read_text(encoding='utf-8')), 'ResearchBrief')
        if brief['payload'].get('discovery_manifest_sha256'):
            # Opt-in provenance only: historical evidence and prompts stay unchanged.
            payload['literature_research'] = {'brief': brief['payload'],
                'experiment_plan': validate_artifact(json.loads(plan_path.read_text(encoding='utf-8')), 'ExperimentPlan')['payload']}
    evidence = _artifact(output / 'evidence_artifact.json', 'EvidenceBundle', payload, [run['artifact_id']])
    return evidence, experiment_summary


async def draft_sections(gateway, evidence, output):
    output = Path(output)
    data = evidence['payload']
    compact = {'methods': [{k:r[k] for k in ('split','policy','budget','tasks','exact_correct','exact_accuracy',
               'micro_field_accuracy','stale_fields','actual_total_tokens')} for r in data['metrics']],
               'limitations': data['limitations'], 'model': data['manifest']['model'],
               'protocol': data['manifest']['scope'], 'references': REFERENCES}
    if 'literature_research' in data:
        compact['literature_research'] = data['literature_research']
    stable_key = digest(compact)
    outline = {
        'methods': 'Structured input schema, valid/observed cutoffs, maximal valid-time atomic conflict groups, budget packing. Baselines and ablations; no tools.',
        'related_work': 'Credit temporal database prior art; memory systems related but not reproduced; workflow ideas borrowed with source audit.',
        'introduction': 'Engineering question: retaining the source evidence needed under a fixed context budget; avoid unsubstantiated novelty.',
        'discussion': 'Explain observations and unresolved failure modes, structured-schema assumptions, lexical baselines, no real dialogue or embedding baseline.',
        'conclusion': 'Reusable opt-in framework extension and reproducible controlled evidence; external validation needed.',
        'abstract': 'Problem, engineering method, empirical qualitative outcome and explicit controlled-study limit.',
    }
    save_json(output / 'outline.json', outline)
    save_json(output / 'references.json', REFERENCES)
    draft_prompt = [
        {'role':'system','content':'Write a cautious English scientific manuscript as JSON with exactly these six '
         'string keys: methods, related_work, introduction, discussion, conclusion, abstract. Work in that order. '
         'Full flowing paragraphs, about eleven hundred words total. NO digits, percentages, URLs or numeric '
         'claims anywhere: measured results and protocol numbers are inserted by code afterward. Refer to the '
         'measured results qualitatively and conditionally. Citations only as [temporal], [memgpt], [memzero], '
         '[amem], [longmemeval], [agentlab], [airesearcher]. Do not invent references. '
         'Bitemporal modeling and per-attribute version filtering are established; our contribution is a '
         'reusable opt-in JiuwenSwarm source-evidence Rail and controlled, logged evaluation. No novelty or '
         'SOTA claim. No Mem0/A-MEM reproduction, no real dialogue benchmark, no semantic embedding baseline. '
         'The ReActAgent has no tools and a single answering call. Summary overhead is included. '
         'Evidence availability is not model citation faithfulness. Do not mention external review scores.'},
        {'role':'user','content':json.dumps({'evidence':compact,'outline':outline}, ensure_ascii=False)},
    ]
    row = await gateway.call(draft_prompt, f'paper/draft/{stable_key}', 3600)
    (output / 'raw_model_response.txt').write_text(row['output'], encoding='utf-8')
    try:
        prose = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', row['output'].strip()))
    except ValueError:
        prose = {}
    save_json(output / 'model_sections.json', prose)
    issues = check_prose(prose)
    if issues:
        revision = await gateway.call(draft_prompt + [
            {'role':'assistant','content':row['output']},
            {'role':'user','content':'Revise the JSON once to fix these mechanical violations. No numeric prose: '+json.dumps(issues)},
        ], f'paper/revise/{stable_key}', 3600)
        try:
            prose = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', revision['output'].strip()))
        except ValueError:
            prose = {}
        issues = check_prose(prose)
    if issues:
        save_json(output / 'writing_status.json', {'status':'failed','issues':issues})
        raise ValueError('Model prose failed bounded numeric/citation checks; raw outputs retained')
    save_json(output / 'reviewed_sections.json', prose)
    critique = await gateway.call([
        {'role':'system','content':'Review the manuscript against the evidence. Return short plain text with '
         'specific weaknesses and missing evidence. Do not assign any score and do not claim official '
         'Stanford review. Distinguish engineering utility from scientific novelty. Do not invent results.'},
        {'role':'user','content':json.dumps({'evidence':compact,'prose':prose}, ensure_ascii=False)},
    ], f'paper/internal_critique/{stable_key}', 1100)
    save_json(output / 'internal_review.json', {'type':'internal_model_critique', 'call_id':critique['id'],
              'text':critique['output'], 'official_stanford_score':None,'official_paper_agent_score':None})
    reviewed = factual_review(prose)
    if check_prose(reviewed):
        raise ValueError('Source-code factual review violates prose checks')
    save_json(output/'factual_review_notes.json', {'reviewer':'coding_assistant_source_and_evidence_review',
        'model_prose_sha256':digest(prose), 'reviewed_prose_sha256':digest(reviewed),
        'corrections':['point timestamps, not valid-time intervals',
                       'no-conflict resolves equal-time ties by observed order; it does not drop all conflicts',
                       'summary compresses retrieved records, not dropped records',
                       'selected-context budget and total API usage are different quantities',
                       'no asserted conflict-handling accuracy benefit when ablation ties'],
        'heldout_method_tuning':False})
    save_json(output/'reviewed_sections.json',reviewed)
    return reviewed


def tex_escape(text):
    replacements = {'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$', '#':r'\#',
                    '_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    return ''.join(replacements.get(c,c) for c in str(text)).replace('—','--').replace('–','--').replace('’',"'")


def tex_prose(text):
    parts = re.split(r'(\[[a-z_,;\s]+\])', text)
    return ''.join(r'\citep{'+','.join(k.strip() for k in re.split(r'[,;]',p[1:-1]))+'}'
                   if re.fullmatch(r'\[[a-z_,;\s]+\]',p) else tex_escape(p) for p in parts)


def factual_review(prose):
    """Authoritative source-code review overrides hallucinated mechanism prose.

    Preserve generated prose separately. These paragraphs describe the frozen
    implementation, not an interpretation inferred from method names.
    """
    reviewed = dict(prose)
    reviewed['introduction'] = (
        'An agent reading an evolving record stream must distinguish when a fact applies from when the '
        'system learned it. Late observations of old facts, unresolved contradictions and deletions can '
        'make naive context selection misleading even when lexical matching succeeds. A restricted context '
        'window adds a second problem: evidence about different requested attributes competes for space. '
        'We study that engineering problem with explicit structured records and a fixed answering model.\n\n'
        'Our contribution is an opt-in JiuwenSwarm source-memory Rail, an append-only record interface and '
        'a reproducible evaluation with persisted responses and resource accounting. Bitemporal modeling '
        'is established prior art [temporal]; neither its invention nor general superiority over memory '
        'systems is claimed. The selectors return original source records, never resolved reference answers. '
        'The evaluation includes lexical methods, a full-context reference, and time/conflict ablations. '
        'All bounded methods share a selected-source-context limit; total API cost is measured separately. '
        'The structured input assumption deliberately excludes free-text extraction and is a major limit '
        'on deployment claims. LongMemEval illustrates the broader interactive setting that still requires '
        'external validation [longmemeval].')
    reviewed['methods'] = (
        'Each source record contains a unique local identifier, an entity, a single attribute, a scalar '
        'value, an effective-time point named valid_at, an observation-time point named observed_at, and '
        'a set or delete operation. There are no validity intervals in this implementation. The append-only '
        'store preserves original records and supports JSONL round trips. Query metadata supplies the entity, '
        'requested attributes and both time cutoffs equally to every method. Visible records satisfy both '
        'cutoffs. For each requested attribute, the versioned selector retains the records at the maximal '
        'visible effective time. Different values or a set/delete disagreement at that time form an '
        'unresolved conflict. Such a group is atomic: it is retained together or omitted together. A '
        'tombstone is source evidence for deletion, not an inferred replacement value.\n\n'
        'Versioned selection packs smaller complete attribute groups first, breaking equal-cost ties in '
        'query order and restoring source order in the final context. Joined JSONL text is recounted after '
        'each addition. This greedy rule is not claimed optimal for arbitrary nonadditive tokenizers. The '
        'no-time ablation keeps the observation cutoff but orders and selects by observation time rather '
        'than effective time. The no-conflict ablation keeps both cutoffs and maximal effective time, then '
        'breaks ties by latest observation; it does not discard every conflicting record.\n\n'
        'Full history passes the unbounded source stream. Recent selection uses a contiguous suffix. '
        'Lexical overlap and BM25 rank serialized source records using the entity, requested attributes '
        'and question text. They receive the same metadata as the structured selectors but do not use '
        'temporal filtering in their ranking. Lexical-summary compresses the already retrieved lexical '
        'records, not discarded records, and truncates the summary to the same selected-context limit. '
        'Summary calls add to total API consumption; they do not make total call budgets equal.\n\n'
        'A fresh openJiuwen ReActAgent receives the selected context and the common query semantics. '
        'The Rail injects context before invocation and records the model response before later agent '
        'postprocessing. Requests are reserved durably before transport and reconciled to provider usage. '
        'Unknown spend blocks further calls. Answer accuracy requires the exact requested JSON keys and '
        'type-correct values. Micro-field accuracy pools correct fields. Stale-field counts compare '
        'nonnull returned values to superseded visible source values. Evidence recall measures reference '
        'record identifiers available in the selected source context, not model-provided citations. '
        'For summary methods it describes the retrieved source records and does not certify compression '
        'faithfulness. Metadata extraction requires no model call here because it is an input assumption.')
    reviewed['discussion'] = (
        'The measured tables describe a single fixed set of model responses, not a robust ranking across '
        'models or independent repeated samplings. In particular, the full-context reference is unbounded '
        'and must not be described as having the same total cost as a bounded method. Equal selected '
        'source-context limits isolate packing behavior; instruction tokens, answer tokens and additional '
        'summary calls remain visible in provider accounting. Differences in these costs are outcomes, '
        'not violations of the selected-context definition.\n\n'
        'The conflict ablation is important because preserving contradictory source records and correctly '
        'interpreting them are separate operations. If extra conflict evidence does not improve exact '
        'answers, the evidence-preservation mechanism has not established an accuracy benefit. It may '
        'still help auditing, but that utility is different from answer correctness. The source audit '
        'therefore records both evidence availability and errors instead of treating retrieval recall '
        'as a substitute for downstream evaluation.\n\n'
        'Several constraints prevent broad conclusions. The record schema and query metadata are given '
        'for free; clean temporal annotations would have an extraction cost and failure rate in deployment. '
        'The cases are synthetic and closely related within families, and there is only a small held-out '
        'sample. Descriptive intervals do not establish significance or external validity. BM25 is lexical; '
        'an embedding retriever is absent. No Mem0 or A-MEM implementation is reproduced [memzero, amem]. '
        'The answering agent has no tools or iterative action loop. Real-dialogue evaluation, direct '
        'citation faithfulness and independent repetitions remain necessary extensions [longmemeval].')
    reviewed['conclusion'] = (
        'This work delivers an opt-in bitemporal source-memory extension and a bounded, traceable '
        'evaluation workflow for JiuwenSwarm on openJiuwen. It tests engineering mechanisms under explicit '
        'structured-input assumptions and reports negative as well as positive observations. Established '
        'temporal semantics are credited [temporal]. Source preservation, model answer correctness and '
        'API cost are kept separate. The evidence supports a reproducible controlled study; it does not '
        'establish a new general memory algorithm or replace external benchmarks and official assessment.')
    reviewed['abstract'] = (
        'Selecting memory for an agent requires deciding which source records remain relevant under '
        'temporal updates and a restricted context window. We implement an opt-in JiuwenSwarm Rail that '
        'filters structured facts by effective and observation times, preserves maximal-time conflict '
        'groups atomically and packs original evidence under a selected-context budget. Bitemporal '
        'modeling is established prior art [temporal]; the contribution is a reusable framework extension '
        'and a traceable controlled evaluation. A fixed ReActAgent is compared across recency, lexical, '
        'BM25, summary, full-history and temporal/conflict ablation conditions. All bounded methods share '
        'a source-context limit, while total provider usage includes instructions, answers and summary '
        'calls. Measured outcomes are reported separately from evidence availability, including null '
        'ablation outcomes. The study uses synthetic records with explicit metadata, no tools and no '
        'free-text ingestion. It supplies reproducible engineering evidence rather than a claim of '
        'superiority over general long-term memory systems.')
    return reviewed


def draw_figures(summary, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    output = Path(output)
    fig, ax = plt.subplots(figsize=(9, 1.7))
    ax.set_xlim(0, 10); ax.set_ylim(0, 2); ax.axis('off')
    labels = ['Append-only\nsource records', 'Effective and\nobserved cutoffs', 'Atomic version /\nconflict groups', 'Joined-text\nbudget packing', 'ReActAgent\nanswer + usage']
    for i, label in enumerate(labels):
        x = .1 + i*2
        ax.add_patch(FancyBboxPatch((x,.55),1.7,.9,boxstyle='round,pad=.05',facecolor='#edf4fa',edgecolor='#346888'))
        ax.text(x+.85,1,label,ha='center',va='center',fontsize=9)
        if i<4:
            ax.annotate('',xy=(x+1.98,1),xytext=(x+1.76,1),arrowprops={'arrowstyle':'->','color':'#346888'})
    fig.savefig(output/'architecture.pdf',bbox_inches='tight'); plt.close(fig)
    rows = measured_rows(summary, 256)
    fig, axes = plt.subplots(1,2,figsize=(9,3.2))
    labels = [r['policy'] for r in rows]
    axes[0].bar(range(len(rows)),[100*r['exact_accuracy'] for r in rows],color='#3b7394')
    axes[0].set_ylabel('Exact accuracy (%)'); axes[0].set_ylim(0,105)
    axes[1].bar(range(len(rows)),[r['actual_total_tokens']/r['tasks'] for r in rows],color='#9b6645')
    axes[1].set_ylabel('Provider tokens per task')
    for ax in axes:
        ax.set_xticks(range(len(rows)),labels,rotation=48,ha='right',fontsize=8)
        ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(output/'results.pdf',bbox_inches='tight'); plt.close(fig)


def render_paper(prose, evidence, summary, output):
    output = Path(output)
    if check_prose(prose):
        raise ValueError('Cannot render unchecked prose')
    manifest = evidence['payload']['manifest']
    rows = measured_rows(summary, 256)
    sensitivity = measured_rows(summary, 512)
    md = ['# '+TITLE,'','**Controlled synthetic study; external evaluations pending.**','', '## Abstract','',prose['abstract'],'']
    tex = [r'\documentclass{article}',r'\usepackage{iclr2026_conference,times}',
           r'\usepackage{graphicx,booktabs,hyperref}',r'\hypersetup{hidelinks}',r'\iclrfinalcopy',
           r'\title{'+tex_escape(TITLE)+'}',r'\author{Anonymous Competition Research System}',
           r'\begin{document}',r'\maketitle',r'\fancyhead[L]{Controlled engineering study -- external evaluation pending}',
           r'\begin{abstract}',tex_prose(prose['abstract']),r'\end{abstract}',
           r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{architecture.pdf}',
           r'\caption{Source-evidence selection and invocation accounting. The memory layer returns original records, not gold answers.}\end{figure}']
    for section in ('introduction','related_work','methods'):
        md += ['## '+section.replace('_',' ').title(),'',prose[section],'']
        tex += [r'\section{'+section.replace('_',' ').title()+'}',tex_prose(prose[section])]
    protocol = ('The fixed protocol uses six development tasks and twenty-four held-out tasks, with disjoint seed namespaces '
                'and six task families. All methods receive identical structured records, query metadata and answering instructions. '
                'The primary selected-context budget is 256 cl100k_base proxy tokens. A 512-token sensitivity comparison uses '
                'twelve fixed held-out tasks; full history is an unbounded reference evaluated only in the primary grid. '
                'The frozen grid has '+str(len(manifest['grid']))+' task-policy-budget outcomes. Each answering session is isolated, '
                'uses temperature zero, disables thinking and tools, and allows 160 output tokens. Lexical summary allows an '
                'additional 256-token model output before truncation to the selected-context budget. API-reported usage, including '
                'summary overhead, is the cost measure; proxy context length is not provider billing. Retrieval ties and source '
                'ordering are deterministic. BM25 here is strictly lexical; no semantic embedding retriever is evaluated.')
    md += ['### Frozen protocol','',protocol,'']
    tex += [r'\subsection{Frozen Protocol}',tex_escape(protocol),r'\section{Measured Results}']
    md += ['## Measured results','', '| Policy | Correct / tasks | Exact | Field | API tokens |', '|---|---:|---:|---:|---:|']
    tex += [r'\begin{table}[ht]\centering\small',r'\begin{tabular}{lrrrr}\toprule',
            r'Policy & Correct & Exact (\%) & Field (\%) & Tokens \\ \midrule']
    for row in rows:
        md.append(f"| {row['policy']} | {row['exact_correct']}/{row['tasks']} | {row['exact_accuracy']:.1%} | {row['micro_field_accuracy']:.1%} | {row['actual_total_tokens']} |")
        tex.append(tex_escape(row['policy'])+f" & {row['exact_correct']}/{row['tasks']} & {100*row['exact_accuracy']:.1f} & {100*row['micro_field_accuracy']:.1f} & {row['actual_total_tokens']} "+r'\\')
    tex += [r'\bottomrule\end{tabular}',r'\caption{Held-out primary comparison. Full history is unbounded; other methods share the selected-context budget. Tokens include summary calls.}\end{table}',
            r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{results.pdf}',
            r'\caption{Primary held-out exact accuracy and provider tokens per task. Point estimates describe this controlled sample.}\end{figure}']
    md += ['', '### Budget sensitivity','', '| Policy | Correct / tasks | Exact |', '|---|---:|---:|']
    tex += [r'\begin{table}[ht]\centering\small',r'\begin{tabular}{lrr}\toprule',r'Policy & Correct & Exact (\%) \\ \midrule']
    for row in sensitivity:
        md.append(f"| {row['policy']} | {row['exact_correct']}/{row['tasks']} | {row['exact_accuracy']:.1%} |")
        tex.append(tex_escape(row['policy'])+f" & {row['exact_correct']}/{row['tasks']} & {100*row['exact_accuracy']:.1f} "+r'\\')
    tex += [r'\bottomrule\end{tabular}',r'\caption{Larger-budget sensitivity on the same fixed subset across bounded methods; this sample differs from the primary table.}\end{table}']
    main_map = {r['policy']:r for r in rows}
    if main_map['versioned']['exact_correct'] == main_map['no_conflict']['exact_correct']:
        observed = ('Versioned and no-conflict selection tie at '+str(main_map['versioned']['exact_correct'])+
                    '/'+str(main_map['versioned']['tasks'])+' exact answers. Thus this run provides no observed '
                    'accuracy gain from atomic conflict preservation. The versioned method retains all reference '
                    'source evidence at the primary budget but the model still makes errors; evidence sufficiency '
                    'does not guarantee correct conflict interpretation.')
        md += ['',observed,'']
        tex += [tex_escape(observed)]
    md += ['### Descriptive paired differences','',
           '| Versioned minus comparator | Tasks | Accuracy difference (pp) | Descriptive interval (pp) |',
           '|---|---:|---:|---:|']
    tex += [r'\begin{table}[ht]\centering\small',r'\begin{tabular}{lrrr}\toprule',
            r'Comparator & Tasks & Difference (pp) & Interval (pp) \\ \midrule']
    for pair in summary['paired_comparisons']:
        if pair['split']!='test' or pair['budget']!=256 or 'versioned' not in (pair['policy_a'],pair['policy_b']):
            continue
        other = pair['policy_b'] if pair['policy_a']=='versioned' else pair['policy_a']
        if other not in ('full','lexical','no_conflict'):
            continue
        sign = 1 if pair['policy_a']=='versioned' else -1
        mean = sign*pair['mean']
        lo, hi = sorted(sign*x for x in pair['descriptive_normal_interval_95'])
        mean, lo, hi = (0.0 if abs(x)<1e-12 else x for x in (mean,lo,hi))
        md.append(f"| {other} | {pair['n']} | {100*mean:.1f} | [{100*lo:.1f}, {100*hi:.1f}] |")
        tex.append(tex_escape(other)+f" & {pair['n']} & {100*mean:.1f} & [{100*lo:.1f}, {100*hi:.1f}] "+r'\\')
    tex += [r'\bottomrule\end{tabular}',r'\caption{Exploratory paired normal intervals on task differences. Small related synthetic cases and unadjusted comparisons preclude significance or generalization claims.}\end{table}']
    for section in ('discussion','conclusion'):
        md += ['', '## '+section.title(),'',prose[section],'']
        tex += [r'\section{'+section.title()+'}',tex_prose(prose[section])]
    disclosure = ('This is an engineering extension and a small synthetic structured-record evaluation, not an evaluation of '
                  'unstructured conversation ingestion, real tool use or unrestricted long-term assistants. No embedding retrieval '
                  'or Mem0/A-MEM implementation is reproduced, and bitemporal modeling is established prior art. There is one '
                  'model response per fixed case, not an independent-model or repeated-sampling robustness study. Related task '
                  'families and small samples limit uncertainty interpretation. Evidence recall measures source records available '
                  'in context, not citations produced by the model; summary-source IDs do not prove facts survived compression. '
                  'Model prose was generated and mechanically checked; measured tables were inserted by code. Codex assisted '
                  'design, implementation and review. The official Stanford and paper-agent scores for this manuscript are pending. '
                  'The Rail was loaded from JiuwenSwarm source on the installed openJiuwen ReActAgent; the full desktop Swarm '
                  'assembly is not evaluated. Source snapshots, frozen code hashes and provider usage accompany this draft.')
    md += ['## Limitations and reproducibility disclosure','',disclosure,'', '## References','']
    tex += [r'\section{Limitations and Reproducibility Disclosure}',tex_escape(disclosure),r'\begin{thebibliography}{9}']
    for ref in REFERENCES:
        md.append(f"[{ref['key']}] {ref['authors']} ({ref['year']}). {ref['title']}. {ref['url']}")
        tex.append(r'\bibitem['+tex_escape(ref['authors'].split(' et al.')[0])+f" et al.({ref['year']})"+']{'+ref['key']+'} '+
                   tex_escape(f"{ref['authors']} ({ref['year']}). {ref['title']}. ")+r'\url{'+ref['url']+'}.')
    tex += [r'\end{thebibliography}',r'\end{document}']
    (output/'paper.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    (output/'paper.tex').write_text('\n'.join(tex)+'\n',encoding='utf-8')
    shutil.copy2(Path(__file__).resolve().parents[1]/'output/paper/iclr2026_conference.sty',output/'iclr2026_conference.sty')
    draw_figures(summary, output)
    claims = [{'claim_id':f"test.{r['policy']}.{r['budget']}.exact", 'metric_ref':{'split':'test','policy':r['policy'],'budget':r['budget']},
               'value':r['exact_accuracy'],'evidence_id':evidence['artifact_id']} for r in rows+sensitivity]
    manuscript = _artifact(output/'manuscript_artifact.json','ManuscriptBundle',
        {'title':TITLE,'sections':prose,'claims':claims,'evidence_id':evidence['artifact_id'],
         'rendered_files':{'paper.md':file_digest(output/'paper.md'),'paper.tex':file_digest(output/'paper.tex')}},[evidence['artifact_id']])
    _artifact(output/'mechanical_review.json','ReviewDecision',
        {'passed':True,'issues':[],'coverage':['source, code, dataset, call, selection and request integrity',
         'prose numeric/citation whitelist','programmatic heldout tables'],
         'external_scores':{'stanford_agentic_reviewer':None,'paper_evaluation_agent':None},
         'not_covered':['scientific novelty','human evaluation','free-form semantic validity']},
        [manuscript['artifact_id'],evidence['artifact_id']])
    return manuscript


async def write_memory_paper(source, output, *, max_total_tokens=300000, config_dir=None):
    from baseline.runtime import read_model_config, token_count
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    evidence, summary = capture_evidence(source, output)
    config = read_model_config(config_dir)
    manifest = evidence['payload']['manifest']
    if config['model'] != manifest['model'] or config['provider'] != manifest['provider'] or digest(config['api_base']) != manifest['endpoint_hash']:
        raise ValueError('Model condition differs from frozen experiment')
    gateway = ModelGateway(config, source, max_total_tokens=max_total_tokens,
                           max_calls=manifest['max_calls'], wall_seconds=manifest['wall_seconds'],count_tokens=token_count)
    prose = await draft_sections(gateway, evidence, output)
    render_paper(prose, evidence, summary, output)
    save_json(output/'writing_status.json',{'status':'succeeded','evidence_id':evidence['artifact_id']})
    updated = analyze_memory(source)
    save_json(output/'resources.json',{'end_to_end':updated['resources'],
        'experiment_only':summary['resources'],'token_admission_limit':max_total_tokens,
        'currency_cost':None,'currency_cost_reason':'No dated price/invoice evidence; SDK zero-cost fields ignored.',
        'spend_limit_note':'Conservative proxy admission with actual provider reconciliation; not a provider-side hard billing cap.',
        'per_stage':{stage:{'calls':len(cs),'tokens':sum(c['usage']['total_tokens'] for c in cs if c['usage'])}
                     for stage,cs in {'experiment':[c for c in gateway.calls if not c['tag'].startswith('paper/')],
                                      'writing_and_internal_review':[c for c in gateway.calls if c['tag'].startswith('paper/')]}.items()}})
    return {'paper':str(output/'paper.tex'),'resources':gateway.totals()}
