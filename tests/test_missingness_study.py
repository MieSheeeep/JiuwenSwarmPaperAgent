import itertools
import tempfile
from pathlib import Path
import unittest
import numpy as np
from research.workflow.missingness_study import expected_losses,risk_coefficients,worst_quadratic,select_policy,predict_pool


class MissingnessTests(unittest.TestCase):
    def test_exact_risk_matches_mask_enumeration_with_indicators(self):
        x=np.array([[1.,2.],[-1.,.5]])
        y=np.array([.3,-.7]);a=np.array([.4,-.2]);fill=np.array([.1,.8]);c=np.array([.6,-.3]);b=.2
        for p in (0.,.1,.5,1.):
            explicit=np.zeros(len(y))
            for mask in itertools.product((0,1),repeat=2):
                mask=np.array(mask);prob=np.prod(np.where(mask,p,1-p))
                prediction=b+np.where(mask,fill,x)@a+mask@c
                explicit+=prob*(prediction-y)**2
            np.testing.assert_allclose(expected_losses(x,y,a,b,fill,c,p),explicit,atol=1e-12)

    def test_risk_coefficients_and_interior_maximum(self):
        # d=(1,-1), e=0 => risk 2p(1-p), concave with max at p=.5.
        x=np.zeros((1,2));y=np.zeros(1);a=np.zeros(2);fill=np.zeros(2);c=np.array([1.,-1.])
        coefficients=risk_coefficients(x,y,a,0.,fill,c)
        np.testing.assert_allclose(coefficients,[-2.,2.,0.])
        value,where=worst_quadratic(coefficients,.1,.9)
        self.assertAlmostEqual(value,.5);self.assertAlmostEqual(where,.5)
        self.assertGreater(value,.18)

    def test_selectors_only_use_validation_risks(self):
        coefficients=np.array([[0.,1.,0.],[0.,0.,.2]])
        self.assertEqual(select_policy('clean',coefficients,{}),0)
        self.assertEqual(select_policy('analytic_minimax',coefficients,{}),1)
        self.assertEqual(select_policy('known_p',coefficients,{},p=.1),0)
        self.assertEqual(select_policy('known_p',coefficients,{},p=.5),1)

    def test_batched_affine_prediction_matches_explicit_fill_and_indicator(self):
        rng=np.random.default_rng(3);x=rng.normal(size=(20,3));mask=rng.random(x.shape)<.4
        model={'a':rng.normal(size=(3,4)),'b':rng.normal(size=4),
               'c':rng.normal(size=(3,4)),'fill':rng.normal(size=(3,4))}
        result=predict_pool(x,mask,model)
        for i in range(4):
            expected=model['b'][i]+np.where(mask,model['fill'][:,i],x)@model['a'][:,i]+mask@model['c'][:,i]
            np.testing.assert_allclose(result[:,i],expected,atol=1e-12)

    def test_saved_prediction_tampering_is_rejected(self):
        from research.workflow import missingness_study
        from research.artifacts import digest,file_digest
        with tempfile.TemporaryDirectory() as d:
            study=missingness_study.MissingnessStudy(d)
            study.prepare=lambda:{'dataset':'fixture'}
            design={'dataset':'fixture','code_sha256':file_digest(Path(missingness_study.__file__))}
            path=Path(d)/'prediction.npz';path.write_bytes(b'fixture')
            value={'design_sha256':digest(design),'rows':[],'rows_sha256':digest([]),'files':{'prediction.npz':file_digest(path)}}
            study.verify(value,design)
            path.write_bytes(b'modified')
            with self.assertRaises(ValueError):study.verify(value,design)


if __name__=='__main__':unittest.main()
