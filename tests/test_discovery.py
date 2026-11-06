import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from research.discovery import validate_stage, validate_handoff
from research.literature import parse_feed, make_chunks, ArxivClient


def corpus():
    return [{'id': 'p1', 'title': 'First', 'url': 'https://arxiv.org/abs/2410.10813', 'reading_scope': 'full_text_excerpt',
             'chunks': [{'id': 'p1:c0', 'text': 'The benchmark measures temporal updates.'}]},
            {'id': 'p2', 'title': 'Second', 'url': 'https://arxiv.org/abs/2504.19413', 'reading_scope': 'abstract_only',
             'chunks': [{'id': 'p2:c0', 'text': 'Memory retrieval uses a graph.'}]}]


def notes():
    return {'papers': [{'paper_id': p['id'], 'method': 'Method described in source',
                       'evaluation': 'not established', 'limitations': 'not established',
                       'evidence': [{'chunk_id': p['chunks'][0]['id'], 'quote': p['chunks'][0]['text']}]
                       } for p in corpus()], 'comparison': 'Different methods; no superiority established.'}


class DiscoveryTests(unittest.TestCase):
    def test_feed_deduplicates_versions_and_keeps_abstract(self):
        feed = '''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2410.10813v2</id><title>Long Memory</title><summary> Test abstract </summary><author><name>A</name></author><published>2024-10-01</published></entry></feed>'''
        rows = parse_feed(feed)
        self.assertEqual(rows[0]['id'], '2410.10813')
        self.assertEqual(rows[0]['abstract'], 'Test abstract')

    def test_chunks_preserve_exact_quote_locators(self):
        chunks = make_chunks('p1', 'a' * 2500)
        self.assertTrue(all(c['id'].startswith('p1:c') for c in chunks))
        self.assertEqual(''.join(c['text'] for c in chunks), 'a' * 2500)

    def test_legacy_arxiv_identifier_is_valid_metadata(self):
        xml = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/hep-lat/0601017v1</id><title>Old paper</title><summary>Abstract</summary></entry></feed>'
        self.assertEqual(parse_feed(xml)[0]['id'], 'hep-lat/0601017')

    def test_unavailable_full_text_is_explicitly_abstract_only(self):
        client = ArxivClient(Path('.'))
        paper = {'id': 'p', 'url': 'https://arxiv.org/abs/2410.10813',
                 'version_url': 'https://arxiv.org/abs/2410.10813v2', 'abstract': 'Only abstract available.'}
        with patch.object(client, 'fetch', side_effect=OSError('offline')):
            read = client.read(paper)
        self.assertEqual(read['reading_scope'], 'abstract_only')
        self.assertEqual(read['read_error'], 'OSError')
        self.assertEqual(read['chunks'][0]['text'], paper['abstract'])

    def test_full_text_excludes_page_scripts_and_is_bounded(self):
        client = ArxivClient(Path('.'))
        paper = {'id': 'p', 'url': 'https://arxiv.org/abs/2410.10813',
                 'version_url': 'https://arxiv.org/abs/2410.10813v2', 'abstract': 'Abstract'}
        with patch.object(client, 'fetch', return_value='<article><script>malicious</script><p>'+'body '*400+'</p></article>'):
            read = client.read(paper, max_chars=1300)
        self.assertEqual(read['reading_scope'], 'full_text_excerpt')
        text = ''.join(c['text'] for c in read['chunks'])
        self.assertNotIn('malicious', text)
        self.assertEqual(len(text), 1300)

    def test_notes_must_cover_every_paper_and_real_quote(self):
        validate_stage('literature_review', notes(), corpus())
        bad = notes(); bad['papers'][0]['evidence'][0]['quote'] = 'invented finding'
        with self.assertRaises(ValueError): validate_stage('literature_review', bad, corpus())
        bad = notes(); bad['papers'].pop()
        with self.assertRaises(ValueError): validate_stage('literature_review', bad, corpus())

    def test_question_cannot_claim_novelty_or_invent_sources(self):
        value = {'candidates': [{'id': 'g1', 'question': 'Does it work?', 'hypothesis': 'It may help.',
                 'motivation': 'Worth testing', 'source_ids': ['p1', 'p2'],
                 'novelty_status': 'unverified', 'falsification': 'No improvement',
                 'verification_query': 'all:memory'}], 'selected_id': 'g1'}
        validate_stage('question_formulation', value, corpus())
        for key, replacement in [('novelty_status', 'proven_novel'), ('source_ids', ['fake'])]:
            bad = copy.deepcopy(value); bad['candidates'][0][key] = replacement
            with self.assertRaises(ValueError): validate_stage('question_formulation', bad, corpus())

    def test_handoff_rejects_unimplemented_or_changed_protocol(self):
        from research.discovery import MEMORY_PROTOCOL
        plan = {'adapter': 'structured-memory-v1', 'protocol': copy.deepcopy(MEMORY_PROTOCOL)}
        validate_handoff(plan)
        plan['protocol']['main_budget'] = 999
        with self.assertRaises(ValueError): validate_handoff(plan)
        with self.assertRaises(ValueError): validate_handoff({'adapter': 'new-algorithm'})

    def test_plan_requires_falsification_and_cost_ceiling(self):
        from research.discovery import PLAN_EXAMPLE
        value = copy.deepcopy(PLAN_EXAMPLE)
        validate_stage('experiment_design', value, corpus(), selected_id='g1')
        for key in ('falsification', 'cost_controls', 'ablations', 'data_split'):
            bad = copy.deepcopy(value); bad.pop(key)
            with self.assertRaises(ValueError): validate_stage('experiment_design', bad, corpus(), selected_id='g1')

    def test_plan_can_cite_retrieved_closest_work_but_not_invented_ids(self):
        from research.discovery import PLAN_EXAMPLE
        value = copy.deepcopy(PLAN_EXAMPLE); value['source_ids'].append('closest')
        validate_stage('experiment_design', value, corpus(), selected_id='g1',
                       closest_papers=[{'id': 'closest'}])
        with self.assertRaises(ValueError):
            validate_stage('experiment_design', value, corpus(), selected_id='g1')


if __name__ == '__main__': unittest.main()
