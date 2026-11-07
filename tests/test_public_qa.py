import copy
import unittest
from research.public_qa import rank, score


class PublicQATests(unittest.TestCase):
    def test_rank_is_independent_of_labels_and_does_not_mutate_documents(self):
        documents = [{'id':'p0','title':'Other','text':'unrelated words'},
                     {'id':'p1','title':'Paris','text':'Paris is the capital of France.'}]
        before = copy.deepcopy(documents)
        self.assertEqual(rank('What is the capital of France?', documents)[0]['id'], 'p1')
        self.assertEqual(documents, before)
        # The selection API accepts only question and documents, never gold labels.
        self.assertEqual(len(rank('France', documents)), 2)

    def test_answer_metric_yes_no_and_partial_overlap(self):
        self.assertEqual(score('The Eiffel Tower', 'Eiffel Tower'), (1.,1.))
        self.assertEqual(score('yes', 'no'), (0.,0.))
        em,f1=score('New York', 'New York City')
        self.assertEqual(em,0.)
        self.assertAlmostEqual(f1,.8)


if __name__=='__main__': unittest.main()
