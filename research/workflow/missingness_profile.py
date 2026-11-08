"""Mask-integrated study profile with bounded Flash authoring and evidence checks."""
from io import BytesIO
from pathlib import Path
import copy
import json
import subprocess
from urllib.request import Request,urlopen
from pypdf import PdfReader
from research.artifacts import save_json,file_digest,atomic_write
from .profile import ConnectedProfile
from .digits_profile import FlashBackend,SourcePage,HEADINGS
from .engine import Workflow,StageResult
from .missingness_study import MissingnessStudy,POLICIES
from .missingness_reporting import summarize,theory_text,LABELS
from .delivery import inspect_pdf

ARXIV=('1307.1493','2406.16484','2407.19804','2409.07510')


def literature(directory):
    folder=Path(directory)/'literature';folder.mkdir(exist_ok=True)
    result=[]
    for identifier in ARXIV:
        html=folder/(identifier+'.html');pdf=folder/(identifier+'.pdf');text=folder/(identifier+'.txt')
        if not html.exists():
            with urlopen(Request('https://arxiv.org/abs/'+identifier,headers={'User-Agent':'JiuwenResearch/1.0'}),timeout=45) as r:html.write_bytes(r.read(2_000_000))
        page=SourcePage();page.feed(html.read_text(encoding='utf-8'))
        if not page.meta.get('citation_title') or not page.abstract:raise ValueError('Primary paper metadata missing')
        if not pdf.exists():
            with urlopen(Request('https://arxiv.org/pdf/'+identifier,headers={'User-Agent':'JiuwenResearch/1.0'}),timeout=60) as r:pdf.write_bytes(r.read(30_000_000))
        if not text.exists():
            reader=PdfReader(BytesIO(pdf.read_bytes()))
            atomic_write(text,'\n\n'.join(page.extract_text() or '' for page in reader.pages))
        full=text.read_text(encoding='utf-8')
        if len(full)<3000:raise ValueError('Paper full-text extraction incomplete')
        result.append({'id':identifier,'title':page.meta['citation_title'][0],
            'authors':page.meta.get('citation_author',[]),'published':page.meta.get('citation_date',[''])[0],
            'url':'https://arxiv.org/abs/'+identifier,'reading_scope':'Full PDF retrieved/extracted; abstract and first 1600 characters of text supplied for comparison. Local full text is available; source algorithms not reproduced.',
            'source_pdf_sha256':file_digest(pdf),'chunks':[{'text':' '.join(page.abstract).strip()},{'text':full[:1600]}]})
    url='https://proceedings.mlr.press/v206/zhou23b.html'
    path=folder/'zhou23b.html'
    if not path.exists():
        with urlopen(url,timeout=45) as r:path.write_bytes(r.read(1_000_000))
    result.append({'id':'zhou23b','title':'Domain Adaptation under Missingness Shift',
        'authors':['Helen Zhou','Sivaraman Balakrishnan','Zachary Lipton'],'published':'2023',
        'url':url,'reading_scope':'Publisher abstract and metadata inspected; full algorithm not reproduced.',
        'chunks':[{'text':'DAMS studies source/target missing-mechanism changes. The publisher abstract states that indicators can reduce DAMS to covariate shift and develops an analytic adjustment for linear models under underreporting completely at random. This study selects among fixed fitted candidates instead of reproducing their adaptation algorithm.'}],
        'source_sha256':file_digest(path)})
    return result


