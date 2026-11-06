"""Independent opt-in retrievers and atomic group packing; no evaluation labels.

Dense features are pretrained MiniLM ONNX embeddings, never lexical hashes.
The original versioned_memory module is imported read-only for its validation
and canonical source serialization, so frozen experiment semantics are retained.
"""
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import time

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = 'Xenova/all-MiniLM-L6-v2'
MODEL_REVISION = '751bff37182d3f1213fa05d7196b954e230abad9'
MODEL_FILES = ('onnx/model_quantized.onnx', 'tokenizer.json', 'tokenizer_config.json', 'config.json')
# Hashes independently pinned with the immutable model revision. A local
# manifest is provenance, never authority to bless arbitrary preexisting bytes.
MODEL_SHA256 = {
    'onnx/model_quantized.onnx': 'afdb6f1a0e45b715d0bb9b11772f032c399babd23bfc31fed1c170afc848bdb1',
    'tokenizer.json': 'da0e79933b9ed51798a3ae27893d3c5fa4a201126cef75586296df9b4d2c62a0',
    'tokenizer_config.json': '9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3',
    'config.json': '7135149f7cffa1a573466c6e4d8423ed73b62fd2332c575bf738a0d033f70df7',
}
DEFAULT_MODEL_DIR = ROOT / 'sources/model_cache/all-MiniLM-L6-v2' / MODEL_REVISION
_spec = importlib.util.spec_from_file_location('_frozen_retrieval_source', ROOT /
    'upstream/jiuwenswarm/agents/harness/common/versioned_memory.py')
_source = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_source)


class DenseUnavailable(RuntimeError):
    """An explicitly unavailable local dense model; no silent baseline fallback."""


