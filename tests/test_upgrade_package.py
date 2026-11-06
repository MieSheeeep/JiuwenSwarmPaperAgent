import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from research.package_upgrade import build_package


class UpgradePackageTests(unittest.TestCase):
    def test_only_reviewed_build_identity_and_allowlisted_public_files(self):
        with TemporaryDirectory() as d:
            root=Path(d);run=root/'output/review_upgrade_20261106';(run/'paper').mkdir(parents=True)
            pdf=b'fixture pdf';(run/'paper/paper.pdf').write_bytes(pdf)
            (run/'summary.json').write_text('{"evaluation_complete":true}')
            (run/'analysis.json').write_text('{}')
            status={'status':'succeeded','paper_sha256':hashlib.sha256(pdf).hexdigest(),
                    'source_analysis_sha256':hashlib.sha256((run/'analysis.json').read_bytes()).hexdigest(),
                    'source_summary_sha256':hashlib.sha256((run/'summary.json').read_bytes()).hexdigest()}
            (run/'paper/writing_status.json').write_text(json.dumps(status))
            (run/'config.local.yaml').write_text('PRIVATE_CONFIG_SENTINEL')
            (run/'review-token.txt').write_text('PRIVATE_TOKEN_SENTINEL')
            result=build_package(root)
            with ZipFile(result['archive']) as z:
                self.assertIn('空梦轮年/paper/paper.pdf',z.namelist())
                self.assertTrue(all('config.local' not in n and 'review-token' not in n for n in z.namelist()))
                status=json.loads(z.read('空梦轮年/submission_status.json'))
                self.assertIsNone(status['stanford_score'])
                self.assertFalse(status['final_submission_ready'])
            (run/'summary.json').write_text('{"evaluation_complete":false}')
            with self.assertRaises(ValueError):build_package(root)
            (run/'summary.json').write_text('{"evaluation_complete":true}')
            (run/'analysis.json').write_text('{"changed":true}')
            with self.assertRaises(ValueError):build_package(root)
            (run/'analysis.json').write_text('{}')
            (run/'paper/paper.pdf').write_bytes(b'tampered')
            with self.assertRaises(ValueError):build_package(root)
