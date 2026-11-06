from pathlib import Path
import tempfile
import unittest
from research.workflow import Workflow
from workbench.data import Repository
from workbench.workflow import payload


class WorkflowViewTests(unittest.TestCase):
    def test_project_progress_excludes_private_configuration_and_traces(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            Workflow.create(root/'output/framework_demo','Research topic',constraints={'private':'private-marker'})
            value=payload(Repository(root))
            self.assertEqual(value[0]['next_stage'],'literature')
            self.assertNotIn('private-marker',str(value))
            self.assertEqual(len(value[0]['artifacts']),11)


if __name__=='__main__':unittest.main()
