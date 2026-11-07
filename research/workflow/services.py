"""Standard tools for literature, local artifacts, experiment plugins and PDF export."""
import inspect
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Protocol

from research.artifacts import atomic_write, file_digest
from .agents import agent_registry


class ExperimentAdapter(Protocol):
    """Implementations own domain methods; each returns JSON plus actual resources."""
    name: str
    version: str

    async def prepare(self, design: dict, directory: Path) -> dict: ...
    async def pilot(self, design: dict, directory: Path) -> dict: ...
    async def run(self, design: dict, directory: Path) -> dict: ...
    async def analyze(self, design: dict, directory: Path) -> dict: ...


class LocalServices:
    def __init__(self, directory, adapters=None):
        self.directory=Path(directory).resolve()
        self.adapters=adapters or {}

    def path(self, relative):
        path=(self.directory/'workspace'/relative).resolve()
        if not path.is_relative_to(self.directory/'workspace'):
            raise ValueError('Workspace path escapes project')
        return path

    def write_text(self, path, text):
        target=self.path(path)
        if not isinstance(text,str):raise ValueError('Text required')
        atomic_write(target,text)
        return {'path':str(target.relative_to(self.directory)), 'sha256':file_digest(target)}

    def read_text(self, path):
        return {'text':self.path(path).read_text(encoding='utf-8')}

    def search(self, query, limit=6):
        from research.literature import ArxivClient
        if type(limit) is not int or not 1<=limit<=10:raise ValueError('Search limit must be 1..10')
        return ArxivClient(self.directory/'literature_cache').search(query,limit)

    def read_paper(self, paper):
        from research.literature import ArxivClient
        return ArxivClient(self.directory/'literature_cache').read(paper)

    async def experiment(self, operation, adapter, design):
        if adapter not in self.adapters:raise ValueError('Experiment adapter unavailable: '+adapter)
        if operation not in ('prepare','pilot','run','analyze'):raise ValueError('Unknown experiment operation')
        value=getattr(self.adapters[adapter],operation)(design,self.directory/'experiments'/adapter)
        result=await value if inspect.isawaitable(value) else value
        if not isinstance(result,dict):raise ValueError('Adapter must return a JSON object')
        return result

    def capabilities(self):
        return {'adapters':[{'name':name,'version':obj.version} for name,obj in self.adapters.items()],
                'literature':['arxiv.search','arxiv.read'],'documents':['workspace.read','workspace.write','paper.compile']}

    def compile_paper(self, manuscript):
        def tex_escape(text):
            replacements={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#',
                          '_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
            return ''.join(replacements.get(c,c) for c in str(text)).replace('—','--').replace('’',"'")
        if not isinstance(manuscript,dict) or not manuscript.get('sections'):
            raise ValueError('Complete manuscript required')
        paper=self.path('paper');paper.mkdir(parents=True,exist_ok=True)
        root=Path(__file__).resolve().parents[2]
        shutil.copy2(root/'output/paper/iclr2026_conference.sty',paper)
        lines=[r'\documentclass{article}',r'\usepackage{iclr2026_conference,times}',
               r'\usepackage{hyperref,booktabs,graphicx}',r'\iclrfinalcopy',
               r'\title{'+tex_escape(manuscript['title'])+'}',r'\author{Research Agent}',
               r'\begin{document}',r'\maketitle']
        if manuscript.get('draft_status')=='requires_revision':
            lines += [r'\fancyhead[L]{Unapproved model draft -- internal review requested revision}',
                      r'\noindent\textbf{Draft status: requires revision.} This generated manuscript has not passed internal review. See the accompanying review report.']
        elif manuscript.get('draft_status')=='pending_review':
            lines += [r'\fancyhead[L]{Generated draft -- final internal review pending}',
                      r'\noindent\textbf{Draft status: pending review.} This manuscript has not passed a final internal review.']
        refs=manuscript.get('references',[])
        figure_files={}
        for figure in manuscript.get('figures',[]):
            path=(self.directory/figure['path']).resolve()
            if not path.is_relative_to(self.directory) or path.suffix not in ('.png','.pdf') or file_digest(path)!=figure['sha256']:
                raise ValueError('Figure outside project or identity mismatch')
            name='figure-'+str(len(figure_files)+1)+path.suffix
            shutil.copy2(path,paper/name);figure_files[figure['path']]=name
        def prose(text):
            result=tex_escape(text)
            for index,ref in enumerate(refs):
                if isinstance(ref,dict) and ref.get('id'):
                    result=result.replace(tex_escape('['+ref['id']+']'),r'\citep{ref'+str(index)+'}')
            return re.sub(r'\b[a-f0-9]{64}\b',lambda m:r'\nolinkurl{'+m.group(0)+'}',result)
        for section in manuscript['sections']:
            heading,text=section['heading'],section['text']
            if heading.lower()=='abstract':lines += [r'\begin{abstract}',prose(text),r'\end{abstract}']
            else:lines += [r'\section{'+tex_escape(heading)+'}',prose(text)]
            if heading.lower()=='results' and manuscript.get('measured_results'):
                lines += [r'\begin{table}[ht]\centering\small\begin{tabular}{lrrrr}\toprule',
                          r'Method & EM & F1 & Documents & Tokens\\ \midrule']
                for name,row in manuscript['measured_results'].items():
                    lines.append(tex_escape(name)+f" & {row['exact']:.3f} & {row['f1']:.3f} & {row['mean_documents']:.3f} & {row['provider_tokens']}"+r'\\')
                lines += [r'\bottomrule\end{tabular}\caption{Metrics recomputed from saved answers.}\end{table}']
            for table in manuscript.get('tables',[]):
                if table['section'].lower()!=heading.lower():continue
                columns=table['columns'];rows=table['rows']
                if not columns or any(len(row)!=len(columns) for row in rows):raise ValueError('Invalid table dimensions')
                lines += [r'\begin{table}[ht]\centering\scriptsize',r'\begin{tabular}{'+'l'*len(columns)+'}',r'\toprule',
                          ' & '.join(tex_escape(c) for c in columns)+r'\\ \midrule']
                lines += [' & '.join(tex_escape(v) for v in row)+r'\\' for row in rows]
                lines += [r'\bottomrule\end{tabular}',r'\caption{'+tex_escape(table['caption'])+'}',r'\end{table}']
            for figure in manuscript.get('figures',[]):
                if figure['section'].lower()!=heading.lower():continue
                lines += [r'\begin{figure}[ht]\centering',r'\includegraphics[width=\linewidth]{'+figure_files[figure['path']]+'}',
                          r'\caption{'+tex_escape(figure['caption'])+'}',r'\end{figure}']
        if refs:
            lines += [r'\begin{thebibliography}{99}']
            for index,ref in enumerate(refs):
                if isinstance(ref,dict):
                    authors=ref.get('authors') or ['Source']
                    if isinstance(authors,str):authors=[authors]
                    authors=[author.strip() for author in authors]
                    family=authors[0].split(',',1)[0].strip() if ',' in authors[0] else authors[0].split()[-1]
                    authors=[a.split(',',1)[1].strip()+' '+a.split(',',1)[0].strip() if ',' in a else a for a in authors]
                    year=str(ref.get('published') or 'n.d.')[:4]
                    label=tex_escape(family+(' et al.' if len(authors)>1 else ''))
                    text=tex_escape(', '.join(authors)+'. '+str(ref.get('title') or ref['id'])+'. '+year+'.')
                    url=ref.get('url')
                    if isinstance(url,str) and url.startswith('https://') and not any(c in url for c in '{}\\'):
                        text+=r' \url{'+url+'}.'
                else:label,year,text='Source','n.d.',tex_escape(str(ref))
                lines += [r'\bibitem['+label+'('+year+')]{ref'+str(index)+'}'+text]
            lines += [r'\end{thebibliography}']
        lines += [r'\end{document}']
        atomic_write(paper/'paper.tex','\n'.join(lines))
        for _ in range(2):
            result=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-disable-installer','paper.tex'],
                cwd=paper,capture_output=True,text=True,timeout=90)
            atomic_write(paper/'compile_diagnostics.txt',result.stdout+result.stderr)
            if result.returncode:raise ValueError('Paper compilation failed')
        return {'files':{str(p.relative_to(self.directory)):file_digest(p)
                         for p in (paper/'paper.pdf',paper/'paper.tex')},
                'checks':{'compiled':True},'visual_inspection':'required'}


def standard_registry(directory, *, model, adapters=None):
    service=LocalServices(directory,adapters)
    tools={'literature.search':service.search,'literature.read':service.read_paper,
           'workspace.read':service.read_text,'workspace.write':service.write_text,
           'experiment.execute':service.experiment,'capabilities':service.capabilities,
           'paper.compile':service.compile_paper}
    stage_tools={
        'literature':['literature.search','literature.read','workspace.write'],
        'question':['workspace.read'],'design':['capabilities','workspace.read'],
        'implementation':['capabilities','experiment.execute','workspace.write'],
        'pilot':['experiment.execute'],'experiment':['experiment.execute'],
        'analysis':['experiment.execute','workspace.read'],
        'writing':['workspace.read','workspace.write','paper.compile'],
        'review':['workspace.read','capabilities'],
        'export':['workspace.read','paper.compile']}
    return agent_registry(model,tools=tools,stage_tools=stage_tools)
