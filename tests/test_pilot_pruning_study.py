"""Numerical and provenance tests; no final benchmark fitting."""
import importlib
from itertools import product
import numpy as np
import pytest


def core():
    try:
        return importlib.import_module('research.workflow.pilot_pruning_study')
    except ModuleNotFoundError:
        pytest.fail('Pilot pruning study implementation is missing')


def test_tiny_enumeration_matches_ordered_sequences():
    m=core(); counts=m.count_grid(3)
    weights=m.probabilities(counts,.1,.3)
    brute={tuple(c):0. for c in counts}
    for sequence in product(range(3),repeat=3):
        c=tuple(sequence.count(k) for k in range(3))
        brute[c]+=float(np.prod(np.array([.1,.7,.2])[list(sequence)]))
    assert len(counts)==10
    assert np.allclose(weights,[brute[tuple(c)] for c in counts])
    assert weights.sum()==pytest.approx(1.)


def test_zero_discordance_exact_retains_uncertainty():
    m=core(); c=np.array([[0,16,0]])
    lo,hi=m.intervals(c,'exact_joint')
    assert lo[0]<0<hi[0]
    nlo,nhi=m.intervals(c,'paired_normal')
    assert nlo[0]==nhi[0]==0


def test_joint_bound_fixed_look_coverage():
    m=core()
    for n in (1,4,16):
        c=m.count_grid(n); lo,hi=m.intervals(c,'exact_joint')
        for q in (.05,.4,1.):
            for g in (-q,0,q):
                p=m.probabilities(c,g,q)
                assert p[(lo<=g)&(hi>=g)].sum()>=.95-1e-12


def test_decision_strict_boundaries_and_legacy_gap():
    m=core()
    lo=np.array([.02,.021,-.1,.001]); hi=np.array([.1,.1,.019,.03]); gain=np.array([.04,.04,0,.01])
    assert m.decide(lo,hi,gain,.02,'tri_state').tolist()==['defer','go','no_go','defer']
    assert m.decide(lo,hi,gain,.02,'delta_binary').tolist()==['no_go','go','no_go','no_go']
    assert m.decide(lo,hi,gain,.02,'legacy_binary').tolist()==['go','go','no_go','no_go']


def test_integrated_rows_and_aggregate_random_deferral():
    m=core(); rows=[]
    for g in (-.04,.08):rows.extend(m.integrate_case(16,g,.2,.02))
    summary=m.mixture_summary(rows,'equal')
    for interval in ('paired_normal','exact_joint'):
        group={r['policy']:r for r in summary if r['interval']==interval}
        rate=group['tri_state']['p_defer']; binary=group['legacy_binary']; matched=group['matched_random_legacy_binary']
        assert matched['p_defer']==pytest.approx(rate)
        assert matched['p_go']==pytest.approx((1-rate)*binary['p_go'])
        assert matched['false_prune_probability']==pytest.approx((1-rate)*binary['false_prune_probability'])
    assert all(abs(r['p_go']+r['p_no_go']+r['p_defer']-1)<1e-10 for r in rows+summary)


def test_saved_prediction_tampering_detected(tmp_path):
    m=core(); study=m.PilotPruningStudy(tmp_path)
    target=tmp_path/'predictions.npz'; np.savez(target,y=[0,1],pred=[0,1])
    frozen=study.freeze_files([target])
    study.verify_files(frozen)
    target.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):study.verify_files(frozen)


def test_source_freeze_is_required(tmp_path):
    study=core().PilotPruningStudy(tmp_path)
    with pytest.raises(ValueError,match='freeze'):study._check({})

def test_scalar_decisions_and_invalid_probabilities():
    m=core()
    assert m.decide(.02,.1,.03,.02,'tri_state').item()=='defer'
    with pytest.raises(ValueError):m.probabilities(m.count_grid(2),.3,.1)


def test_prediction_cache_binds_input_data(tmp_path):
    m=core();study=m.PilotPruningStudy(tmp_path)
    iris=m.load_iris()
    study._predictions('health',iris.data,iris.target,m.SEEDS[:1])
    changed=iris.data.copy();changed[0,0]+=.1
    with pytest.raises(ValueError,match='input'):study._predictions('health',changed,iris.target,m.SEEDS[:1])

def test_audit_detects_results_tampering(tmp_path):
    m=core();study=m.PilotPruningStudy(tmp_path);study.root.mkdir(parents=True)
    rows=m.integrate_case(2,0,.2,.02)
    m.save_json(study.root/'results.json',{'rows':rows,'rows_sha256':m.digest(rows)})
    assert study.audit({})['passed']
    saved=__import__('json').loads((study.root/'results.json').read_text())
    saved['rows'][0]['p_go']=.99;m.save_json(study.root/'results.json',saved)
    assert not study.audit({})['passed']

def test_audit_rejects_rehashed_incomplete_registered_grid(tmp_path):
    m=core();study=m.PilotPruningStudy(tmp_path);study.root.mkdir(parents=True)
    rows=m.integrate_case(2,0,.2,.02)
    m.save_json(study.root/'results.json',{'rows':rows,'rows_sha256':m.digest(rows)})
    study._check=lambda protocol: {'datasets':[{'name':n} for n in ('breast_cancer','wine','spambase','magic')]}
    audit=study.audit({'registered':True})
    assert not audit['passed']
    assert 'grid' in str(audit)