def _sha256(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


class DenseEncoder:
    """Pinned public quantized MiniLM, masked mean pooling, L2 normalization.

    Downloads are opt-in, inference is local CPU only (at most four threads).
    Each encode call is batched at 16 texts, truncated to 256 wordpiece tokens.
    ``identity`` includes exact weights/tokenizer checksums and local timings.
    """
    def __init__(self, model_dir=None, *, download=False, threads=4):
        if type(threads) is not int or not 1 <= threads <= 4:
            raise ValueError('CPU threads must be between 1 and 4')
        self.model_dir = Path(model_dir) if model_dir is not None else DEFAULT_MODEL_DIR
        started = time.perf_counter()
        try:
            if download:
                self._download()
            absent = [name for name in MODEL_FILES if not (self.model_dir / name).is_file()]
            if absent:
                raise FileNotFoundError(', '.join(absent))
            hashes = {name: _sha256(self.model_dir / name) for name in MODEL_FILES}
            if hashes != MODEL_SHA256:
                raise ValueError('Pinned model checksum mismatch')
            manifest_path = self.model_dir / 'identity.json'
            if not manifest_path.exists():
                raise ValueError('Missing download provenance identity.json; use download=True')
            previous = json.loads(manifest_path.read_text(encoding='utf-8'))
            if (previous.get('revision') != MODEL_REVISION or previous.get('model') != MODEL_ID
                    or previous.get('sha256') != hashes):
                raise ValueError('Pinned model provenance/checksum mismatch')
            import numpy as np
            import onnxruntime as ort
            from tokenizers import Tokenizer
            self._np = np
            self.tokenizer = Tokenizer.from_file(str(self.model_dir / 'tokenizer.json'))
            self.tokenizer.enable_truncation(max_length=256)
            self.tokenizer.enable_padding(pad_id=0, pad_token='[PAD]')
            options = ort.SessionOptions()
            options.intra_op_num_threads = threads
            options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(str(self.model_dir / 'onnx/model_quantized.onnx'),
                                               sess_options=options, providers=['CPUExecutionProvider'])
            self.identity = {**previous, 'runtime': 'onnxruntime', 'runtime_version': ort.__version__,
                             'threads': threads, 'pooling': 'attention-mask mean then L2',
                             'max_length': 256, 'batch_size': 16, 'device': 'CPU',
                             'remote_embedding_calls': 0, 'generation_tokens': 0,
                             'truncation': True, 'cache_key': 'sha256 UTF-8 text',
                             'download_bytes': sum((self.model_dir / name).stat().st_size for name in MODEL_FILES)}
            self.load_seconds = time.perf_counter() - started
            self.encode_seconds = 0.
            self.encoded_text_count = 0
            self._cache = {}
        except Exception as exc:
            raise DenseUnavailable(f'Local pretrained dense encoder unavailable: {exc}') from exc

    def _download(self):
        import requests
        self.model_dir.mkdir(parents=True, exist_ok=True)
        # Immutable repository revision, no executable remote model code.
        for name in MODEL_FILES:
            target = self.model_dir / name
            if target.is_file():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + '.partial')
            try:
                with requests.get(f'https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{name}',
                                  stream=True, timeout=(20, 120)) as response:
                    response.raise_for_status()
                    with temporary.open('wb') as output:
                        for chunk in response.iter_content(1024 * 1024):
                            output.write(chunk)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        hashes = {name: _sha256(self.model_dir / name) for name in MODEL_FILES}
        if hashes != MODEL_SHA256:
            raise ValueError('Pinned download checksum mismatch; remove or replace untrusted model files')
        manifest = {'model': MODEL_ID, 'revision': MODEL_REVISION,
                    'source': f'https://huggingface.co/{MODEL_ID}/tree/{MODEL_REVISION}',
                    'sha256': hashes}
        path = self.model_dir / 'identity.json'
        # Existing provenance must never silently be re-blessed after corruption.
        if path.exists() and json.loads(path.read_text(encoding='utf-8')) != manifest:
            raise ValueError('Existing model provenance/checksum mismatch')
        path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    def encode(self, texts):
        if not all(isinstance(text, str) for text in texts):
            raise ValueError('encode expects a list of strings')
        started = time.perf_counter()
        keys = {text: hashlib.sha256(text.encode('utf-8')).hexdigest() for text in texts}
        missing = list(dict.fromkeys(text for text in texts if keys[text] not in self._cache))
        np = self._np
        for start in range(0, len(missing), 16):
            batch = missing[start:start + 16]
            encoded = self.tokenizer.encode_batch(batch)
            candidates = {'input_ids': np.array([item.ids for item in encoded], dtype=np.int64),
                          'attention_mask': np.array([item.attention_mask for item in encoded], dtype=np.int64),
                          'token_type_ids': np.array([item.type_ids for item in encoded], dtype=np.int64)}
            inputs = {item.name: candidates[item.name] for item in self.session.get_inputs()}
            hidden = self.session.run(None, inputs)[0]
            mask = candidates['attention_mask'][..., None]
            pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
            pooled /= np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
            self._cache.update((keys[text], vector) for text, vector in zip(batch, pooled.tolist()))
        self.encode_seconds += time.perf_counter() - started
        self.encoded_text_count += len(missing)
        return [list(self._cache[keys[text]]) for text in texts]


def _terms(text):
    return re.findall(r'\w+', text.casefold())


def rank_texts(texts, question, method='bm25', encoder=None):
    """Rank indices deterministically. Hybrid is equal-weight RRF, k=60."""
    if method not in ('bm25', 'dense', 'hybrid'):
        raise ValueError('unknown retrieval method: ' + str(method))
    if not texts:
        return []
    if method == 'hybrid':
        rankings = [rank_texts(texts, question, name, encoder) for name in ('bm25', 'dense')]
        scores = [0.] * len(texts)
        for ranking in rankings:
            for rank, (index, _) in enumerate(ranking, 1):
                scores[index] += 1 / (60 + rank)
    elif method == 'bm25':
        docs = [_terms(text) for text in texts]
        average = sum(map(len, docs)) / len(docs)
        frequencies = Counter(term for doc in docs for term in set(doc))
        question_terms = set(_terms(question))
        scores = []
        for document in docs:
            counts = Counter(document)
            scores.append(sum(math.log(1 + (len(docs) - frequencies[t] + .5) / (frequencies[t] + .5))
                              * counts[t] * 2.5 / (counts[t] + 1.5 * (.25 + .75 * len(document) / max(average, 1)))
                              for t in question_terms if counts[t]))
    else:
        encoder = encoder if encoder is not None else DenseEncoder()
        vectors = encoder.encode([question, *texts])
        if (len(vectors) != len(texts) + 1 or not vectors[0] or
                any(len(v) != len(vectors[0]) or any(not math.isfinite(x) for x in v) for v in vectors)):
            raise ValueError('encoder must return equal-size finite vectors')
        def cosine(vector):
            norm = math.sqrt(sum(x*x for x in vector) * sum(x*x for x in vectors[0]))
            return sum(a*b for a, b in zip(vector, vectors[0])) / norm if norm else 0.
        scores = [cosine(vector) for vector in vectors[1:]]
    return sorted(enumerate(scores), key=lambda item: (-item[1], item[0]))


