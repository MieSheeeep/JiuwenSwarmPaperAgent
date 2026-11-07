"""New digits study stages over the shared workflow and pinned research skills."""
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.request import Request,urlopen
from research.artifacts import save_json,file_digest
from .agents import JiuwenBackend
from .engine import Workflow,StageResult,STAGES
from .profile import ConnectedProfile
from .digits_study import DigitsStudy
from .digits_reporting import analyze
from .delivery import inspect_pdf

SOURCE_IDS=('1705.08500','1706.04599','1906.02530','2405.05160','2305.15508')
HEADINGS=('Abstract','Introduction','Related Work','Methods','Experimental Setup','Results','Discussion','Limitations','Conclusion','Reproducibility')


class SourcePage(HTMLParser):
    def __init__(self):super().__init__();self.meta={};self.abstract=[];self.inside=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='meta' and attrs.get('name','').startswith('citation_'):
            self.meta.setdefault(attrs['name'],[]).append(attrs.get('content',''))
        if tag=='blockquote' and 'abstract' in attrs.get('class',''):self.inside=True
    def handle_endtag(self,tag):
        if tag=='blockquote':self.inside=False
    def handle_data(self,data):
        if self.inside:self.abstract.append(data)


def sources(directory):
    directory=Path(directory)/'literature';directory.mkdir(exist_ok=True)
    values=[]
    for identifier in SOURCE_IDS:
        path=directory/(identifier+'.html')
        if not path.exists():
            request=Request('https://arxiv.org/abs/'+identifier,headers={'User-Agent':'JiuwenResearch/1.0'})
            with urlopen(request,timeout=30) as response:raw=response.read(2_000_000)
            path.write_bytes(raw)
        page=SourcePage();page.feed(path.read_text(encoding='utf-8'))
        if not page.meta.get('citation_title') or not page.abstract:raise ValueError('Source metadata/abstract missing: '+identifier)
        values.append({'id':identifier,'title':page.meta['citation_title'][0],
            'authors':page.meta.get('citation_author',[]),'published':page.meta.get('citation_date',[''])[0],
            'url':'https://arxiv.org/abs/'+identifier,'reading_scope':'abstract and metadata only',
            'source_sha256':file_digest(path),'chunks':[{'text':' '.join(page.abstract).strip()}]})
    return values


class FlashBackend:
    def __init__(self):self.backend=JiuwenBackend()
    async def __call__(self,messages,context,tag):
        from baseline.runtime import read_model_config
        if read_model_config()['model']!='deepseek-flash':raise ValueError('Only deepseek-flash is authorized for this study')
        return await self.backend(messages,context,tag)


