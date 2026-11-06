"""Immutable English prose revisions and bounded local figure/PDF build jobs."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from threading import RLock, Thread
import time
import uuid

from research.memory_paper import SECTIONS, REFERENCES, tex_escape, tex_prose
from .figure_skills import SKILLS, PROFILES, render_figures


class Conflict(Exception): pass


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temp.replace(path)


class Studio:
    def __init__(self, repository):
        self.repo = repository
        self.lock = RLock()
        self.active = False
        self.instance = uuid.uuid4().hex
        self.states = {}

    def _base(self, run_id):
        self.repo._run(run_id)
        return self.repo._safe(self.repo.root/'output/workbench'/run_id/'revisions')

    def _revision(self, run_id, revision_id):
        if not re.fullmatch(r'r_[a-f0-9]{20}', revision_id): raise KeyError('Unknown revision')
        path = self.repo._safe(self._base(run_id)/revision_id)
        if not (path/'revision.json').is_file(): raise KeyError('Unknown revision')
        return path

    def list(self, run_id):
        revisions = []
        for path in self._base(run_id).glob('r_*/revision.json'):
            row = self.repo._json(path, {})
            revisions.append(row)
        revisions.sort(key=lambda r: (r['created_at'], r['id']), reverse=True)
        _, paper, _, _ = self.repo._paths(run_id)
        original = self.repo._json(paper/'reviewed_sections.json', {})
        return {'revisions': revisions, 'latest': revisions[0]['id'] if revisions else None,
                'original_sections': original, 'skills': SKILLS,
                'original_pdf_sha256': sha(paper/'paper.pdf') if (paper/'paper.pdf').is_file() else None}

    def get(self, run_id, revision_id):
        path = self._revision(run_id, revision_id)
        result = self.repo._json(path/'revision.json', {})
        if sha(self.repo._safe(path/'sections.json')) != result['sections_sha256']:
            raise ValueError('Revision sections changed')
        result['sections'] = self.repo._json(path/'sections.json', {})
        result['latex'] = self.asset(run_id, revision_id, 'latex').read_text(encoding='utf-8')
        jobs = [self._job(path, p.name) for p in (path/'jobs').glob('j_*') if (p/'job.json').is_file()]
        result['jobs'] = sorted(jobs, key=lambda r:r['created_at'], reverse=True)
        return result

    def save(self, run_id, sections, base_revision):
        if not isinstance(sections, dict) or set(sections) != set(SECTIONS): raise ValueError('Exactly six manuscript sections required')
        if any(not isinstance(v,str) or not v.strip() or len(v)>24000 for v in sections.values()): raise ValueError('Each section must contain 1–24000 characters')
        if any(re.search(r'[\u3400-\u9fff\x00-\x08]',v) for v in sections.values()): raise ValueError('Academic sections must be English plain text')
        keys = {r['key'] for r in REFERENCES}
        for text in sections.values():
            citations = [k.strip() for c in re.findall(r'\[([a-z_,;\s]+)\]',text) for k in re.split('[,;]',c)]
            if any(key not in keys for key in citations): raise ValueError('Use only registered citation keys')
        with self.lock:
            state = self.list(run_id)
            if state['latest'] != base_revision: raise Conflict('A newer revision exists; reload before saving')
            _, paper, _, _ = self.repo._paths(run_id)
            original_tex = self.repo._safe(paper/'paper.tex').read_text(encoding='utf-8')
            tex = original_tex
            for key, value in sections.items():
                content = tex_prose(value)
                if key == 'abstract':
                    pattern = r'(\\begin\{abstract\}\s*).*?(\\end\{abstract\})'
                else:
                    title = re.escape(key.replace('_',' ').title())
                    pattern = r'(\\section\{'+title+r'\}\s*).*?(?=\\(?:subsection\{|section\{|begin\{thebibliography\}))'
                tex, count = re.subn(pattern, lambda m: m[1]+content+'\n'+(m[2] if key=='abstract' else ''),tex,flags=re.S)
                if count != 1: raise ValueError('Manuscript template section not found: '+key)
            banner = r'\par\noindent{\small\textbf{UNREVIEWED WORKBENCH REVISION. Original external score does not apply.}}\par'
            marker = r'\maketitle' if r'\maketitle' in tex else r'\begin{document}'
            tex = tex.replace(marker,marker+'\n'+banner,1)
            revision_id = 'r_'+uuid.uuid4().hex[:20]
            base = self._base(run_id); base.mkdir(parents=True, exist_ok=True)
            destination = self.repo._safe(base/revision_id); destination.mkdir()
            (destination/'paper.tex').write_text(tex, encoding='utf-8')
            write_json(destination/'sections.json',sections)
            for filename in ('iclr2026_conference.sty',):
                source = self.repo._safe(paper/filename)
                if source.is_file(): shutil.copy2(source,destination/filename)
            parent_sections = self.get(run_id,base_revision)['sections'] if base_revision else state['original_sections']
            changes = {key:{'before':parent_sections.get(key,''),'after':sections[key],
                            'diff':'\n'.join(difflib.unified_diff(parent_sections.get(key,'').splitlines(),sections[key].splitlines(),fromfile='previous',tofile='revision',lineterm=''))}
                       for key in SECTIONS if parent_sections.get(key,'') != sections[key]}
            metadata = {'id':revision_id,'created_at':datetime.now(timezone.utc).isoformat(), 'parent':base_revision,
                        'original_pdf_sha256':state['original_pdf_sha256'],'source_tex_sha256':sha(paper/'paper.tex'),
                        'latex_sha256':sha(destination/'paper.tex'),'sections_sha256':sha(destination/'sections.json'),
                        'review_status':'unreviewed','changes':changes,
                        'evidence_sha256':{name:sha(self.repo._safe(self.repo._run(run_id)/name)) for name in
                                           ('manifest.json','summary.json','dataset.json','results.jsonl') if (self.repo._run(run_id)/name).is_file()},
                        'checks':['English plain-text sections; TeX escaped','Measured tables preserved from original template',
                                  'Edited scientific claims require review; no score inherited']}
            write_json(destination/'revision.json', metadata)
            return metadata

    def asset(self, run_id, revision_id, asset):
        if asset != 'latex': raise KeyError('Unknown revision asset')
        path = self._revision(run_id,revision_id)
        metadata = self.repo._json(path/'revision.json',{})
        file = self.repo._safe(path/'paper.tex')
        if sha(file) != metadata['latex_sha256']: raise ValueError('Revision source changed')
        return file

    def _job(self, revision, job_id):
        if not re.fullmatch(r'j_[a-f0-9]{20}', job_id): raise KeyError('Unknown job')
        path = self.repo._safe(revision/'jobs'/job_id/'job.json')
        if not path.is_file(): raise KeyError('Unknown job')
        row = json.loads(json.dumps(self.states[str(path.parent)])) if str(path.parent) in self.states else self.repo._json(path,{})
        if row['status'] in ('queued','running') and row.get('instance') != self.instance:
            row['status']='interrupted'; row['error']='Server restarted; start a new local build.'
        return row

    def job(self, run_id, revision_id, job_id): return self._job(self._revision(run_id,revision_id),job_id)

    def job_asset(self, run_id, revision_id, job_id, filename):
        allowed = {'paper.pdf','paper.tex','results.pdf','results.png','results.svg','architecture.pdf','architecture.svg','architecture.png','architecture.json','figure_manifest.json','compile.log'}
        if filename not in allowed: raise KeyError('Unknown job asset')
        revision = self._revision(run_id,revision_id)
        job = self._job(revision,job_id)
        if filename not in job.get('files',{}): raise KeyError('Job artifact unavailable')
        path = self.repo._safe(revision/'jobs'/job_id/filename)
        if sha(path) != job['files'][filename]: raise ValueError('Job artifact changed')
        return path

    def start(self, run_id, revision_id, kind, profile='color'):
        if kind not in ('figures','compile') or profile not in PROFILES: raise ValueError('Unknown local job or figure profile')
        revision = self._revision(run_id,revision_id)
        self.asset(run_id,revision_id,'latex')
        with self.lock:
            if self.active: raise Conflict('A local build is running; wait for it to finish')
            self.active = True
            try:
                job_id = 'j_'+uuid.uuid4().hex[:20]
                folder = self.repo._safe(revision/'jobs'/job_id); folder.mkdir(parents=True)
                state = {'id':job_id,'revision_id':revision_id,'kind':kind,'profile':profile,'status':'queued',
                         'created_at':datetime.now(timezone.utc).isoformat(),'instance':self.instance,'files':{},'log':[]}
                write_json(folder/'job.json', state)
                self.states[str(folder)] = state
                Thread(target=self._execute,args=(run_id,revision,folder,state),daemon=True).start()
                return state
            except Exception:
                self.active=False
                raise

    def _execute(self,run_id,revision,folder,state):
        try:
            state['status']='running';state['log'].append('Reading pinned evidence and rendering registered local figure skills.')
            write_json(folder/'job.json',state)
            metadata = self.repo._json(revision/'revision.json',{})
            for name, expected in metadata['evidence_sha256'].items():
                if sha(self.repo._safe(self.repo._run(run_id)/name)) != expected: raise ValueError('Evidence changed since revision save')
            summary = self.repo._json(self.repo._run(run_id)/'summary.json',{})
            render_figures(summary,folder,state['profile'])
            state['log'].append('Generated results and architecture: PDF, SVG, PNG; recorded figure manifest.')
            if state['kind']=='compile':
                self.asset(run_id,revision.name,'latex')
                shutil.copy2(revision/'paper.tex',folder/'paper.tex')
                style = self.repo._safe(revision/'iclr2026_conference.sty')
                if style.is_file(): shutil.copy2(style,folder/style.name)
                compiler = shutil.which('pdflatex')
                if not compiler: raise ValueError('pdflatex is not installed; generated source and figures retained')
                deadline=time.monotonic()+90; logs=[]
                for index in range(2):
                    result = subprocess.run([compiler,'-interaction=nonstopmode','-halt-on-error','-no-shell-escape','-disable-installer','paper.tex'],cwd=folder,
                                             capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=max(1,deadline-time.monotonic()))
                    logs.append(result.stdout+result.stderr)
                    (folder/'compile.log').write_text('\n'.join(logs),encoding='utf-8')
                    if result.returncode: raise ValueError('PDF compilation failed; inspect compile.log')
                    state['log'].append(f'LaTeX pass {index+1} completed.')
            state['status']='succeeded';state['log'].append('Local job complete. New draft has no external review score.')
        except Exception as error:
            state['status']='failed';state['error']=str(error);state['log'].append(str(error))
        finally:
            try:
                allowed = ('paper.pdf','paper.tex','results.pdf','results.svg','results.png','architecture.pdf','architecture.svg','architecture.png','architecture.json','figure_manifest.json','compile.log')
                state['files']={name:sha(folder/name) for name in allowed if (folder/name).is_file() and (name!='paper.pdf' or state['status']=='succeeded')}
                write_json(folder/'job.json',state)
            except Exception:
                state['status']='failed';state['error']='Unable to persist build artifacts; check local disk.'
                state['files'].pop('paper.pdf',None)
            finally:
                with self.lock: self.active=False
