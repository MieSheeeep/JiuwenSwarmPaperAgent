"""CPU research audit over the shared workflow, with evidence-bound English writing."""
import copy
import json
from pathlib import Path
import re
import subprocess

from research.artifacts import file_digest, save_json
from .digits_profile import FlashBackend
from .engine import Workflow, StageResult, STAGES
from .profile import ConnectedProfile
from .pilot_pruning_study import PilotPruningStudy
from .delivery import inspect_pdf

HEADINGS=('Abstract','Introduction','Related Work','Methods','Experimental Setup',
          'Results','Discussion','Limitations','Conclusion','Reproducibility')


def validate_manuscript(value,known):
    if any(r.get('id') not in known for r in value.get('references',[])):
        raise ValueError('Unknown manuscript reference')
    body=' '.join(s['text'] for s in value['sections'])
    if re.search(r'[\u4e00-\u9fff]',body):raise ValueError('English manuscript required')
    inline=set()
    for bracket in re.findall(r'\[([^\]\n]+)\]',body):
        for token in re.split(r'[,;]\s*',bracket):
            token=token.strip()
            if token in known or re.fullmatch(r'\d{4}\.\d{4,5}|[a-z][a-z0-9.-]*',token):inline.add(token)
    if inline-set(known):raise ValueError('Unknown inline manuscript citation: '+', '.join(sorted(inline-set(known))))
    cited={r['id'] for r in value.get('references',[])}
    if inline-cited:raise ValueError('Inline citation missing from bibliography')
    if {s['heading'] for s in value['sections']}!=set(HEADINGS):raise ValueError('Incomplete manuscript headings')
    if len(body.split())<1200:raise ValueError('Manuscript too short')


def health_decision(value):
    return {**value,'decision':'go' if value['passed'] else 'no_go',
            'reason':'Numerical and execution health only; not a test for positive findings or novelty.'}


