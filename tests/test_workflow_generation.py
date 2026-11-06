import json
from pathlib import Path
import tempfile
import unittest
from research.workflow.method_program import Program,MethodError
from research.workflow.data_service import DataService
from research.artifacts import save_json


class GenerationTests(unittest.TestCase):
    def test_generated_lexical_selector_runs_without_eval_or_labels(self):
        code='''def select(question, passages, budget):
    terms = set(question.lower().split())
    ordered = sorted(passages, key=lambda p: -len(terms.intersection(set(p["text"].lower().split()))))
    return [p["id"] for p in ordered[:budget]]
'''
        program=Program(code)
        docs=[{'id':'a','title':'Other','text':'Unrelated','answer':'secret'},
              {'id':'b','title':'Lab','text':'Paris France'}]
        self.assertEqual(program.select('Paris France',docs,1),['b'])
        self.assertEqual(docs[0]['answer'],'secret')
        with self.assertRaises(KeyError):
            Program('def select(question, passages, budget):\n return [passages[0]["answer"]]').select('Q',docs,1)

    def test_imports_file_io_private_attributes_and_loops_are_rejected(self):
        sources=['import os\n',
            'def select(question, passages, budget):\n return open("private")',
            'def select(question, passages, budget):\n return passages.__class__',
            'def select(question, passages, budget):\n while True:\n  return []']
        for source in sources:
            with self.subTest(source=source),self.assertRaises((MethodError,TypeError)):
                Program(source).select('q',[],1)

    def test_bad_ids_and_budget_overflow_rejected(self):
        with self.assertRaises(MethodError):
            Program('def select(question, passages, budget):\n return ["fake"]').select('q',[],1)
        with self.assertRaises(MethodError):
            Program('def select(question, passages, budget):\n return ["a","b"]').select(
                'q',[{'id':x,'title':x,'text':x} for x in ('a','b')],1)

    def test_public_data_preparation_is_deterministic_and_cached(self):
        count=[]
        def fetch(url):
            count.append(url)
            return {'rows':[{'row':{'id':str(i),'question':'Q','answer':'A',
                'context':{'title':['Doc'],'sentences':[['Text']]}}} for i in range(10)]}
        with tempfile.TemporaryDirectory() as directory:
            service=DataService(directory,fetch)
            config={'dataset_provider':'hotpotqa-distractor','dataset_rows':10,'dataset_seed':7}
            dataset=service.prepare(config)
            first=dataset.read_bytes()
            self.assertEqual(service.prepare(config).read_bytes(),first)
            self.assertEqual(len(count),1)
            tasks=json.loads(first)
            self.assertEqual({t['split'] for t in tasks},{'dev','test'})
            self.assertFalse({t['id'] for t in tasks if t['split']=='dev'} & {t['id'] for t in tasks if t['split']=='test'})
            with self.assertRaises(ValueError):service.prepare({**config,'dataset_seed':8})


if __name__=='__main__':unittest.main()
