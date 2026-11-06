"""Inspect a compiled paper, bind external review, and build an allowlisted bundle."""
import json
from pathlib import Path
import re
import shutil
import uuid
from zipfile import ZipFile,ZIP_DEFLATED
from research.artifacts import atomic_write,file_digest,save_json


def inspect_pdf(pdf, output):
    """Render every page for human inspection; structural checks aren't visual approval."""
    from pypdf import PdfReader
    import pypdfium2 as pdfium
    pdf=Path(pdf);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    reader=PdfReader(pdf)
    pages=[]
    document=pdfium.PdfDocument(str(pdf))
    try:
        for i,page in enumerate(reader.pages):
            text=page.extract_text() or ''
            image=output/f'page-{i+1:03}.png'
            rendered=document[i]
            bitmap=rendered.render(scale=1.0)
            pil=bitmap.to_pil()
            pil.save(image);pil.close();bitmap.close();rendered.close()
            pages.append({'page':i+1,'characters':len(text.strip()),'preview':image.name})
    finally:document.close()
    if not pages or any(p['characters']==0 for p in pages):
        raise ValueError('PDF contains empty or unextractable page')
    report={'pdf_sha256':file_digest(pdf),'pages':pages,'structural_checks_passed':True,
            'visual_review':'pending','scope':'Page rendering and extractable text; scientific and visual quality need review.'}
    previous=output/'inspection.json'
    if previous.exists():
        prior=json.loads(previous.read_text(encoding='utf-8'))
        if prior.get('pdf_sha256')==report['pdf_sha256'] and prior.get('visual_review')=='accepted_by_operator':
            report.update(visual_review=prior['visual_review'],visual_review_note=prior['visual_review_note'])
    save_json(output/'inspection.json',report)
    return report


def bind_review(project,pdf,token_file,receipt):
    project=Path(project).resolve();pdf=Path(pdf).resolve()
    if not pdf.is_relative_to(project):raise ValueError('Review PDF must belong to this project')
    data=json.loads(Path(receipt).read_text(encoding='utf-8'))
    if data.get('paper_sha256')!=file_digest(pdf):
        raise ValueError('Review receipt is for another PDF')
    token=Path(token_file).read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,300}',token):raise ValueError('Invalid external review token format')
    target=project/'external_review';target.mkdir(exist_ok=True)
    atomic_write(target/'PaperReview-AccessToken.txt',token+'\n')
    save_json(target/'receipt.json',data)
    return {'status':'receipt_imported','paper_sha256':file_digest(pdf),
            'verification':'Local identity binding only; service response not independently authenticated.'}


def approve_visual(project,pdf,note):
    if not isinstance(note,str) or not note.strip():raise ValueError('Visual review note required')
    project=Path(project).resolve();pdf=Path(pdf).resolve()
    if not pdf.is_relative_to(project):raise ValueError('PDF must belong to project')
    path=project/'workspace/paper/previews/inspection.json'
    report=json.loads(path.read_text(encoding='utf-8'))
    if report['pdf_sha256']!=file_digest(pdf):raise ValueError('Previewed PDF changed')
    report.update(visual_review='accepted_by_operator',visual_review_note=note)
    save_json(path,report)
    return report