class PilotPruningProfile(ConnectedProfile):
    def __init__(self,directory,*,model=None):
        super().__init__(directory,model=model or FlashBackend())
        self.study=PilotPruningStudy(directory)

    def evidence(self,inputs):
        a=inputs['analysis'];d=inputs['design']
        selected=[r for r in a['metrics'] if r['delta']==.02 and r['mixture']=='equal'
                  and r['n'] in (32,128,256)]
        cases=inputs['experiment']['results']
        empirical={r['case_id'].split(':n')[0]:{k:r[k] for k in ('dataset','seed','pair','gain','discordance','test_count')}
                   for r in cases if r['kind']=='empirical'}
        costs=a['costs']; comparisons=[]
        for kind in ('synthetic','empirical'):
            for mixture in ('equal','futile3x','useful3x'):
                for interval in ('paired_normal','exact_joint'):
                    subset=[r for r in costs if r['kind']==kind and r['mixture']==mixture and r['interval']==interval]
                    groups={}
                    for r in subset:
                        key=tuple(r[k] for k in ('n','delta','c_defer','c_false_go','c_false_prune'))
                        groups.setdefault(key,{})[r['policy']]=r['expected_cost']
                    n=len(groups)
                    row={'kind':kind,'mixture':mixture,'interval':interval,'cost_cells':n}
                    for baseline in ('legacy_binary','delta_binary','matched_random_delta_binary','always_defer'):
                        differences=[x['tri_state']-x[baseline] for x in groups.values()]
                        row[baseline]={'tri_state_strictly_lower_cost':sum(v < -1e-12 for v in differences),
                                       'ties':sum(abs(v)<=1e-12 for v in differences),
                                       'difference_range':[min(differences),max(differences)]}
                    comparisons.append(row)
        return {'question':inputs['question'],'protocol':{k:d[k] for k in ('split','methods','metrics','grid','costs','mixture_rule','sampling_scope')},
                'dataset_shapes':[(x['name'],x['shape']) for x in d['datasets']],
                'scope':a['scope'],'primary_rows':selected,'all_cost_comparisons':comparisons,
                'empirical_pair_references':list(empirical.values()),
                'interval_coverage_range':{kind:{ci:[min(r['ci_coverage'] for r in cases if r['kind']==kind and r['interval']==ci),
                                                      max(r['ci_coverage'] for r in cases if r['kind']==kind and r['interval']==ci)]
                                                for ci in ('paired_normal','exact_joint')} for kind in ('synthetic','empirical')},
                'limitations':a['limitations'],'resources':inputs['experiment']['resources'],
                'audit':a['audit'],'figure_captions':[x['caption'] for x in a['figures']],
                'table_captions':[x['caption'] for x in a['tables']],
                'method_definition':{
                    'sampling':'D in {-1,0,+1}; P(D=+1)=(q+g)/2, P(D=-1)=(q-g)/2, P(D=0)=1-q. Integrate all multinomial count outcomes.',
                    'paired_normal':'ghat +/- 1.96 sqrt((qhat-ghat^2)/(n-1)), clipped to [-1,1]; sample variance uses n-1.',
                    'exact_joint':'Two two-sided marginal Clopper-Pearson intervals, each error alpha/2, each tail alpha/4. [Lplus-Uminus,Uplus-Lminus]. Union-bound fixed-look coverage at least1-alpha.',
                    'legacy_binary':'GO only if lower>0 AND observed gain>=delta; otherwise NO_GO.',
                    'boundary':'abs(g-delta)<=1e-12 is boundary; contributes denominator but neither error direction.',
                    'models':d['model']},
                'verified_editorial_notes':[
                    'Cost counts are pairwise wins, not counts of the global cheapest policy.',
                    'Synthetic useful3x exact_joint versus always_defer:356 cheaper and49 more expensive cells, maximum difference+0.000939833. A previous reviewer incorrectly called all405 cheaper despite this positive maximum; do not repeat that correction.',
                    'Empirical exact_joint delta.02 equal tri-state false-prune mass increases with n32/128/256 (7.117e-8,2.186e-6,2.347e-5), while deferral decreases. Do not call those values a decreasing sequence.',
                    'AlwaysGO/alwaysReject error masses depend on truth prevalence: empirical equal delta.02=.5/.5, synthetic equal delta.02=15/28 and9/28. Boundary4/28 has neither error direction.'],
                'sources':[{k:s.get(k) for k in ('id','title','authors','url','published','reading_scope','abstract')} for s in inputs['literature']['sources']],
                'interpretation':'All count outcomes integrated under IID categorical sampling. Errors are unconditional mixture masses, not conditional-on-useful rates. Boundary regimes remain denominators but have zero error mass. Cost cells are dependent sensitivity conditions, not independent experimental samples. No sequential continuation was implemented; larger fixed n is a separate more-data reference and cost of collecting observations is not in decision losses.'}

    async def execute(self,context):
        self.context=context;before={r['id'] for r in self.calls};inputs=context.inputs;stage=context.stage
        if stage=='question':
            value={'question':'How do interval construction, decision rules and nonzero deferral costs affect false pruning in research-agent performance-improvement pilots?',
                   'hypothesis':'Deferring inconclusive pilots can reduce false pruning, but increased deferral and its cost may erase any advantage; interval conservatism and decision logic must be separated.',
                   'source_ids':['1810.08240','2610.35971','2608.14905','scipy-cp'],
                   'falsification':'Report every frozen condition and all cost settings; no assumed universal dominance. Numerical health, not positive improvement, controls execution.',
                   'authority':'User explicitly requested own experiments and stopped repeated novelty vetoes; complete this scoped study. Classical statistical machinery is prior art.',
                   'idea_origin':'Operator code-audit lead after rejected model proposals; not claimed fully autonomous ideation.'}
        elif stage=='design':
            from . import pilot_pruning_study as core
            manifest=self.study.prepare()
            value={**manifest,'budget':Workflow(self.directory).state['limits'],
                   'manifest_sha256':file_digest(self.study.manifest_path),
                   'source_hashes':self.study.freeze_files([Path(core.__file__)]),
                   'grid':{'n':list(core.NS),'gain':list(core.GAINS),'discordance':list(core.DISCORDANCES),'delta':list(core.DELTAS),'alpha':.05,'validity':'abs(gain)<=discordance'},
                   'costs':{'defer':[.05,.25,1.],'false_go':[.25,1.,4.],'false_prune':[1.,4.,16.]},
                   'sampling_scope':'IID paired categorical fixed-look distribution; empirical replay with replacement from frozen finite test correctness, not population truth.',
                   'primary_reporting':{'delta':.02,'mixture':'equal','table_n':[32,128,256],'figures':'all fixed n; separate interval and kind; complete CSVs'},
                   'continuation_scope':'No sequential trajectories; n=256 fixed-budget reference. Observation acquisition and retraining costs are excluded from decision-loss model.',
                   'figure_formats':['pdf','png']}
            save_json(self.directory/'frozen_protocol.json',value)
        elif stage=='implementation':
            self.study._check(inputs['design'])
            value={'adapter':self.study.name,'version':self.study.version,'capabilities':['exact_count_integration','fixed_classifiers','immutable_prediction_replay','costed_deferral','registered_grid_audit'],
                   'operator_implemented':True,'source_hashes':inputs['design']['source_hashes']}
        elif stage=='pilot':
            value=health_decision(self.study.pilot(inputs['design']))
            save_json(self.directory/'health_pilot.json',value)
        elif stage=='experiment':
            measured=self.study.run(inputs['design'])
            value={'results':measured['rows'],'resources':measured['resources'],'raw_hash':measured['rows_sha256'],
                   'files':measured['files'],'protocol_hash':Workflow(self.directory).state['stages']['design']['sha256']}
        elif stage=='analysis':
            from .pilot_pruning_reporting import analyze
            value=analyze(self.study,inputs['design'])
        elif stage=='writing':
            known={s['id']:s for s in inputs['literature']['sources']}
            if context.feedback:
                previous=max((json.loads(p.read_text(encoding='utf-8')) for p in (self.directory/'artifacts').glob('writing-*.json')),key=lambda a:a['created_at'])['payload']
                value=await self.json('Revise the complete English manuscript to address the supplied substantive factual issues. Return title,sections,references with source id only. Preserve all measured values and scope. Do not add experiments or promise superiority. Full paragraphs, 1800-2400 words, same required headings. No raw TeX.',
                    {'previous':{k:previous[k] for k in ('title','sections','references')},'issues':context.feedback[-1]['issues'],'evidence':self.evidence(inputs)},'writing/revise')
            else:
                value=await self.json('Write an English empirical research report using only the supplied new results. Return title,sections(list of heading,text),references(list of source id objects). Exactly these headings: '+', '.join(HEADINGS)+'. Full paragraphs,1800-2400 words; no markdown tables or raw TeX. Cite source ids in square brackets. Explain paired categorical enumeration, both CI constructions and all six policies,matched random deferral across mixtures,strict threshold/boundary logic,4 datasets/3 splits/3 fixed model pairs,all5n/all3delta/all3mixtures/all27positive cost triples. Tables1-2 and Figures1-3 are inserted from measurements. Do not list every row in prose; explain representative values and full sensitivity ranges, including losses. No novel theorem claim, no ICLR acceptance claim, no independent count-state sample count, no significance claim, no real deployment or scientific-quality success claims. Important: costs exclude collecting extra observations; DEFER is a terminal action cost, not a measured continuation policy. A larger fixed n is NOT a sequential continuation experiment. The actual hypothesis may fail. Distinguish prior methods from newly measured results. Use at most180 words from each provided research source; focus on our own experiment. Classical Clopper-Pearson is sourced by scipy-cp; Howard source is about anytime intervals, not the source of our fixed-look algorithm.',
                    self.evidence(inputs),'writing/draft')
            save_json(self.directory/'model_draft_capture.json',value)
            validate_manuscript(value,known)
            value['references']=[{k:known[r['id']].get(k) for k in ('id','title','authors','published','url')} for r in value['references']]
            value.update(evidence_hash=Workflow(self.directory).state['stages']['analysis']['sha256'],
                         figures=copy.deepcopy(inputs['analysis']['figures']),tables=copy.deepcopy(inputs['analysis']['tables']))
        elif stage=='review':
            evidence=self.evidence(inputs);audit=self.study.audit(inputs['design'])
            manuscript={k:inputs['writing'][k] for k in ('title','sections','references')}
            value=await self.json('Independently audit this complete report against measured evidence. Return decision(accept|revise|stop),issues(list at most4 objects with location,claim,evidence,fix),target(writing if revise),checks. Under900words. Require numerical correctness,source fidelity,scope/cost honesty and adequate methods. Do not let a lack of positive performance turn a correct negative report into a failure. Conversely do not accept unsupported superiority. This is factual/editorial clearance of an exploratory report, not scientific novelty certification or venue acceptance. Each criticism must point to actual text and supplied evidence. Do not demand unperformed experiments as editorial fixes.',
                {'manuscript':manuscript,'evidence':evidence,'audit':audit},'review/factual_audit')
            if not audit['passed']:value={'decision':'stop','issues':[{'location':'artifacts','claim':'Audit failed','evidence':audit,'fix':'Repair provenance before export'}]}
            if value['decision']=='revise':value['target']='writing'
            contribution=await self.json('Assess scientific contribution separately from factual correctness. Return strengths,weaknesses,novelty_0_10,significance_0_10,readiness,recommended_next_experiments. Under450words. Do not inflate grade or equate a valid report with conference acceptance; do not reject honest reporting merely because methods are standard. No additional experiments are claimed.',
                {'manuscript':manuscript,'evidence_scope':evidence['interpretation'],'limitations':evidence['limitations']},'review/contribution')
            value['contribution_assessment']=contribution
            value['scope']='Fresh contexts of the same Flash family; factual/editorial clearance only, no external review.'
            save_json(self.directory/'review_capture.json',value)
        elif stage=='export':
            value=self.compile_report(inputs['writing'])
            pdf=next(p for p in value['files'] if p.endswith('.pdf'))
            value['inspection']=inspect_pdf(self.directory/pdf,self.directory/'workspace/paper/previews')
            value['checks'].update(evidence_bound=inputs['writing']['evidence_hash']==Workflow(self.directory).state['stages']['analysis']['sha256'],
                                   replay_verified=self.study.audit(inputs['design'])['passed'],factual_review_accepted=inputs['review']['decision']=='accept')
            value['review_scope']=inputs['review']['scope'];value['external_review']='not submitted'
        else:raise ValueError('Unimplemented audit stage: '+stage)
        return StageResult(value,self.usage([r for r in self.calls if r['id'] not in before]))

    def compile_report(self,manuscript):
        result=self.compiler(manuscript)
        paper=self.directory/'workspace/paper';tex=paper/'paper.tex'
        source=tex.read_text(encoding='utf-8').replace(r'\maketitle',r'\maketitle'+'\n'+r'\fancyhead[L]{Exploratory research report -- fixed-look pilot audit}')
        tex.write_text(source,encoding='utf-8')
        for _ in range(2):
            proc=subprocess.run(['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-disable-installer','paper.tex'],cwd=paper,capture_output=True,text=True,timeout=90)
            (paper/'compile_diagnostics.txt').write_text(proc.stdout+proc.stderr,encoding='utf-8')
            if proc.returncode:raise ValueError('Report compilation failed')
        result['files']={p:file_digest(self.directory/p) for p in result['files']}
        return result

    def registry(self):
        from .registry import Registry
        registry=Registry()
        for stage in STAGES[2:]:registry.stage(stage,self.execute)
        return registry