class DigitsProfile(ConnectedProfile):
    def __init__(self,directory,*,model=None):
        super().__init__(directory,model=model or FlashBackend())
        self.study=DigitsStudy(directory)

    def evidence(self,inputs):
        analysis=inputs['analysis'];design=inputs['design']
        rows=[]
        for row in analysis['metrics']:
            if row['target'] not in (.8,1.):continue
            rows.append({'condition':row['condition'],'method':row['method'],'target':row['target'],
                'coverage_mean_sd':[row['metrics']['coverage']['mean'],row['metrics']['coverage']['sd']],
                'accepted_error_mean_sd':[row['metrics']['selective_risk']['mean'],row['metrics']['selective_risk']['sd']],
                'aurc_mean':row['metrics']['aurc']['mean'],'min_accepted':row['min_accepted']})
        calibration=[{'condition':r['condition'],'method':r['method'],
            'nll_mean':r['metrics']['nll']['mean'],'ece15_mean':r['metrics']['ece15']['mean']}
            for r in analysis['metrics'] if r['method'] in ('msp','temperature_msp') and r['target']==.8]
        secondary=[{'condition':r['condition'],'method':r['method'],
            'coverage':r['metrics']['coverage']['mean'],'risk':r['metrics']['selective_risk']['mean']}
            for r in analysis['metrics'] if r['target']==.9]
        return {'question':inputs['question'],'protocol':{k:v for k,v in design.items() if k!='split'},
            'split_counts':analysis['split_counts'],'primary_results':rows,'secondary_results':secondary,
            'calibration_results':calibration,'temperatures':analysis['temperature'],
            'audit':analysis['audit'],'limitations':analysis['limitations'],'definitions':analysis['definition'],
            'literature':inputs['literature']['sources'],'resources':analysis['resources'],
            'environment':analysis['environment'],'rows_hash':analysis['rows_hash'],
            'figure_captions':[f['caption'] for f in analysis['figures']],
            'table_captions':[t['caption'] for t in analysis['tables']],
            'metric_notes':'AURC mean prefix error after stable descending confidence sort. ECE:15 equal-width bins. Temperature fit on validation NLL, T in [0.05,20]. Error SD is model initialization variability, not an independent-dataset confidence interval. Severe noise preserves labels but may obscure image identity.'}

    async def execute(self,context):
        self.context=context;before={r['id'] for r in self.calls}
        stage=context.stage;inputs=context.inputs
        if stage=='literature':
            papers=sources(self.directory)
            notes=await self.json('Compare these five abstracts for a small empirical study of clean-validation rejection thresholds under image corruption. Return comparison (under 350 words),limitations (list). Acknowledge selective classification and shift have prior work; no novelty claim. Do not infer unprovided full-text results.',papers,'literature/compare')
            value={**notes,'sources':papers}
        elif stage=='question':
            value={'question':'Do rejection thresholds selected for 80% clean-validation coverage preserve their operating behavior when digit images are corrupted?',
                'hypothesis':'Clean-derived confidence thresholds need not maintain target coverage or low accepted-sample error under corruption; temperature scaling need not repair selective ranking.',
                'source_ids':list(SOURCE_IDS),'falsification':'Report absolute mean coverage drift from 0.8 across every predeclared condition. A drift above 0.05 is a descriptive operational failure, not a significance test or risk-guarantee violation.',
                'authority':'User selected a new handwritten-digit reliability topic; operator froze experimental protocol before held-out scoring.'}
        elif stage=='design':
            from . import digits_study
            value={**self.study.prepare(),'budget':Workflow(self.directory).state['limits'],
                'code_sha256':file_digest(Path(digits_study.__file__)),
                'primary_drift_threshold':.05,'sampling_note':'Bundled digits dataset; one stratified random image split, no verified writer-group disjointness.'}
            save_json(self.directory/'frozen_protocol.json',value)
        elif stage=='implementation':
            self.study._check(inputs['design'])
            value={'adapter':self.study.name,'version':self.study.version,
                'capabilities':['fresh_mlp_training','validation_only_temperature_and_thresholds','corruptions','saved_weight_inference_replay'],
                'source_sha256':inputs['design']['code_sha256'],'operator_implemented':True}
        elif stage=='pilot':value=self.study.pilot(inputs['design'])
        elif stage=='experiment':
            measured=self.study.run(inputs['design'])
            value={'results':measured['rows'],'protocol_hash':Workflow(self.directory).state['stages']['design']['sha256'],
                'resources':measured['resources'],'raw_hash':measured['rows_sha256'],'files':measured['files']}
        elif stage=='analysis':
            value=analyze(self.study,inputs['design'])
            value['experiment_hash']=Workflow(self.directory).state['stages']['experiment']['sha256']
        elif stage=='writing':
            evidence=self.evidence(inputs)
            outline=await self.json('Plan a concise original empirical paper using supplied new experiment evidence. Return outline (at most 450 words) and limitations. Distinguish new measurements from algorithm novelty; this is a fresh study of established methods, not a new algorithm. Required headings: '+', '.join(HEADINGS),evidence,'writing/outline')
            save_json(self.directory/'outline.json',outline)
            value=await self.json('Write an English empirical research paper from the supplied newly trained digits study. Return title,sections (list of heading,text),references (list with known source IDs). Use exactly these headings: '+', '.join(HEADINGS)+'. Between 2200 and 3200 words total, full paragraphs, no markdown tables or raw TeX. Refer to supplied Table 1 and Figures 1-2; code inserts these from measured values. Cite sources using [arxiv ID]. Do not copy their abstract prose. The small sklearn 8x8 dataset is NOT MNIST; five models share the same split, and SD is initialization variability. State 1077/360/360 train/validation/test counts, all four confidence rules, two target coverages and seven conditions. Do not conflate calibration with ranking, matched validation target with guaranteed test coverage, or CPU models with the writing LLM. Do not invent uncertainty intervals, significance, public preregistration, algorithm novelty or ICLR acceptance. No old QA evidence. Explain the actual observed outcomes and their scope. Keep full artifact hashes out of prose. Preserve correct measurements if review feedback disputes them without evidence.',
                {'evidence':evidence,'outline':outline,'feedback':context.feedback},'writing/draft')
            save_json(self.directory/'model_draft_capture.json',value)
            for section in value['sections']:
                section['heading']=section['heading'].strip()
            if {s['heading'] for s in value['sections']}!=set(HEADINGS):raise ValueError('Digits manuscript headings incomplete')
            if sum(len(s['text'].split()) for s in value['sections'])<1800:raise ValueError('Digits manuscript too short')
            known={p['id']:p for p in inputs['literature']['sources']}
            if any(r.get('id') not in known for r in value['references']):raise ValueError('Unknown digits citation')
            value['references']=[{k:known[r['id']][k] for k in ('id','title','authors','published','url')} for r in value['references']]
            value.update(evidence_hash=Workflow(self.directory).state['stages']['analysis']['sha256'],
                figures=copy.deepcopy(inputs['analysis']['figures']),tables=copy.deepcopy(inputs['analysis']['tables']))
        elif stage=='review':
            audit=self.study.audit(inputs['design'])
            value=await self.json('Audit this manuscript against the measured evidence and observed saved-weight replay. Return decision (accept|revise|stop),issues (at most 3 concise substantive issues),target (writing if revise),finding_checks (list). Under 900 tokens total. Each criticism must cite an exact paper location and exact measured row or source. Do not override verified numbers by mentally recounting a partial list. This is an exploratory study, not an algorithm novelty claim. Do not demand SOTA or new experiments as a condition of truthful reporting; accept explicitly scoped observations if accurately described. No ICLR acceptance prediction. This is a single-model factual audit, not an independent cold multi-model panel.',
                {'manuscript':inputs['writing'],'measured_evidence':self.evidence(inputs),'replay':audit},'review/audit')
            save_json(self.directory/'review_capture.json',value)
            if value.get('decision')=='revise':value['target']='writing'
            value['scope']='Single Flash factual audit plus actual saved-weight inference and metric replay; no external peer review.'
        elif stage=='export':
            value=self.compiler(inputs['writing'])
            pdf=next(name for name in value['files'] if name.endswith('.pdf'))
            value['inspection']=inspect_pdf(self.directory/pdf,self.directory/'workspace/paper/previews')
            value['checks'].update(internal_review_accepted=inputs['review']['decision']=='accept',
                evidence_bound=inputs['writing']['evidence_hash']==Workflow(self.directory).state['stages']['analysis']['sha256'],
                saved_weight_replay=self.study.audit(inputs['design'])['status']=='verified')
            value['external_review']='not submitted';value['submission_materials_complete']=False
        else:raise ValueError('Unknown digits stage')
        return StageResult(value,self.usage([r for r in self.calls if r['id'] not in before]))
