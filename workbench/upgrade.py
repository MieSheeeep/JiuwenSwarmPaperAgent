"""Read-only presentation of the new review-gap study, never private model config."""
from pathlib import Path
import hashlib


GAPS=[
    ('external','外部效度与样本规模','research/external_benchmark.py','官方清洗版 500 题；匹配子集与完整主方法分别报告。'),
    ('semantic','语义与混合检索','research/advanced_retrieval.py','固定权重的本地 MiniLM、BM25、RRF；无远程 embedding 费用。'),
    ('conflict','冲突感知回答','research/review_upgrade.py','基础、冲突核验及双调用反思，保留实际费用与负结果。'),
    ('packing','装包机制与预算消融','research/advanced_retrieval.py','原子组、动态规划代理目标、多样性；真实拼接 token 再检查。'),
    ('robustness','多种子、多模型与重复','research/upgrade_protocol.py','三组新主测试种子、Flash / Pro、重复回答及任务聚类统计。'),
    ('errors','错误分析与机制解释','research/upgrade_errors.py','区分证据可用性与回答正确性，避免相关性被写成因果。'),
    ('statistics','匹配比较与不确定性','research/upgrade_analysis.py','共同任务、重复不充样本量、配对检验与多重比较说明。'),
    ('accounting','资源与 Token 校准','research/model_gateway.py','全阶段实际用量计账；选择预算与供应商账单分别展示。'),
    ('writing','证据驱动写作与审稿回复','research/claim_revision.py','主张关联哈希和测量字段；逐项保留未充分解决的问题。'),
    ('portability','框架接口与可复现性','research/agent_invocation.py','实际 ReActAgent、独立 Rail、固定模型与数据身份。'),
]
ALLOWED={'protocol.json','summary.json','REPORT.md','analysis.json','analysis_report.md','model_catalogue.json',
         'preprocessing.json','cohorts.json','grid.json','run_state.json','claim_ledger.json','chapter_plan.json','reviewer_response.md',
         'retrieval_audit_summary.json','runtime_versions.json','protocol_amendments.jsonl'}
ALLOWED.update({'framework_contribution.patch','framework_contribution.json','resource_report.json','resources_all_stages.json',
                'parallel_assignment.json','segment_merge_manifest.json','error_analysis.json','error_analysis_report.md','local_resources.json','admission_reserves.json','external_review.json'})
PAPER_FILES={'paper.pdf':'paper/paper.pdf','paper.tex':'paper/paper.tex','paper.md':'paper/paper.md',
             'references.json':'paper/references.json','figure_manifest.json':'paper/figure_manifest.json',
             'writing_status.json':'paper/writing_status.json','internal_review.txt':'paper/internal_review.txt',
             'review_revisions.json':'paper/review_revisions.json','final_sections.json':'paper/final_sections.json',
             'editorial_revisions.json':'paper/editorial_revisions.json','implementation_evidence.json':'paper/implementation_evidence.json'}


def _paper_current(directory,status):
    if status.get('status')!='succeeded':return False
    for name,key in [('paper/paper.pdf','paper_sha256'),('summary.json','source_summary_sha256'),('analysis.json','source_analysis_sha256')]:
        path=directory/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=status.get(key):return False
    return True


def payload(repository):
    root=repository.root;directory=repository._safe(root/'output/review_upgrade_20261106')
    protocol=repository._json(directory/'protocol.json',{})
    state=repository._json(directory/'run_state.json',{})
    summary=repository._json(directory/'summary.json',{})
    analysis=repository._json(directory/'analysis.json',{})
    catalogue=repository._json(directory/'model_catalogue.json',{})
    paper_status=repository._json(directory/'paper/writing_status.json',{})
    if paper_status.get('status')=='succeeded' and not _paper_current(directory,paper_status):
        paper_status={**paper_status,'status':'stale_evidence'}
    resource_report=repository._json(directory/'resource_report.json',{})
    external_review=repository._json(directory/'external_review.json',{})
    if external_review and external_review.get('paper_sha256')!=paper_status.get('paper_sha256'):
        external_review={'review_status':'stale_submission','score':None}
    score=external_review.get('score') if external_review.get('review_status')=='complete' else None
    score_note=('新稿已送 Stanford Agentic Reviewer，正在等待结果；旧稿分数不移植。' if external_review.get('submitted') and score is None
                else f'新稿 Stanford AI 评审 {score}/10；不是会议录用或比赛总分。' if score is not None
                else '新研究尚无 Stanford / 比赛官方新评分；旧稿分数不移植。')
    from research.jsonl_ledger import read_jsonl
    calls=read_jsonl(directory/'calls.jsonl')
    requests=read_jsonl(directory/'requests.jsonl')
    results=read_jsonl(directory/'results.jsonl')
    if calls and not str(state.get('status','')).startswith('parallel_'):
        summary={**summary,'completed':len(results),'resources':{**summary.get('resources',{}),
            'total_calls':len(requests),'total_tokens':sum(c['usage']['total_tokens'] for c in calls if c.get('usage')),
            'unknown_usage_calls':sum(not bool(c.get('usage')) for c in calls),
            'in_flight_requests':len(requests)-len(calls)}}
    gaps=[]
    for key,title,source,note in GAPS:
        gaps.append({'id':key,'title':title,'source':source,'note':note,
                     'implementation_ready':(root/source).is_file(),'empirical_status':'以实际对照与评审判断；代码实现不等于缺口已解决'})
    return {'run_id':'review_upgrade_20261106','state':state,'protocol':protocol,'summary':summary,'analysis':analysis,
            'models':catalogue.get('models',[]),'gaps':gaps,
            'paper_status':paper_status,'resource_report':resource_report,'external_review':external_review,
            'files':[{'name':name,'bytes':(directory/name).stat().st_size} for name in sorted(ALLOWED) if (directory/name).is_file()]+
                    [{'name':name,'bytes':(directory/path).stat().st_size} for name,path in PAPER_FILES.items() if (directory/path).is_file() and (name!='paper.pdf' or paper_status.get('status')=='succeeded')],
            'score':score,'score_note':score_note}


def file_path(repository,name):
    if name not in ALLOWED and name not in PAPER_FILES:raise KeyError('Unknown research artifact')
    directory=repository.root/'output/review_upgrade_20261106'
    if name=='paper.pdf' and not _paper_current(directory,repository._json(directory/'paper/writing_status.json',{})):raise KeyError('PDF build unavailable or stale')
    path=repository._safe(directory/PAPER_FILES.get(name,name))
    if not path.is_file():raise KeyError('Missing research artifact')
    return path
