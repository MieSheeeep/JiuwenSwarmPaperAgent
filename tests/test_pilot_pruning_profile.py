import pytest


def test_manuscript_rejects_unknown_reference():
    from research.workflow.pilot_pruning_profile import validate_manuscript
    with pytest.raises(ValueError, match='Unknown'):
        validate_manuscript({'title':'Audit', 'sections':[{'heading':'Abstract','text':'Text'}],
                             'references':[{'id':'invented'}]}, {'known':{}})


def test_manuscript_rejects_non_english_body():
    from research.workflow.pilot_pruning_profile import validate_manuscript
    with pytest.raises(ValueError, match='English'):
        validate_manuscript({'title':'Audit', 'sections':[{'heading':'Abstract','text':'中文论文'}],
                             'references':[]}, {})


def test_failed_health_pilot_never_becomes_go():
    from research.workflow.pilot_pruning_profile import health_decision
    result=health_decision({'passed':False,'diagnostics':{'mass_ok':False}})
    assert result['passed'] is False
    assert result['decision']=='no_go'


def test_inline_citations_must_be_known_and_in_bibliography():
    from research.workflow.pilot_pruning_profile import validate_manuscript,HEADINGS
    value={'title':'Audit','sections':[{'heading':h,'text':'word '*130} for h in HEADINGS], 'references':[]}
    value['sections'][0]['text']+=' [made-up-source]'
    with pytest.raises(ValueError,match='Unknown inline'):
        validate_manuscript(value,{})
    value['sections'][0]['text']=value['sections'][0]['text'].replace('made-up-source','1810.08240')
    with pytest.raises(ValueError,match='bibliography'):
        validate_manuscript(value,{'1810.08240':{}})


def test_math_interval_is_not_a_citation():
    from research.workflow.pilot_pruning_profile import validate_manuscript,HEADINGS
    value={'title':'Audit','sections':[{'heading':h,'text':'word '*130} for h in HEADINGS],'references':[]}
    value['sections'][0]['text']+=' [L_plus-U_minus,U_plus-L_minus]'
    validate_manuscript(value,{})