def pack_atomic_groups(groups, budget, count_tokens, packer='smaller_first'):
    """Pack group dictionaries; never split a group or inspect evaluation fields.

    DP maximizes sum(group.utility) subject to an ADDITIVE surrogate cost:
    sum(tokens(group.text) + tokens(newline)) <= budget + tokens(newline).
    Equal objective ties keep the earlier DP state. This is *not* a proof of
    optimality under nonadditive tokenization. The actual joined text is checked
    and whole final groups removed if needed. Metadata reports both objectives.
    """
    if type(budget) is not int or budget < 0:
        raise ValueError('budget must be a nonnegative integer')
    if packer not in ('rank_first', 'smaller_first', 'utility_dp', 'diverse'):
        raise ValueError('unknown atomic group packer: ' + str(packer))
    separator_cost = count_tokens('\n')
    costs = [count_tokens(g['text']) + separator_cost for g in groups]
    utilities = [g['utility'] for g in groups]
    if any(not math.isfinite(u) or u < 0 for u in utilities):
        raise ValueError('group utility must be finite and nonnegative')
    def render(indices):
        return '\n'.join(groups[i]['text'] for i in indices)
    selected = []
    if packer == 'utility_dp':
        # Sparse 0/1 DP over token costs; immutable tuple states prevent reuse.
        states = {0: (0., ())}
        for i, cost in enumerate(costs):
            updated = dict(states)
            for used, (utility, chosen) in sorted(states.items()):
                candidate_cost = used + cost
                if candidate_cost <= budget + separator_cost:
                    previous = updated.get(candidate_cost)
                    candidate = (utility + utilities[i], chosen + (i,))
                    if previous is None or candidate[0] > previous[0]:
                        updated[candidate_cost] = candidate
            states = updated
        selected = list(max(states.items(), key=lambda pair: (pair[1][0], -pair[0]))[1][1])
    else:
        if packer == 'rank_first':
            order = range(len(groups))
        elif packer == 'smaller_first':
            order = sorted(range(len(groups)), key=lambda i: (costs[i], i))
        else:
            buckets = defaultdict(list)
            for i in sorted(range(len(groups)), key=lambda i: (-utilities[i], i)):
                buckets[groups[i]['aspect']].append(i)
            order = [bucket[j] for j in range(max(map(len, buckets.values()), default=0))
                     for bucket in buckets.values() if j < len(bucket)]
        for i in order:
            if count_tokens(render([*selected, i])) <= budget:
                selected.append(i)
    objective_before = sum(utilities[i] for i in selected)
    dropped = 0
    while selected and count_tokens(render(selected)) > budget:
        selected.pop()
        dropped += 1
    text = render(selected)
    if count_tokens(text) > budget:
        raise ValueError('token counter assigns empty text more tokens than the budget')
    return {'text': text, 'record_ids': [r for i in selected for r in groups[i]['record_ids']],
            'proxy_tokens': count_tokens(text), 'conflicts': [],
            'metadata': {'packer': packer, 'selected_group_indices': selected,
                         'objective': 'sum of nonnegative group utilities',
                         'objective_before_recheck': objective_before,
                         'objective_after_recheck': sum(utilities[i] for i in selected),
                         'additive_surrogate_tokens': sum(costs[i] for i in selected) -
                                                     (separator_cost if selected else 0),
                         'actual_recheck_dropped_groups': dropped,
                         'actual_tokenizer_optimality_claim': False}}


