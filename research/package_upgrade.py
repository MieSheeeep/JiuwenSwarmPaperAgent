"""Build a separate, explicit-allowlist upgrade bundle without legacy review tokens."""
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED


def sha(data):return hashlib.sha256(data).hexdigest()


def build_package(root=None):
    root=Path(root or Path(__file__).resolve().parents[1]);run=root/'output/review_upgrade_20261106'
    paper=run/'paper';status=json.loads((paper/'writing_status.json').read_text(encoding='utf-8'))
    if status.get('status')!='succeeded' or sha((paper/'paper.pdf').read_bytes())!=status.get('paper_sha256'):
        raise ValueError('No verified new-paper build')
    if sha((run/'summary.json').read_bytes())!=status.get('source_summary_sha256'):
        raise ValueError('Paper was written against a different experiment summary')
    if sha((run/'analysis.json').read_bytes())!=status.get('source_analysis_sha256'):
        raise ValueError('Paper was written against a different matched analysis')
    files={}
    def add(name,path):
        if Path(path).is_file():files[name.replace('\\','/')]=Path(path).read_bytes()
    def text(name,value):files[name]=value.encode('utf-8')
    for folder in ('research','baseline','tests','workbench'):
        for p in sorted((root/folder).glob('*.py')):add('code/'+str(p.relative_to(root)),p)
    for name in ('requirements-baseline.txt','requirements-research-upgrade.txt','README.md','config.example.yaml'):
        add('code/'+name,root/name)
    for name in ('frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json','frontend/vite.config.ts','frontend/index.html','scripts/start_workbench.ps1'):
        add('code/'+name,root/name)
    for folder in ('frontend/src','frontend/dist','frontend/tests'):
        for p in sorted((root/folder).rglob('*')):
            if p.is_file():add('code/'+str(p.relative_to(root)),p)
    for p in sorted((root/'docs').glob('*.md')):
        add('docs/'+p.name,p);add('code/docs/'+p.name,p)
    for name in ('review_related_work_20261106.json','deepseek_pricing_20261106.json'):
        add('sources/'+name,root/'sources'/name)
        add('code/sources/'+name,root/'sources'/name)
    from workbench.upgrade import ALLOWED
    for name in sorted(ALLOWED | {'dataset.json','results.jsonl','judgments.jsonl','calls.jsonl','requests.jsonl'}):
        add('code/output/review_upgrade_20261106/'+name,run/name)
    for folder in [*run.glob('segments*'),run/'protocol_versions',run/'preflight_protocol_versions']:
        if not folder.is_dir():continue
        for path in sorted(folder.rglob('*')):
            if path.is_file() and path.suffix in {'.json','.jsonl','.py'}:
                add('code/output/review_upgrade_20261106/'+str(path.relative_to(run)),path)
    for p in sorted(paper.iterdir()):
        if p.suffix in {'.pdf','.tex','.sty','.md','.json','.txt','.png','.svg'}:add('paper/'+p.name,p)
    for name in ('calls.jsonl','requests.jsonl'):
        add('code/output/review_upgrade_20261106/writing_ledger/'+name,run/'writing_ledger'/name)
    for name in ('framework_contribution.patch','framework_contribution.json','resource_report.json'):
        add(name,run/name)
    from research.package_release import FRAMEWORK_FILES
    for name in [*FRAMEWORK_FILES,'jiuwenswarm/agents/harness/common/rails/frozen_messages_rail.py','docs/frozen_messages_rail.md','LICENSE','pyproject.toml']:
        add('code/upstream/'+name,root/'upstream'/name)
    add('code/output/paper/iclr2026_conference.sty',root/'output/paper/iclr2026_conference.sty')
    text('code/README.md','# Upgrade research runtime\n\nRun commands from this code directory with Python 3.12. Install requirements-baseline.txt and requirements-research-upgrade.txt. Supplied source modules are loaded directly from upstream/; installed SDK versions are pinned. Configure your private provider outside this bundle using config.example.yaml. Never copy private config into the bundle.\n\nSee docs/research_upgrade_20261106.md, docs/external_benchmark_protocol.md and docs/retrieval_upgrade.md for fixed public data/model downloads and checksums. Original data and weights are intentionally excluded. Start a NEW output directory when running changed source or on another machine. Frozen old ledgers are for offline audit, not an invitation to append new calls.\n\npython -m research.review_upgrade --output output/new_study --max-total-tokens 3000000\n\nThis command spends configured model API tokens. The cap includes later answer judging, reflection, writing and revisions. Original benchmark scores are not claimed.\n\nFor the Chinese read-only upgrade workbench: python -m workbench.server, then open http://127.0.0.1:8765/#upgrade. Built frontend assets are included; developing them requires npm ci and npm run build inside frontend/.\n')
    text('Agentic Reviewer/status.md','# New manuscript review\n\nNo external Stanford review has been obtained for this exact paper. Previous-paper tokens and scores are excluded. Upload this PDF and add the returned token/results before a final competition submission.\n')
    summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
    submission={'paper_sha256':status['paper_sha256'],'evaluation_complete':summary.get('evaluation_complete',False),
                'answer_conditions_complete':summary.get('answer_conditions_complete',False),
                'stanford_score':None,'paper_evaluation_agent_score':None,'competition_uploaded':False,
                'final_submission_ready':False,'reason':'Fresh external review/access token and competition upload remain outstanding.'}
    review_dir=root/'submission/review-upgrade-20261106'
    if (review_dir/'receipt.json').exists():
        receipt=json.loads((review_dir/'receipt.json').read_text(encoding='utf-8'))
        if receipt.get('paper_sha256')!=status['paper_sha256'] or not receipt.get('submitted'):
            raise ValueError('External review receipt does not bind this PDF')
        token=review_dir/'PaperReview-AccessToken.txt'
        if not token.is_file() or not token.read_text(encoding='utf-8').strip():raise ValueError('Submitted review token unavailable')
        for name in ('PaperReview-AccessToken.txt','receipt.json','review.txt'):
            add('Agentic Reviewer/'+name,review_dir/name)
        submission.update(stanford_score=receipt.get('score'),stanford_submission='submitted',stanford_review_status=receipt.get('review_status','pending'),
                          reason='New PDF submitted for review; independent paper-agent scoring and competition upload remain outstanding.')
        text('Agentic Reviewer/status.md','# New manuscript review\n\nSubmitted to paperreview.ai using the exact PDF SHA256 in receipt.json. Review status: '+str(receipt.get('review_status','pending'))+'. The private access token is included for the competition review workflow; do not publish it. Old-paper scores and tokens are excluded.\n')
    text('submission_status.json',json.dumps(submission,ensure_ascii=False,indent=2)+'\n')
    text('提交说明.md','# 全面优化研究包\n\n包含新版英文论文、实验与写作账本、匹配统计、错误分析、资源报告、中文工作台及框架贡献 patch。新稿尚无外部评审分数；本包不是已完成官网提交的证明。\n\n原始外部数据与本地模型权重不打包；按文档下载固定版本并核对哈希。模型 API 凭证需自行配置，未包含于本包。冻结协议中的原始机器路径用于溯源，迁移复现应创建新的运行目录和协议。\n')
    for name,data in files.items():
        if re.search(rb'\bsk-[A-Za-z0-9_-]{16,}',data):raise ValueError('Potential API secret in '+name)
    manifest={name:sha(data) for name,data in sorted(files.items())}
    text('bundle_manifest.json',json.dumps({'files':manifest,'paper_sha256':status['paper_sha256']},ensure_ascii=False,indent=2)+'\n')
    out=root/'submission/空梦轮年-全面优化-20261106.zip';out.parent.mkdir(exist_ok=True)
    with ZipFile(out,'w',compression=ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):z.writestr('空梦轮年/'+name,data)
    with ZipFile(out) as z:
        if z.testzip():raise ValueError('ZIP CRC failure')
        for name,expected in manifest.items():
            if sha(z.read('空梦轮年/'+name))!=expected:raise ValueError('ZIP digest mismatch')
    return {'archive':str(out),'files':len(files),'bytes':out.stat().st_size,**submission}


if __name__=='__main__':print(json.dumps(build_package(),ensure_ascii=False,indent=2))
