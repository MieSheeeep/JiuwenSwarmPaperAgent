import itertools
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research import advanced_retrieval as retrieval


class SemanticFixture:
    identity = {'kind': 'test-only-semantic-fixture'}

    def encode(self, texts):
        return [[1., 0.] if any(t in text.lower() for t in ('car', 'automobile'))
                else [0., 1.] for text in texts]


def record(i, attr='owner', value='v', valid=2, observed=2, **extra):
    return dict(id=str(i), entity='p', attribute=attr, value=value, valid_at=valid,
                observed_at=observed, operation='set', **extra)


QUERY = dict(entity='p', attributes=['owner', 'region'], as_of=10, known_at=10)


class AdvancedRetrievalTests(unittest.TestCase):
    def test_dense_semantic_ranking_and_rrf_exact_score(self):
        texts = ['An automobile moves.', 'A garden grows.', 'Car car car']
        encoder = SemanticFixture()
        dense = retrieval.rank_texts(texts, 'car', 'dense', encoder)
        self.assertEqual([i for i, _ in dense], [0, 2, 1])
        lexical = retrieval.rank_texts(texts, 'car', 'bm25')
        hybrid = dict(retrieval.rank_texts(texts, 'car', 'hybrid', encoder))
        for i in range(3):
            expected = sum(1 / (60 + next(j for j, pair in enumerate(ranking, 1) if pair[0] == i))
                           for ranking in (dense, lexical))
            self.assertAlmostEqual(hybrid[i], expected)

    def test_no_lexical_fallback_for_unavailable_dense(self):
        with self.assertRaises(retrieval.DenseUnavailable):
            retrieval.DenseEncoder(model_dir='definitely-missing-model')

    def test_download_cannot_bless_preexisting_wrong_files_without_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            model_dir = Path(directory)
            for name in retrieval.MODEL_FILES:
                target = model_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'untrusted preexisting file')
            encoder = retrieval.DenseEncoder.__new__(retrieval.DenseEncoder)
            encoder.model_dir = model_dir
            with patch('requests.get', side_effect=AssertionError('network must not be needed')):
                with self.assertRaisesRegex(ValueError, 'Pinned download checksum mismatch'):
                    encoder._download()
            self.assertFalse((model_dir / 'identity.json').exists())

    @unittest.skipUnless((retrieval.DEFAULT_MODEL_DIR / 'identity.json').is_file(), 'local model not downloaded')
    def test_trusted_preexisting_cache_validates_without_network(self):
        with patch('requests.get', side_effect=AssertionError('trusted cache must work offline')):
            encoder = retrieval.DenseEncoder(download=True)
        self.assertEqual(encoder.identity['sha256'], retrieval.MODEL_SHA256)

    def test_versioned_filters_time_and_preserves_atomic_conflict(self):
        rows = [record(0, value='old', valid=1), record(1, value='A'), record(2, value='B'),
                record(3, attr='region'), record(4, valid=20), record(5, observed=20)]
        for packer in ('smaller_first', 'utility_dp', 'diverse'):
            selected = retrieval.select_records(rows, QUERY, 'versioned', 10000, len, packer=packer)
            self.assertEqual(set(selected['record_ids']), {'1', '2', '3'})
            self.assertEqual(selected['conflicts'], ['owner'])
            self.assertEqual(selected['proxy_tokens'], len(selected['text']))
            limited = retrieval.select_records(rows, QUERY, 'versioned', 250, len, packer=packer)
            self.assertEqual('1' in limited['record_ids'], '2' in limited['record_ids'])

    def test_utility_dp_matches_independent_exhaustive_additive_optimum(self):
        groups = [dict(text='a' * size, record_ids=[str(i)], utility=utility, aspect=str(i % 2))
                  for i, (size, utility) in enumerate([(8, 9), (5, 7), (5, 7), (2, 1)])]
        for budget in range(1, 26):
            choices = [comb for k in range(5) for comb in itertools.combinations(range(4), k)
                       if len('\n'.join(groups[i]['text'] for i in comb)) <= budget]
            expected = max(sum(groups[i]['utility'] for i in comb) for comb in choices)
            result = retrieval.pack_atomic_groups(groups, budget, len, 'utility_dp')
            self.assertEqual(result['metadata']['objective_before_recheck'], expected)
            self.assertLessEqual(len(result['text']), budget)

    def test_nonadditive_tokenizer_actual_recheck_drops_whole_group(self):
        def strange_tokens(text):
            return len(text) + (100 if '\n' in text and len(text) > 1 else 0)
        groups = [dict(text='a', record_ids=['a'], utility=1, aspect='x'),
                  dict(text='b', record_ids=['b'], utility=1, aspect='y')]
        result = retrieval.pack_atomic_groups(groups, 5, strange_tokens, 'utility_dp')
        self.assertLessEqual(result['proxy_tokens'], 5)
        self.assertEqual(len(result['record_ids']), 1)
        self.assertEqual(result['metadata']['actual_recheck_dropped_groups'], 1)
        self.assertFalse(result['metadata']['actual_tokenizer_optimality_claim'])

    def test_diverse_round_robin_covers_aspects(self):
        groups = [dict(text='a', record_ids=['a'], utility=9, aspect='x'),
                  dict(text='b', record_ids=['b'], utility=8, aspect='x'),
                  dict(text='c', record_ids=['c'], utility=7, aspect='y')]
        result = retrieval.pack_atomic_groups(groups, 3, len, 'diverse')
        self.assertEqual(result['record_ids'], ['a', 'c'])

    def test_rank_first_preserves_retriever_priority_over_shorter_candidates(self):
        rows = [record(0, value='garden'), record(1, value='automobile vehicle transport')]
        query = {**QUERY, 'question': 'car'}
        budget = len(json.dumps(rows[1], sort_keys=True, separators=(',', ':')))
        dense = retrieval.select_records(rows, query, 'dense', budget, len,
                                         encoder=SemanticFixture(), packer='rank_first')
        self.assertEqual(dense['record_ids'], ['1'])
        class ReverseFixture:
            identity = {'kind': 'reverse-test-only'}
            def encode(self, texts):
                return [[1., 0.] if 'automobile' not in text else [0., 1.] for text in texts]
        reverse = retrieval.select_records(rows, query, 'dense', budget, len,
                                           encoder=ReverseFixture(), packer='rank_first')
        self.assertEqual(reverse['record_ids'], ['0'])

    @unittest.skipUnless((retrieval.DEFAULT_MODEL_DIR / 'identity.json').is_file(), 'local model not downloaded')
    def test_pretrained_local_synonyms_and_cache_and_stable_identity(self):
        encoder = retrieval.DenseEncoder()
        texts = ['A car engine needs a mechanic.', 'A physician treats sick patients.']
        self.assertEqual(retrieval.rank_texts(texts, 'Doctor gives medical treatment.', 'dense', encoder)[0][0], 1)
        count = encoder.encoded_text_count
        retrieval.rank_texts(texts, 'Doctor gives medical treatment.', 'dense', encoder)
        self.assertEqual(encoder.encoded_text_count, count)
        self.assertNotIn('model_load_seconds', encoder.identity)
        self.assertGreater(encoder.load_seconds, 0)

    def test_gold_fields_never_enter_ranking_or_source_text(self):
        plain = [record(0), record(1, attr='region')]
        decorated = [{**r, 'gold': 'SECRET', 'gold_evidence': ['SECRET'], 'utility': 1e100} for r in plain]
        for policy in ('bm25', 'dense', 'hybrid', 'versioned'):
            a = retrieval.select_records(plain, {**QUERY, 'question': 'automobile'}, policy, 10000, len,
                                         encoder=SemanticFixture())
            b = retrieval.select_records(decorated, {**QUERY, 'question': 'automobile', 'gold': 'SECRET'},
                                         policy, 10000, len, encoder=SemanticFixture())
            self.assertEqual(a['text'], b['text'])
            self.assertNotIn('SECRET', b['text'])

    def test_invalid_policy_budget_and_nonfinite_embeddings_fail(self):
        with self.assertRaises(ValueError):
            retrieval.select_records([], QUERY, 'bm25', -1, len)
        with self.assertRaises(ValueError):
            retrieval.rank_texts(['a'], 'b', 'unknown')
        class Broken:
            def encode(self, texts):
                return [[math.nan] for _ in texts]
        with self.assertRaises(ValueError):
            retrieval.rank_texts(['a'], 'b', 'dense', Broken())


if __name__ == '__main__':
    unittest.main()