def build_release(project,compiled, *, team='JiuwenSwarmPaperAgent'):
    from .engine import Workflow
    project=Path(project).resolve()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',team):raise ValueError('Simple team directory name required')
    workflow=Workflow(project);workflow.verify()
    sources=workflow.artifact('literature')['payload']['sources']
    paper_names=[name for name in compiled['files'] if name.endswith('paper.pdf')]
    if len(paper_names)!=1:raise ValueError('Exactly one compiled PDF required')
    pdf=(project/paper_names[0]).resolve()
    if not pdf.is_relative_to(project) or file_digest(pdf)!=compiled['files'][paper_names[0]]:
        raise ValueError('Compiled PDF changed')
    package=project/'delivery'/uuid.uuid4().hex/team
    package.mkdir(parents=True,exist_ok=True)
    files={}
    def copy(relative,path):
        path=Path(path)
        dest=package/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,dest);files[relative]=file_digest(dest)
    def write(relative,text):
        dest=package/relative;atomic_write(dest,text);files[relative]=file_digest(dest)
    for name in compiled['files']:
        path=(project/name).resolve()
        if not path.is_relative_to(project) or file_digest(path)!=compiled['files'][name]:raise ValueError('Compilation artifact changed')
        if path.suffix in ('.pdf','.tex','.sty'):copy('paper/'+path.name,path)
    root=Path(__file__).resolve().parents[2]
    copy('paper/iclr2026_conference.sty',root/'output/paper/iclr2026_conference.sty')
    for path in (root/'research/workflow').glob('*.py'):copy('code/research/workflow/'+path.name,path)
    for name in ('__init__.py','artifacts.py','contracts.py','model_gateway.py','agent_invocation.py','literature.py'):
        copy('code/research/'+name,root/'research'/name)
    for path in (root/'baseline').glob('*.py'):copy('code/baseline/'+path.name,path)
    copy('code/requirements-baseline.txt',root/'requirements-baseline.txt')
    copy('code/output/paper/iclr2026_conference.sty',root/'output/paper/iclr2026_conference.sty')
    copy('docs/architecture.md',root/'docs/research_framework.md')
    write('docs/module_call.md','openJiuwen ReActAgent + JiuwenSwarm FrozenMessagesRail; durable ModelGateway. '
          'Source service: arXiv. Generated method: bounded AST interpreter. No unrestricted Python execution.\n')
    write('docs/innovation.md','Engineering contribution: source-linked stages, generated bounded document selectors, '
          'frozen protocol, separate development and held-out execution, claim-bound paper, review routing. '
          'Scientific novelty requires evaluation; no novelty certification is made.\n')
    write('framework_contribution.md','Existing JiuwenSwarm Rail extensions are supplied as a patch; no merged upstream PR is claimed.\n')
    patch=root/'output/framework_contribution.patch'
    if patch.exists():copy('framework_contribution.patch',patch)
    rail=root/'upstream/jiuwenswarm/agents/harness/common/rails/frozen_messages_rail.py'
    if rail.exists():copy('code/upstream/jiuwenswarm/agents/harness/common/rails/frozen_messages_rail.py',rail)
    license_file=root/'upstream/LICENSE'
    if license_file.exists():copy('code/upstream/LICENSE',license_file)
    for stage in ('topic','question','design','implementation','analysis','writing','review'):
        row=workflow.state['stages'][stage]
        copy('provenance/'+stage+'.json',project/row['artifact'])
    data_manifest=project/'data/manifest.json'
    if data_manifest.exists():copy('provenance/data_manifest.json',data_manifest)
    dataset=project/'data/tasks.json'
    if dataset.exists():copy('provenance/dataset.json',dataset)
    for path in (project/'experiments').rglob('*_results.json'):
        copy('provenance/'+str(path.relative_to(project)).replace('\\','/'),path)
    previews=project/'workspace/paper/previews'
    inspection=previews/'inspection.json'
    visual_ready=False
    if inspection.exists():
        report=json.loads(inspection.read_text(encoding='utf-8'))
        if report['pdf_sha256']!=file_digest(pdf):raise ValueError('PDF inspection identity mismatch')
        visual_ready=report['visual_review']=='accepted_by_operator'
        copy('paper/inspection.json',inspection)
        for path in previews.glob('page-*.png'):copy('paper/previews/'+path.name,path)
    ledger=project/'model_ledger/calls.jsonl'
    if ledger.exists():
        from research.model_gateway import read_jsonl,valid_usage
        rows=read_jsonl(ledger)
        requests=read_jsonl(project/'model_ledger/requests.jsonl')
        if ({r['id'] for r in requests}!={r['id'] for r in rows} or
            any(not valid_usage(row.get('usage')) for row in rows)):
            raise ValueError('Unknown provider usage prevents release')
        write('provenance/call_usage.json',json.dumps([{k:r.get(k) for k in ('id','tag','model','usage','status')} for r in rows],indent=2))
    resources=workflow.state['usage']
    write('resource_report.md',f"# Resources\n\nCalls: {resources['calls']}\n\nKnown provider tokens: {resources['tokens']}\n")
    implementation=workflow.artifact('implementation')['payload']
    if implementation.get('source_path'):copy('code/generated_method.py',project/implementation['source_path'])
    receipt=project/'external_review/receipt.json'
    review_ready=False
    if receipt.exists():
        review=json.loads(receipt.read_text(encoding='utf-8'))
        if review.get('paper_sha256')!=file_digest(pdf):raise ValueError('External review PDF identity mismatch')
        token=project/'external_review/PaperReview-AccessToken.txt'
        if not token.exists():raise ValueError('External review token missing')
        copy('AgenticReviewer/PaperReview-AccessToken.txt',token)
        copy('AgenticReviewer/receipt.json',receipt);review_ready=True
    write('submission_status.json',json.dumps({'paper_sha256':file_digest(pdf),
        'external_review_ready':review_ready,'visual_review_ready':visual_ready,
        'submission_materials_complete':review_ready and visual_ready,
        'competition_ready':False,'official_submission_confirmed':False,
        'note':'Local structural checklist only; official eligibility/quality remain externally assessed.'},indent=2))
    write('README.md','# Reproduction\n\nInstall code/requirements-baseline.txt. Apply framework_contribution.patch '
          'to the pinned upstream checkout. Provide your own model configuration. '
          'Inspect provenance/design.json and data_manifest.json to reconstruct the frozen data split. '
          'Initialize research.workflow and explicitly enable model calls to reproduce. Private API keys are not bundled.\n')
    save_json(package/'manifest.json',{'files':files,'paper_sha256':file_digest(pdf),'sources':sources,
                                     'external_review_ready':review_ready})
    archive=package.parent/(team+'.zip')
    # Only current allowlisted files enter the archive; no stale or private directory traversal.
    with ZipFile(archive,'w',ZIP_DEFLATED) as zipfile:
        for relative in [*files,'manifest.json']:
            zipfile.write(package/relative,team+'/'+relative)
    return {'archive':str(archive.relative_to(project)),'sha256':file_digest(archive),
            'external_review_ready':review_ready,'visual_review_ready':visual_ready,'file_count':len(files)+1}
