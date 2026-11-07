import asyncio
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from zipfile import ZipFile
from research.artifacts import save_json,atomic_write,file_digest
from research.workflow import Workflow,StageResult
from research.workflow.services import LocalServices
from research.workflow.delivery import inspect_pdf,build_release,bind_review,approve_visual
from test_workflow_framework import registry


class DeliveryTests(unittest.TestCase):
    def test_external_figure_cannot_enter_paper(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d)/'project';project.mkdir()
            other=Path(d)/'private.png';other.write_bytes(b'not an image')
            manuscript={'title':'Fixture','sections':[{'heading':'Results','text':'Fixture.'}],
                'figures':[{'section':'Results','path':str(other),'sha256':file_digest(other),'caption':'outside'}]}
            with self.assertRaises(ValueError):LocalServices(project).compile_paper(manuscript)

    def test_real_offline_pdf_previews_bundle_and_review_identity(self):
        async def check(root):
            workflow=Workflow.create(root/'project','Offline delivery integration')
            services=LocalServices(workflow.directory)
            r=registry()
            def export(context):
                result=services.compile_paper(context.inputs['writing'])
                pdf=workflow.directory/next(name for name in result['files'] if name.endswith('paper.pdf'))
                preview=inspect_pdf(pdf,workflow.directory/'workspace/paper/previews')
                self.assertEqual(preview['visual_review'],'pending')
                self.assertTrue((workflow.directory/'workspace/paper/previews/page-001.png').exists())
                package=build_release(workflow.directory,result)
                with ZipFile(workflow.directory/package['archive']) as archive:
                    names=archive.namelist()
                    self.assertTrue(any(n.endswith('/paper/paper.pdf') for n in names))
                    self.assertFalse(any(n.endswith('PaperReview-AccessToken.txt') for n in names))
                    status=json.loads(archive.read('JiuwenSwarmPaperAgent/submission_status.json'))
                    self.assertFalse(status['competition_ready'])
                    # Fresh unpack must resolve the pinned resources without this checkout.
                    archive.extractall(root/'unpacked')
                clean=subprocess.run([sys.executable,'-m','research.workflow.skillpack'],
                    cwd=root/'unpacked/JiuwenSwarmPaperAgent/code',capture_output=True,text=True,timeout=30)
                self.assertEqual(clean.returncode,0,clean.stderr)
                self.assertEqual(json.loads(clean.stdout)['integrity'],'verified')
                token=root/'fixture-token.txt';atomic_write(token,'offline_fixture_token_123456789')
                receipt=root/'receipt.json';save_json(receipt,{'paper_sha256':'wrong'})
                with self.assertRaises(ValueError):bind_review(workflow.directory,pdf,token,receipt)
                approve_visual(workflow.directory,pdf,'Offline fixture layout inspected for integration only')
                save_json(receipt,{'paper_sha256':file_digest(pdf),'status':'offline fixture receipt'})
                bind_review(workflow.directory,pdf,token,receipt)
                second=build_release(workflow.directory,result)
                self.assertNotEqual(package['archive'],second['archive'])
                self.assertTrue(second['external_review_ready'])
                self.assertTrue(second['visual_review_ready'])
                return StageResult(result)
            r.handlers['export']=export
            status=await workflow.run(r)
            self.assertEqual(status['status'],'completed',workflow.state['events'][-1])
        with tempfile.TemporaryDirectory() as d:asyncio.run(check(Path(d)))


if __name__=='__main__':unittest.main()
