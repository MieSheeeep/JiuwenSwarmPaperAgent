"""UTF-8 JSONL codec: only LF ends a record; Unicode separators are valid data."""
import json
import os
from pathlib import Path

from research.model_gateway import UnknownSpend


def read_jsonl(path):
    path=Path(path)
    if not path.exists():return []
    try:
        return [json.loads(line) for line in path.read_text(encoding='utf-8').split('\n') if line.strip()]
    except (ValueError,UnicodeError) as error:
        raise UnknownSpend(f'Interrupted or invalid ledger at {path.name}; reconcile before spending') from error


def append_durable(path,row):
    # ASCII escaping also allows older JSONL readers to inspect newly written files.
    with Path(path).open('a',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(row,ensure_ascii=True,allow_nan=False)+'\n')
        stream.flush();os.fsync(stream.fileno())


def configure_gateway_ledger():
    # Dedicated v3 runtime adapter. Keep the historical source file/hash intact.
    import research.model_gateway as gateway
    gateway.read_jsonl=read_jsonl
    gateway.append_durable=append_durable
