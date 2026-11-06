"""Standard tools for literature, local artifacts, experiment plugins and PDF export."""
import inspect
import json
from pathlib import Path
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
        from research.memory_paper import tex_escape
        if not isinstance(manuscript,dict) or not manuscript.get('sections'):
            raise ValueError('Complete manuscript required')
        paper=self.path('paper');paper.mkdir(parents=True,exist_ok=True)
        root=Path(__file__).resolve().parents[2]
        shutil.copy2(root/'output/paper/iclr2026_conference.sty',paper)
        lines=[r'\documentclass{article}',r'\usepackage{iclr2026_conference,times}',
               r'\usepackage{hyperref,booktabs,graphicx}',r'\iclrfinalcopy',
               r'\title{'+tex_escape(manuscript['title'])+'}',r'\author{Research Agent}',
               r'\begin{document}',r'\maketitle']
        for section in manuscript['sections']:
            heading,text=section['heading'],section['text']
            if heading.lower()=='abstract':lines += [r'\begin{abstract}',tex_escape(text),r'\end{abstract}']
            else:lines += [r'\section{'+tex_escape(heading)+'}',tex_escape(text)]
        refs=manuscript.get('references',[])
        if refs:
            lines += [r'\section*{References}']
            for ref in refs:
                lines += [tex_escape(json.dumps(ref,ensure_ascii=True) if isinstance(ref,dict) else str(ref))+r'\par']
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
