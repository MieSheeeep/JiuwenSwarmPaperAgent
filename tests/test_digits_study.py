import tempfile
from pathlib import Path
import unittest
import numpy as np
from research.workflow.digits_study import softmax, confidence_scores, selective_metrics, corrupt, forward_logits, DigitsStudy


class DigitsTests(unittest.TestCase):
    def test_scores_and_empty_rejection(self):
        z=np.array([[2.,0.,0.],[0.,2.,0.]])
        p=softmax(z)
        np.testing.assert_allclose(p.sum(axis=1),1)
        scores=confidence_scores(z,2.)
        np.testing.assert_allclose(scores['logit_margin'],[2.,2.])
        value=selective_metrics(z,np.array([0,0]),scores['msp'],threshold=1.1)
        self.assertEqual(value['accepted'],0)
        self.assertEqual(value['coverage'],0)
        self.assertIsNone(value['selective_risk'])
        value=selective_metrics(z,np.array([0,0]),scores['msp'],threshold=0)
        self.assertEqual(value['selective_risk'],.5)

    def test_corruption_is_shared_deterministic_and_bounded(self):
        x=np.full((10,64),.5)
        a=corrupt(x,'gaussian_0.30')
        np.testing.assert_array_equal(a,corrupt(x,'gaussian_0.30'))
        self.assertTrue(np.all((a>=0)&(a<=1)))
        np.testing.assert_array_equal(corrupt(x,'clean'),x)
        self.assertFalse(np.array_equal(a,x))

    def test_saved_weight_forward_matches_sklearn(self):
        from sklearn.neural_network import MLPClassifier
        import warnings
        rng=np.random.default_rng(4);x=rng.normal(size=(50,8));y=np.arange(50)%3
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            model=MLPClassifier(hidden_layer_sizes=(5,),max_iter=3,random_state=1).fit(x,y)
        np.testing.assert_allclose(softmax(forward_logits(model.coefs_,model.intercepts_,x)),model.predict_proba(x),atol=1e-12)

    def test_split_is_disjoint_and_frozen_data_cannot_change(self):
        with tempfile.TemporaryDirectory() as d:
            study=DigitsStudy(Path(d));design=study.prepare()
            parts=[set(design['split'][s]) for s in ('train','validation','test')]
            self.assertEqual([len(p) for p in parts],[1077,360,360])
            self.assertFalse(parts[0]&parts[1] or parts[1]&parts[2] or parts[0]&parts[2])
            with (Path(d)/'data/digits.npz').open('ab') as f:f.write(b'changed')
            with self.assertRaises(ValueError):study.prepare()


if __name__=='__main__':unittest.main()
