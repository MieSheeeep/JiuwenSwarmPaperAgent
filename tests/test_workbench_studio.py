import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import time

from workbench.data import Repository
from workbench.studio import Studio, Conflict


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run = self.root/'output/memory_live_test'
        self.paper = self.root/'output/memory_paper_test'
        self.run.mkdir(parents=True); self.paper.mkdir()
        (self.run/'manifest.json').write_text(json.dumps({'schema_version': 2}))
        self.sections = {k: 'Original English paragraph.' for k in ('abstract','introduction','related_work','methods','discussion','conclusion')}
        (self.paper/'reviewed_sections.json').write_text(json.dumps(self.sections))
        tex = '\\documentclass{article}\n\\begin{document}\n\\begin{abstract}\nOriginal English paragraph.\n\\end{abstract}\n'
        for k in ('introduction','related_work','methods','discussion','conclusion'):
            tex += '\\section{'+k.replace('_',' ').title()+'}\nOriginal English paragraph.\n'
            if k == 'methods': tex += '\\subsection{Frozen Protocol}\nFrozen evidence.\n\\section{Measured Results}\nFrozen measurements.\n'
        tex += '\\section{Limitations and Reproducibility Disclosure}\nOriginal disclosure.\n\\end{document}'
        (self.paper/'paper.tex').write_text(tex)
        self.studio = Studio(Repository(self.root))

    def tearDown(self): self.tmp.cleanup()

    def test_save_is_immutable_and_preserves_source(self):
        source = (self.paper/'paper.tex').read_bytes()
        draft = self.studio.save(self.run.name, self.sections, None)
        self.assertEqual(self.studio.list(self.run.name)['revisions'][0]['id'], draft['id'])
        self.assertEqual((self.paper/'paper.tex').read_bytes(), source)
        with self.assertRaises(Conflict): self.studio.save(self.run.name, self.sections, None)

    def test_untrusted_text_is_escaped_and_measurements_preserved(self):
        self.sections['methods'] = r'Explaining \input{secret} with 50% budget.'
        revision = self.studio.save(self.run.name, self.sections, None)
        tex = self.studio.asset(self.run.name, revision['id'], 'latex').read_text()
        self.assertNotIn(r'Explaining \input{secret}', tex)
        self.assertIn('Frozen measurements.', tex)
        self.assertIn('UNREVIEWED WORKBENCH REVISION', tex)

    def test_rejects_invalid_content_and_paths(self):
        with self.assertRaises(ValueError): self.studio.save(self.run.name, {'abstract': ''}, None)
        with self.assertRaises(KeyError): self.studio.asset(self.run.name, '../private', 'latex')
        revision = self.studio.save(self.run.name, self.sections, None)
        with self.assertRaises(KeyError): self.studio.asset(self.run.name, revision['id'], 'token')
        with self.assertRaises(ValueError): self.studio.start(self.run.name, revision['id'], 'unknown')

    def test_changed_section_file_is_rejected(self):
        revision = self.studio.save(self.run.name, self.sections, None)
        path = self.root/'output/workbench'/self.run.name/'revisions'/revision['id']/'sections.json'
        path.write_text('{}')
        with self.assertRaises(ValueError): self.studio.get(self.run.name,revision['id'])

    def test_failed_figure_job_is_explicit_and_unlocks_next_job(self):
        revision = self.studio.save(self.run.name, self.sections, None)
        with patch('workbench.studio.render_figures', side_effect=ValueError('Test figure failure')):
            job = self.studio.start(self.run.name,revision['id'],'figures')
            deadline=time.monotonic()+5
            while self.studio.active and time.monotonic()<deadline: time.sleep(.01)
        result=self.studio.job(self.run.name,revision['id'],job['id'])
        self.assertEqual(result['status'],'failed')
        self.assertFalse(self.studio.active)
        self.assertNotIn('paper.pdf',result['files'])

    def test_final_metadata_failure_always_releases_guard(self):
        revision=self.studio.save(self.run.name,self.sections,None)
        folder=self.root/'output/workbench'/self.run.name/'revisions'/revision['id']/'jobs'/'j_test'
        folder.mkdir(parents=True)
        state={'status':'queued','kind':'figures','profile':'color','log':[],'files':{}}
        self.studio.active=True
        with patch('workbench.studio.render_figures',return_value={}), patch('workbench.studio.write_json',side_effect=[None,OSError('disk error')]):
            self.studio._execute(self.run.name,folder.parent.parent,folder,state)
        self.assertFalse(self.studio.active)
        self.assertEqual(state['status'],'failed')

    def test_mutations_require_local_token_and_preserve_conflict_status(self):
        from workbench.server import make_server
        server=make_server(Repository(self.root),port=0)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        payload=json.dumps({'sections':self.sections,'base_revision':None}).encode()
        url=base+'/api/runs/'+self.run.name+'/studio'
        try:
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(url,data=payload,headers={'Content-Type':'application/json'}))
            self.assertEqual(caught.exception.code,403)
            with urlopen(base+'/api/session') as response: token=json.load(response)['token']
            headers={'Content-Type':'application/json','X-Workbench-Token':token}
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(url,data=payload,headers={**headers,'Origin':'https://untrusted.example'}))
            self.assertEqual(caught.exception.code,403)
            with urlopen(Request(url,data=payload,headers=headers)) as response:
                self.assertEqual(response.status,201)
            with self.assertRaises(HTTPError) as caught: urlopen(Request(url,data=payload,headers=headers))
            self.assertEqual(caught.exception.code,409)
        finally: server.shutdown();server.server_close();thread.join()


if __name__ == '__main__': unittest.main()