class MissingnessProfile(ConnectedProfile):
    def __init__(self,directory,*,model=None):
        super().__init__(directory,model=model or FlashBackend())
        self.study=MissingnessStudy(directory);self.compiler=self.compile_with_equations

    def evidence(self,inputs):
        a=inputs['analysis'];d=inputs['design']
        primary={name:[] for name in ('wine_red','wine_white','airfoil','yacht')}
        for r in a['metrics']:
            if r['condition']=='mcar_0.5':primary[r['dataset']].append([r['method'],r['nrmse_mean'],r['nrmse_split_sd'],r['regret_mse_mean']])
        curves=[]
        for dataset in primary:
            for method in ('clean','mc_worst9','analytic_minimax','native_hist'):
                selected=[next(r for r in a['metrics'] if (r['dataset'],r['condition'],r['method'])==(dataset,c,method))['nrmse_mean'] for c in ('clean','mcar_0.1','mcar_0.3','mcar_0.5','block_0.3','mar_0.3')]
                curves.append([dataset,method,*selected])
        timing=[]
        for dataset in primary:
            records=[r for r in a['selection_records'] if r['dataset']==dataset]
            import numpy as np
            timing.append({'dataset':dataset,'same_selection_as_sampled9':sum(r['integrated_and_sampled9_agree'] for r in records),
                'splits':len(records),'sampled27_ms_median':float(np.median([r['sampled27_ms'] for r in records])),
                'integrated_coefficients_plus_envelope_ms_median':float(np.median([r['integrated_with_coefficients_ms'] for r in records])),
                'split_counts':[r['split_counts'] for r in records]})
        stress=[]
        for dataset in primary:
            for condition in ('mcar_0.3','block_0.3','mar_0.3'):
                base=next(r for r in a['metrics'] if (r['dataset'],r['condition'],r['method'])==(dataset,condition,'clean'))
                selected=next(r for r in a['metrics'] if (r['dataset'],r['condition'],r['method'])==(dataset,condition,'analytic_minimax'))
                stress.append([dataset,condition,selected['nrmse_mean']-base['nrmse_mean'],base['actual_missing_fraction']])
        return {'question':inputs['question'],'datasets':d['datasets'],'protocol':{k:v for k,v in d.items() if k not in ('datasets','code_sha256')},
            'primary_p50_columns':['policy','mean_split_nrmse','sd_split_nrmse','mean_regret_pool_normalized_mse'],
            'primary_p50':primary,'curve_columns':['dataset','policy','clean','mcar_0.1','mcar_0.3','mcar_0.5','block_0.3','mar_0.3'],
            'curves':curves,'paired_intervals':a['paired_intervals'],'validation_timing_and_choices':timing,
            'stress_columns':['dataset','condition','integrated_minus_clean_nrmse','actual_missing_fraction'],
            'stress_results':stress,
            'theory':a['theory'],'limitations':a['limitations'],'audit':a['audit'],'resources':a['resources'],
            'source_papers':inputs['literature']['sources'],'measured_rows_hash':a['rows_hash'],
            'figure_captions':[f['caption'] for f in a['figures']],'table_captions':[t['caption'] for t in a['tables']],
            'critical_definitions':'Primary normalized RMSE = sqrt(mean squared error averaged across nine shared test masks within a split), then split-mean reported. Targets normalized by training SD, not original-unit RMSE. Oracle uses test labels and only lower-bounds the affine pool, not KNN/HistGB. Known-p gets declared p but not test labels. No test-set tuning. Conditional bootstrap uses root pooled loss, not the mean of split roots; the difference is intentional. Row groups make repeated test memberships dependent. No end-to-end timing claim.'}

    async def execute(self,context):
        self.context=context;before={r['id'] for r in self.calls};inputs=context.inputs;stage=context.stage
        if stage=='literature':
            papers=literature(self.directory)
            notes=await self.json('Compare supplied primary sources for fixed-predictor model selection under changing missingness rates. Return comparison (under 280 words), limitations (list). Explicitly acknowledge prior dropout expected-loss algebra, existing missingness-shift methods, and imputation benchmarks. Do not claim novelty or reproduction of their algorithms.',papers,'literature/compare')
            value={**notes,'sources':papers}
        elif stage=='question':
            value={'question':'Can exact mask-integrated validation select fixed linear prediction pipelines usefully when future missingness rate is uncertain?',
                'hypothesis':'Exact integration removes validation-mask Monte Carlo error under its affine/MCAR assumptions; its choices need not improve test risk or extend to correlated missingness.',
                'source_ids':[*ARXIV,'zhou23b'],'falsification':'Report all four datasets, five feature-group splits, all rates, both out-of-family stress tests and all selectors; compare risk/regret with sampled validation and stronger contextual models. No requirement to beat clean validation.',
                'authority':'User authorized a new easy-to-run research topic; operator selected and froze this design before held-out performance.'}
        elif stage=='design':
            from . import missingness_study
            value={**self.study.prepare(),'code_sha256':file_digest(Path(missingness_study.__file__)),
                'split':{'protocol':'Feature-group random splits, seeds101/211/307/401/503, approx60/20/20'},
                'methods':[*POLICIES,'known_p','oracle','knn_ridge','native_hist'],
                'metrics':['normalized_rmse','normalized_mse','regret_pool_mse','conditional_paired_bootstrap','validation_seconds'],
                'budget':Workflow(self.directory).state['limits'],'acceptance':'No promised performance gain; honest reporting under frozen selection/evaluation boundaries.'}
            save_json(self.directory/'frozen_protocol.json',value)
        elif stage=='implementation':
            self.study.check(inputs['design']);value={'adapter':self.study.name,'version':self.study.version,
                'capabilities':['fresh_linear_and_reference_model_fits','validation_only_selection','mask_integration','common_test_masks','prediction_replay'],
                'source_sha256':inputs['design']['code_sha256'],'operator_implemented':True}
        elif stage=='pilot':value=self.study.pilot(inputs['design'])
        elif stage=='experiment':
            result=self.study.run(inputs['design']);value={'results':result['rows'],'protocol_hash':Workflow(self.directory).state['stages']['design']['sha256'],
                'resources':result['resources'],'raw_hash':result['rows_sha256'],'files':result['files']}
        elif stage=='analysis':
            value=summarize(self.study,inputs['design']);value['experiment_hash']=Workflow(self.directory).state['stages']['experiment']['sha256']
        elif stage=='writing':
            if context.feedback:
                previous=max([json.loads(p.read_text(encoding='utf-8')) for p in (self.directory/'artifacts').glob('writing-*.json')],key=lambda a:a['created_at'])['payload']
                issues=context.feedback[-1]['issues'];headings={i.get('section','') for i in issues if isinstance(i,dict)}&set(HEADINGS)
                if not headings:headings={'Results','Discussion','Conclusion'}
                facts=self.evidence(inputs);facts.pop('source_papers',None)
                patch=await self.json('Correct only supplied manuscript sections using verified evidence and review. Return replacements (list of heading,text), no other keys. Under 1100 words. Do not change numbers, assumptions or scientific settings merely to satisfy a reviewer. Retain correct information and narrow unsupported claims.',
                    {'sections':[s for s in previous['sections'] if s['heading'] in headings],'issues':issues,'facts':facts},'writing/patch')
                replacements={r['heading']:r['text'] for r in patch['replacements']}
                if set(replacements)!=headings:raise ValueError('Unexpected repair headings')
                save_json(self.directory/'last_missingness_patch.json',patch)
                value={**previous,'sections':[{'heading':s['heading'],'text':replacements.get(s['heading'],s['text'])} for s in previous['sections']]}
            else:
                evidence=self.evidence(inputs)
                outline=await self.json('Plan a research paper with these exact headings: '+', '.join(HEADINGS)+'. Return outline (under 400 words) and limitations. Center the exact finite-validation risk identity, controlled model selection comparison, all observed outcomes and limits. No claim of a new general theorem or universal robust prediction.',evidence,'writing/outline')
                save_json(self.directory/'outline.json',outline)
                value=await self.json('Write an English research manuscript about mask-integrated validation for selecting fixed linear predictors under missingness-rate shift. Return title,sections (list of heading,text),references (list of known source IDs). Use exactly: '+', '.join(HEADINGS)+'. Aim 2400-3200 words total. Full paragraphs, no raw TeX or markdown tables. Code inserts measured tables, two quantitative figures and the exact equations under Methods. Explain the short proof in words and refer to the displayed identity. Sources are prior work; acknowledge expected-loss/dropout algebra is established. No unsupported first/novel/SOTA claims. This study uses four datasets from three families and five overlapping feature-group splits, not twenty independent populations. Explain twelve common candidates, validation selection, exact-vs-grid control, known-p diagnostic, label-informed pool oracle, nonlinear references outside the pool, target normalization, conditional bootstrap limits, and outside-MCAR stress. Cite sources as [ID]. Report positive, null and negative outcomes; avoid claiming broad superiority from one dataset. Timing excludes fitting and is not end-to-end speed. Do not quote full hashes. Avoid guarantees that extend finite-validation mask integration to population risk or correlated/MAR missingness.',
                    {'evidence':evidence,'outline':outline,
                     'display_equation_numbering':'Code inserts predictor (1), e/d definitions (2), expected-loss identity (3), quadratic risk (4), coefficients (5). Refer to the identity as (3), or avoid numbering. No equation gives a population-risk guarantee.'},'writing/draft')
                save_json(self.directory/'model_draft_capture.json',value)
                if {s['heading'] for s in value['sections']}!=set(HEADINGS):raise ValueError('Manuscript heading mismatch')
                if sum(len(s['text'].split()) for s in value['sections'])<1800:raise ValueError('Manuscript too short')
                canonical={p['id']:p for p in inputs['literature']['sources']}
                reference_ids=[r if isinstance(r,str) else r.get('id') for r in value['references']]
                if any(identifier not in canonical for identifier in reference_ids):raise ValueError('Unknown reference')
                value['references']=[{k:canonical[identifier][k] for k in ('id','title','authors','published','url')} for identifier in reference_ids]
            value.update(evidence_hash=Workflow(self.directory).state['stages']['analysis']['sha256'],
                figures=copy.deepcopy(inputs['analysis']['figures']),tables=copy.deepcopy(inputs['analysis']['tables']))
        elif stage=='review':
            audit=self.study.audit(inputs['design'])
            if context.feedback and (self.directory/'last_missingness_patch.json').exists():
                patch=json.loads((self.directory/'last_missingness_patch.json').read_text(encoding='utf-8'))
                all_facts=self.evidence(inputs)
                facts={k:all_facts[k] for k in ('primary_p50','paired_intervals','stress_results','stress_columns','theory','critical_definitions')}
                value=await self.json('Check these changed excerpts against earlier issues and measured facts. Return decision (accept|revise|stop),issues (at most two {section,issue,evidence,repair}). Entire JSON under 180 words. Previously correct algebra and correctly rounded tables need no repair. Operator also corrected overstatements about equal selections and stress-test gains; check these against facts. This is a focused follow-up, not fresh whole-paper review. Do not expand to new experiments or invent scientific requirements.',
                    {'revised_sections':patch['replacements'],'earlier_issues':context.feedback[-1]['issues'],'facts':facts},'review/patch_audit')
                value['scope']='Focused Flash follow-up after prior manuscript audit, with actual local metric/prediction replay.'
            else:
                value=await self.json('Audit manuscript against supplied primary-source evidence, exact algebra and measured results. Return decision (accept|revise|stop),issues (at most THREE {section,issue,evidence,repair}),checks. Under 1100 tokens. Name exact mismatches; validate equations, assumptions, dataset/split independence, oracle privileges, RMSE aggregation and bootstrap scope. Correct approximations/ranges are acceptable. Do not invent mistakes by mentally recounting a partial table or require SOTA for a scoped empirical paper. State incomplete evidence as such, do not predict conference scores. This is a single-Flash factual audit, not external peer review.',
                    {'manuscript':inputs['writing'],'evidence':self.evidence(inputs),'observed_replay':audit},'review/audit')
                value['scope']='Single Flash factual audit plus actual affine prediction and all-metric replay; not external peer review.'
            if value.get('decision')=='revise':value['target']='writing'
            save_json(self.directory/'review_capture.json',value)
        elif stage=='export':
            value=self.compiler(inputs['writing']);pdf=next(k for k in value['files'] if k.endswith('.pdf'))
            value['inspection']=inspect_pdf(self.directory/pdf,self.directory/'workspace/paper/previews')
            value['checks'].update(internal_review_accepted=inputs['review']['decision']=='accept',
                evidence_bound=inputs['writing']['evidence_hash']==Workflow(self.directory).state['stages']['analysis']['sha256'],
                prediction_metric_replay=self.study.audit(inputs['design'])['status']=='verified')
            value['external_review']='not submitted';value['submission_materials_complete']=False
        else:raise ValueError('Unknown research stage')
        return StageResult(value,self.usage([r for r in self.calls if r['id'] not in before]))

    def compile_with_equations(self,manuscript):
        compiled=self.service.compile_paper(manuscript)
        paper=self.directory/'workspace/paper';path=paper/'paper.tex'
        tex=path.read_text(encoding='utf-8').replace(r'\documentclass{article}',r'\documentclass{article}'+'\n'+r'\usepackage{amsmath,amssymb}')
        block=r'''
\paragraph{Exact finite-row mask integration.}
Let $M_j\sim\mathrm{Bernoulli}(p)$ independently, with $M_j=1$ denoting a missing feature. For fixed coefficients and fills,
\begin{align}
\widehat y(M)&=b+\sum_j a_j[(1-M_j)x_j+M_j f_j]+\sum_j c_jM_j,\\
e&=b+a^\top x-y,\qquad d_j=a_j(f_j-x_j)+c_j,\\
\mathbb E_M[(\widehat y(M)-y)^2\mid x,y]
&=\left(e+p\sum_j d_j\right)^2+p(1-p)\sum_j d_j^2.
\end{align}
Averaging over complete validation rows yields
\begin{align}
R(p)&=A p^2+B p+C,\\
A&=\overline{(\sum_j d_j)^2-\sum_j d_j^2},\quad
B=\overline{2e\sum_j d_j+\sum_j d_j^2},\quad C=\overline{e^2}.
\end{align}
The interval maximum is evaluated at its endpoints and, when $A<0$, at $p_*=-B/(2A)$ if this point is interior. The selector minimizes this finite-validation maximum across the twelve fitted candidates. This identity does not establish population or out-of-family robustness.
'''
        marker=r'\section{Experimental Setup}'
        if marker not in tex:raise ValueError('Missing equation insertion anchor')
        atomic_write(path,tex.replace(marker,block+'\n'+marker))
        for _ in range(2):
            result=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-disable-installer','paper.tex'],cwd=paper,capture_output=True,text=True,timeout=90)
            atomic_write(paper/'compile_diagnostics.txt',result.stdout+result.stderr)
            if result.returncode:raise ValueError('Equation compilation failed; see local diagnostics')
        compiled['files']={str(p.relative_to(self.directory)):file_digest(p) for p in (paper/'paper.pdf',path)}
        return compiled
