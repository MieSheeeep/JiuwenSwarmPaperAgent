"""Durable call ledger with conservative admission and fail-closed unknown spend."""
import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
import uuid

from research.artifacts import digest


class BudgetExceeded(ValueError):
    pass


class UnknownSpend(RuntimeError):
    pass


class InvocationContractError(RuntimeError):
    """Provider response exists but experiment instrumentation is invalid."""


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        # JSONL records end at ASCII LF. PDF text can contain literal U+2028,
        # U+2029 or U+0085 inside a valid JSON string; str.splitlines would
        # split those source characters and misdiagnose known spend as unknown.
        return [json.loads(line) for line in path.read_text(encoding='utf-8').split('\n') if line.strip()]
    except ValueError as error:
        raise UnknownSpend(f'Interrupted or invalid ledger at {path.name}; reconcile before spending') from error


def append_durable(path, row):
    with Path(path).open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def valid_usage(usage):
    return (isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0
            for k in ('input_tokens', 'output_tokens', 'total_tokens')) and
            usage['total_tokens'] == usage['input_tokens'] + usage['output_tokens'])


def invocation_fingerprint(messages, tag, max_tokens, model, provider, endpoint_hash):
    return digest({'messages': messages, 'tag': tag, 'max_tokens': max_tokens,
                   'model': model, 'provider': provider, 'endpoint_hash': endpoint_hash,
                   'settings': 'temperature0-thinking-disabled-v1'})


