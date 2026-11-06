"""Explicit file allowlist for the competition bundle; never copy private config."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
TEAM = '空梦轮年'
FRAMEWORK_FILES = [
    'jiuwenswarm/agents/harness/common/context_budget.py',
    'jiuwenswarm/agents/harness/common/rails/context_budget_rail.py',
    'jiuwenswarm/agents/harness/common/rails/__init__.py',
    'jiuwenswarm/agents/harness/common/versioned_memory.py',
    'jiuwenswarm/agents/harness/common/rails/versioned_memory_rail.py',
    'docs/versioned_memory.md',
]


def framework_patch():
    upstream = ROOT/'upstream'
    tracked = subprocess.run(['git','diff','HEAD','--',*FRAMEWORK_FILES],cwd=upstream,
                             capture_output=True,text=True,check=True).stdout
    additions=[]
    for relative in FRAMEWORK_FILES:
        check=subprocess.run(['git','ls-files','--error-unmatch','--',relative],cwd=upstream,capture_output=True)
        if check.returncode:
            lines=(upstream/relative).read_text(encoding='utf-8').splitlines(keepends=True)
            additions.append(f'diff --git a/{relative} b/{relative}\nnew file mode 100644\n'+
                             ''.join(difflib.unified_diff([],lines,fromfile='/dev/null',tofile='b/'+relative)))
    return tracked+''.join(additions)


def build_package():
    files={}
    def add(relative,source):
        path=PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe bundle path')
        files[str(path)]=Path(source).read_bytes()
    def text(relative,value):
        files[relative]=value.encode('utf-8')
    for folder in ('research','baseline','tests'):
        for path in sorted((ROOT/folder).glob('*.py')):
            add('code/'+str(path.relative_to(ROOT)).replace('\\','/'),path)
    for relative in FRAMEWORK_FILES:
        add('code/upstream/'+relative,ROOT/'upstream'/relative)
    license_path=ROOT/'upstream/LICENSE'
    if license_path.exists():
        add('code/upstream/LICENSE',license_path)
    add('code/requirements-baseline.txt',ROOT/'requirements-baseline.txt')
    add('code/output/paper/iclr2026_conference.sty',ROOT/'output/paper/iclr2026_conference.sty')
    add('code/README.md',ROOT/'research/RELEASE_README.md')
    add('code/research/README.md',ROOT/'research/README.md')
    add('code/research/RELEASE_README.md',ROOT/'research/RELEASE_README.md')
    text('code/config.example.yaml', 'models:\n  defaults:\n    - is_default: true\n      model_client_config:\n'
         '        model_name: ${MODEL_NAME:-deepseek-flash}\n        client_provider: OpenAI\n'
         '        api_base: ${API_BASE}\n        api_key: ${API_KEY}\n')
    for name in ('memory_release_20261016.md','competition_optimization_scorecard.md','research_system_v2_design.md','review_followup_20261016.md'):
        add('docs/'+name,ROOT/'docs'/name)
    for name in ('research_system_code_audit_2026-10-11.md','reference_repo_manifest.json'):
        add('sources/'+name,ROOT/'sources'/name)
    live=ROOT/'output/memory_live_20261016'
    for path in sorted(live.glob('*.json*')):
        add('code/output/memory_live_20261016/'+path.name,path)
    paper=ROOT/'output/memory_paper_20261016'
    allowed_suffixes={'.pdf','.tex','.sty','.json','.jsonl','.md','.txt'}
    for path in sorted(paper.rglob('*')):
        if path.is_file() and path.suffix in allowed_suffixes and path.name!='compile_diagnostics.txt':
            add('paper/'+str(path.relative_to(paper)).replace('\\','/'),path)
    add('resource_report.json',paper/'resources.json')
    text('framework_contribution.patch',framework_patch())
    text('framework_contribution.md', '# Framework contribution\n\nOpt-in versioned source-memory store, '
         'selection policies and Rail in JiuwenSwarm, verified on installed openJiuwen ReActAgent. '
         'Includes earlier baseline rail changes; source audit distinguishes old and new contributions. '
         'No upstream PR or merge is claimed. Apply the patch in a compatible JiuwenSwarm checkout.\n')
    token=ROOT/'submission/memory-20261016-review-token.txt'
    add('Agentic Reviewer/PaperReview-AccessToken.txt',token)
    add('Agentic Reviewer/status.md',ROOT/'submission/memory-20261016-review-status.md')
    add('Agentic Reviewer/review.txt',ROOT/'submission/memory-20261016-review.txt')
    review_path=ROOT/'submission/memory-20261016-review-summary.json'
    add('Agentic Reviewer/review_summary.json',review_path)
    external_review=json.loads(review_path.read_text(encoding='utf-8'))
    proof=ROOT/'submission/memory-20261016-stanford-success.jpg'
    if proof.exists():
        add('Agentic Reviewer/submission_success.jpg',proof)
    pdf_hash=hashlib.sha256((paper/'paper.pdf').read_bytes()).hexdigest()
    status={'local_release':'complete','stanford_submission':'confirmed_success',
            'stanford_score':external_review['score'],'stanford_score_scale':10,
            'paper_evaluation_agent_score':None,'competition_uploaded':False,
            'final_submission_ready':False,'reason':'Stanford review returned; competition point conversion and separate paper-evaluation agent score unverified.',
            'submitted_paper_sha256':pdf_hash,'token_is_private':True,
            'format':'One team root with code, docs, paper, Agentic Reviewer and resource/contribution records.'}
    text('submission_status.json',json.dumps(status,ensure_ascii=False,indent=2)+'\n')
    text('提交说明.md','# 优化版交付说明\n\n本包包含新源码、冻结协议、真实调用、论文、资源报告和贡献 patch。'
         '新稿 Stanford Agentic Reviewer 评分为 4.5/10，原始评审已归档；比赛官网尚未上传本版。'
         '不要将内部审查或旧稿得分作为本版官方评测。请保管 Agentic Reviewer 中的私有 Token。\n')
    # Inspect allowlisted public/code text for common API-secret formats. The
    # review token is intentionally included for the requested competition flow.
    for name,data in files.items():
        if name.endswith(('.py','.yaml','.json','.jsonl','.md','.txt')) and 'AccessToken' not in name:
            if re.search(rb'\bsk-[A-Za-z0-9_-]{16,}',data):
                raise ValueError('Potential API secret in allowlisted file: '+name)
    manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())}
    text('bundle_manifest.json',json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),
         'files':manifest,'paper_sha256':pdf_hash},ensure_ascii=False,indent=2)+'\n')
    staging=ROOT/'submission'/f'{TEAM}-优化版-20261016'
    staging.mkdir(parents=True,exist_ok=True)
    for relative,data in files.items():
        target=staging/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    archive=ROOT/'submission'/f'{TEAM}-优化版-20261016.zip'
    with ZipFile(archive,'w',compression=ZIP_DEFLATED) as zip_file:
        for relative,data in sorted(files.items()):
            zip_file.writestr(TEAM+'/'+relative,data)
    with ZipFile(archive) as zip_file:
        if zip_file.testzip() is not None:
            raise ValueError('Archive CRC verification failed')
        if len(zip_file.namelist())!=len(files):
            raise ValueError('Archive member count mismatch')
        for relative,expected in manifest.items():
            if hashlib.sha256(zip_file.read(TEAM+'/'+relative)).hexdigest()!=expected:
                raise ValueError('Archive digest mismatch')
    return {'archive':str(archive),'files':len(files),'bytes':archive.stat().st_size,
            'paper_sha256':pdf_hash,'external_review':'completed','stanford_score':external_review['score'],'competition_uploaded':False}


if __name__=='__main__':
    print(json.dumps(build_package(),ensure_ascii=False,indent=2))
