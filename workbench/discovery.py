"""Read-only, allowlisted discovery summaries; never expose model request ledgers."""
import json

from research.discovery import load_bundle


def payload(repository):
    rows = []
    for directory in sorted((repository.root / 'output').glob('discovery_*'), reverse=True):
        try:
            directory = repository._safe(directory)
            manifest = repository._json(directory / 'manifest.json', {})
            if not manifest or 'skill_hashes' not in manifest: continue
            state = repository._json(directory / 'state.json', {})
            row = {'id': directory.name, 'topic': manifest['topic'], 'status': state.get('status', 'pending'),
                   'resources': state.get('resources', {}), 'reason': state.get('reason'), 'bundle': None}
            if state.get('status') == 'completed':
                bundle = load_bundle(directory)
                # Excerpts/transport requests are not needed in the overview.
                bundle['sources'] = [{k: p.get(k) for k in ('id', 'title', 'url', 'reading_scope')} for p in bundle['sources']]
                row['bundle'] = bundle
            rows.append(row)
        except (OSError, ValueError, KeyError, TypeError):
            rows.append({'id': directory.name, 'status': 'invalid', 'topic': '研究产物校验失败', 'bundle': None,
                         'reason': '文件缺失、格式错误或内容发生变化', 'resources': {}})
    return rows