class ModelGateway:
    def __init__(self, config, directory, *, max_total_tokens, max_calls, wall_seconds, count_tokens):
        if any(type(n) is not int or n <= 0 for n in (max_total_tokens, max_calls, wall_seconds)):
            raise ValueError('Explicit positive integer token/call/time limits are required')
        self.config = config
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_total_tokens, self.max_calls, self.wall_seconds = max_total_tokens, max_calls, wall_seconds
        self.count_tokens = count_tokens
        self.calls = read_jsonl(self.directory / 'calls.jsonl')
        self.requests = read_jsonl(self.directory / 'requests.jsonl')
        ids = [r.get('id') for r in self.requests]
        call_ids = [c.get('id') for c in self.calls]
        if len(set(ids)) != len(ids) or len(set(call_ids)) != len(call_ids) or set(call_ids) - set(ids):
            raise UnknownSpend('Ledger request/response IDs disagree')
        self.started = time.monotonic()
        self.invocation_errors = read_jsonl(self.directory / 'invocation_errors.jsonl')

    def totals(self):
        completed = {c['id'] for c in self.calls}
        unknown = [c['id'] for c in self.calls if not valid_usage(c.get('usage'))]
        unknown.extend(r['id'] for r in self.requests if r['id'] not in completed)
        unknown.extend(e['id'] for e in self.invocation_errors if e.get('spend_uncertain'))
        elapsed = sum(c.get('elapsed_seconds', 0) for c in self.calls)
        return {'api_calls': len(self.requests),
                'known_api_tokens': sum(c['usage']['total_tokens'] for c in self.calls if valid_usage(c.get('usage'))),
                'unknown_spend_ids': unknown, 'summed_call_seconds': elapsed}

    async def call(self, messages, tag, max_tokens=256, invoke=None):
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError('max_tokens must be positive')
        fingerprint = invocation_fingerprint(messages, tag, max_tokens, self.config['model'],
                                              self.config['provider'], digest(self.config['api_base']))
        if any(e.get('fingerprint') == fingerprint for e in self.invocation_errors):
            raise InvocationContractError('A persisted response failed experimental instrumentation; cannot reuse as valid evidence')
        cached = [c for c in self.calls if c.get('fingerprint') == fingerprint and c.get('status') == 'ok']
        if cached:
            if not valid_usage(cached[-1].get('usage')):
                raise UnknownSpend('Cached response has unknown usage')
            return cached[-1]
        totals = self.totals()
        if totals['unknown_spend_ids']:
            raise UnknownSpend('Unreconciled billable attempt; no automatic retry or further spend')
        # Proxy tokenizer is not vendor billing: reserve a conservative margin,
        # then reconcile actual usage. A provider overrun halts subsequent calls.
        estimated = self.count_tokens(json.dumps(messages, ensure_ascii=False))
        reservation = 2 * estimated + 512 + max_tokens
        if totals['known_api_tokens'] + reservation > self.max_total_tokens:
            raise BudgetExceeded('Token admission limit reached')
        elapsed = time.monotonic() - self.started
        if self.requests:
            try:
                first_time = min(datetime.fromisoformat(r['created_at']) for r in self.requests)
                elapsed = max(elapsed, (datetime.now(timezone.utc) - first_time).total_seconds())
            except (KeyError, ValueError, TypeError) as error:
                raise UnknownSpend('Cannot reconstruct persisted wall-clock allowance') from error
        remaining_seconds = self.wall_seconds - elapsed
        if totals['api_calls'] >= self.max_calls or remaining_seconds <= 0:
            raise BudgetExceeded('Call or wall-time limit reached')
        request_id = uuid.uuid4().hex
        request = {'id': request_id, 'fingerprint': fingerprint, 'tag': tag,
                   'messages_hash': digest(messages),
                   'reserved_tokens': reservation, 'max_output_tokens': max_tokens,
                   'created_at': datetime.now(timezone.utc).isoformat()}
        # Reservation is durable before any transport can start. Concurrent
        # in-flight requests are considered unknown until their responses arrive.
        append_durable(self.directory / 'requests.jsonl', request)
        self.requests.append(request)
        started = time.monotonic()
        recorded = []

        def record(output, usage, actual_messages):
            if recorded:
                # Account for the unexpected response instead of hiding it as
                # an ordinary postprocessing failure. Its reservation is marked
                # retrospective, and any further spending requires reconciliation.
                extra_id = uuid.uuid4().hex
                extra_tag = tag + '/unexpected-response'
                extra_request = {**request, 'id': extra_id, 'tag': extra_tag,
                                 'reservation_origin': 'unexpected_response_observed'}
                append_durable(self.directory / 'requests.jsonl', extra_request)
                self.requests.append(extra_request)
                extra = {'id': extra_id, 'fingerprint': fingerprint, 'tag': extra_tag,
                         'model': self.config['model'], 'output': output, 'messages': actual_messages,
                         'usage': usage if valid_usage(usage) else None,
                         'raw_usage': usage if not valid_usage(usage) else None,
                         'status': 'unexpected_response', 'elapsed_seconds': 0}
                append_durable(self.directory / 'calls.jsonl', extra)
                self.calls.append(extra)
                event = {'id': extra_id, 'fingerprint': fingerprint, 'spend_uncertain': True,
                         'error_type': 'UnexpectedResponse'}
                append_durable(self.directory / 'invocation_errors.jsonl', event)
                self.invocation_errors.append(event)
                raise InvocationContractError('More than one response for a single-call invocation')
            row = {'id': request_id, 'fingerprint': fingerprint, 'tag': tag,
                   'model': self.config['model'], 'output': output, 'messages': actual_messages,
                   'usage': usage if valid_usage(usage) else None,
                   'raw_usage': usage if not valid_usage(usage) else None,
                   'status': 'ok' if valid_usage(usage) else 'unknown',
                   'elapsed_seconds': time.monotonic() - started,
                   'timestamp_utc': datetime.now(timezone.utc).isoformat()}
            append_durable(self.directory / 'calls.jsonl', row)
            self.calls.append(row)
            recorded.append(row)

        async def default_invoke(on_response):
            from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
            client = ModelClientConfig(client_provider=self.config['provider'], api_base=self.config['api_base'],
                                       api_key=self.config['api_key'], timeout=120, max_retries=0)
            settings = ModelRequestConfig(model=self.config['model'], temperature=0, top_p=1,
                                          max_tokens=max_tokens, extra_body={'thinking': {'type': 'disabled'}})
            response = await Model(client, settings).invoke(messages)
            usage = response.usage_metadata.model_dump() if response.usage_metadata else None
            on_response(response.content, usage, messages)
            return response.content

        try:
            await asyncio.wait_for((invoke or default_invoke)(record), timeout=min(250, remaining_seconds))
        except Exception as error:
            if isinstance(error, InvocationContractError):
                event = {'id': request_id, 'fingerprint': fingerprint, 'error_type': type(error).__name__}
                append_durable(self.directory / 'invocation_errors.jsonl', event)
                self.invocation_errors.append(event)
                raise
            if not recorded:
                row = {'id': request_id, 'fingerprint': fingerprint, 'tag': tag, 'model': self.config['model'],
                       'output': '', 'usage': None, 'status': 'unknown', 'error_type': type(error).__name__,
                       'elapsed_seconds': time.monotonic() - started}
                append_durable(self.directory / 'calls.jsonl', row)
                self.calls.append(row)
                raise UnknownSpend('Transport/agent failed before a persisted response; spend unknown') from error
            # A successful billable response remains usable even if the agent
            # later fails while assembling its final output.
        if not recorded or not valid_usage(recorded[0]['usage']):
            raise UnknownSpend('Response usage missing; stop until reconciled')
        return recorded[0]
