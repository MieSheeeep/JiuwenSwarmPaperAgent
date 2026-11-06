"""Hashed envelopes and atomic JSON persistence."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

from research.contracts import SCHEMA_VERSION, validate_payload


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                         allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def create_artifact(kind, payload, parent_ids=()):
    validate_payload(kind, payload)
    envelope = {'schema_version': SCHEMA_VERSION, 'kind': kind,
                'parent_ids': list(parent_ids), 'payload': payload,
                'created_at': datetime.now(timezone.utc).isoformat()}
    content_hash = digest(envelope)
    return {**envelope, 'content_hash': content_hash, 'artifact_id': f'{kind}:{content_hash}'}


def validate_artifact(artifact, expected_kind=None):
    if not isinstance(artifact, dict):
        raise ValueError('Artifact must be an object')
    fields = {'schema_version', 'kind', 'parent_ids', 'payload', 'created_at', 'content_hash', 'artifact_id'}
    if set(artifact) != fields or artifact['schema_version'] != SCHEMA_VERSION:
        raise ValueError('Invalid artifact envelope or schema version')
    if expected_kind and artifact['kind'] != expected_kind:
        raise ValueError('Wrong artifact kind')
    validate_payload(artifact['kind'], artifact['payload'])
    if not isinstance(artifact['parent_ids'], list) or not all(isinstance(p, str) for p in artifact['parent_ids']):
        raise ValueError('Invalid artifact parents')
    content = {k: v for k, v in artifact.items() if k not in {'content_hash', 'artifact_id'}}
    computed = digest(content)
    if artifact['content_hash'] != computed or artifact['artifact_id'] != f"{artifact['kind']}:{computed}":
        raise ValueError('Artifact content hash mismatch')
    return artifact


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create temporary file beside target so os.replace is on the same volume.
    handle, name = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