def select_records(records, query, policy, budget, count_tokens, encoder=None, packer='smaller_first'):
    """Baseline retrieval over all raw records, or visible latest atomic groups.

    versioned matches frozen maximal-valid-time grouping, including every visible
    equal-time record. Smaller-first has unit group utility (coverage objective).
    Baseline utility is 1/rank; its atomic groups each contain one raw record.
    Only allowlisted source/query fields are used, never gold answers or labels.
    """
    started = time.perf_counter()
    if policy not in ('bm25', 'dense', 'hybrid', 'versioned'):
        raise ValueError('unknown selection policy: ' + str(policy))
    records = _source._validate_records(records)
    if (not isinstance(query.get('entity'), str) or not isinstance(query.get('attributes'), list)
            or not all(isinstance(a, str) for a in query['attributes'])
            or any(type(query.get(k)) is not int for k in ('as_of', 'known_at'))):
        raise ValueError('query requires entity, attributes and integer cutoffs')
    lines = [_source._serialize(r) for r in records]
    conflicts, groups = [], []
    if policy == 'versioned':
        for attribute in dict.fromkeys(query['attributes']):
            visible = [i for i, r in enumerate(records) if r['entity'] == query['entity']
                       and r['attribute'] == attribute and r['valid_at'] <= query['as_of']
                       and r['observed_at'] <= query['known_at']]
            if not visible:
                continue
            latest = max(records[i]['valid_at'] for i in visible)
            indices = [i for i in visible if records[i]['valid_at'] == latest]
            if len({(records[i]['operation'], _source._serialize(records[i]['value'])) for i in indices}) > 1:
                conflicts.append(attribute)
            groups.append({'text': '\n'.join(lines[i] for i in indices),
                           'record_ids': [records[i]['id'] for i in indices], 'utility': 1., 'aspect': attribute})
    else:
        question = ' '.join([query['entity'], *query['attributes'], str(query.get('question', ''))])
        if policy in ('dense', 'hybrid') and encoder is None:
            encoder = DenseEncoder()
        ranking = rank_texts(lines, question, policy, encoder)
        for rank, (i, _) in enumerate(ranking, 1):
            groups.append({'text': lines[i], 'record_ids': [records[i]['id']],
                           'utility': 1 / rank, 'aspect': records[i]['attribute']})
    result = pack_atomic_groups(groups, budget, count_tokens, packer)
    if policy == 'versioned':
        selected = set(result['record_ids'])
        result['record_ids'] = [r['id'] for r in records if r['id'] in selected]
        result['text'] = '\n'.join(lines[i] for i, r in enumerate(records) if r['id'] in selected)
        # Reordering can change a real tokenizer: remove entire groups and recheck.
        while result['record_ids'] and count_tokens(result['text']) > budget:
            last_group = result['metadata']['selected_group_indices'].pop()
            selected.difference_update(groups[last_group]['record_ids'])
            result['record_ids'] = [r['id'] for r in records if r['id'] in selected]
            result['text'] = '\n'.join(lines[i] for i, r in enumerate(records) if r['id'] in selected)
            result['metadata']['actual_recheck_dropped_groups'] += 1
            result['metadata']['objective_after_recheck'] -= groups[last_group]['utility']
        result['proxy_tokens'] = count_tokens(result['text'])
        remaining = result['metadata']['selected_group_indices']
        result['metadata']['additive_surrogate_tokens'] = (
            sum(count_tokens(groups[i]['text']) + count_tokens('\n') for i in remaining)
            - (count_tokens('\n') if remaining else 0))
    result['conflicts'] = conflicts
    result['metadata'].update(policy=policy, retrieval_seconds=time.perf_counter() - started,
                              atomic_group_count=len(groups), utility_source='unit coverage' if policy == 'versioned'
                              else 'reciprocal retrieval rank, no labels', rrf_k=60 if policy == 'hybrid' else None)
    if policy in ('dense', 'hybrid') and encoder is not None:
        result['metadata']['encoder_identity'] = encoder.identity
    return result
