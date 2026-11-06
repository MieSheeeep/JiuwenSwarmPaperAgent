"""Translate allowlisted research artifacts into the workbench API."""
import hashlib
import json
from pathlib import Path
import re


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def _safe(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root):
            raise KeyError('Artifact outside project')
        return path

    def _json(self, path, default=None):
        path = self._safe(path)
        if not path.is_file(): return default
        value = json.loads(path.read_text(encoding='utf-8'))
        if default is not None and not isinstance(value, type(default)):
            raise ValueError('Invalid artifact structure')
        if isinstance(default, list) and any(not isinstance(row, dict) for row in value):
            raise ValueError('Expected structured records')
        return value

    def _run(self, run_id):
        if not re.fullmatch(r'memory_live_[A-Za-z0-9_-]+', run_id):
            raise KeyError('Unknown run')
        path = self._safe(self.root/'output'/run_id)
        if not (path/'manifest.json').is_file():
            raise KeyError('Unknown run')
        return path

    def runs(self):
        items = []
        for path in sorted((self.root/'output').glob('memory_live_*'), reverse=True):
            if not (path/'manifest.json').is_file():
                continue
            try:
                manifest = self._json(path/'manifest.json', {})
                items.append({'id': path.name, 'label': path.name.removeprefix('memory_live_'),
                              'model': manifest.get('model', 'Unknown')})
            except (ValueError, KeyError, OSError):
                continue
        return items

    def _paths(self, run_id):
        run = self._run(run_id)
        suffix = run.name.removeprefix('memory_live_')
        paper = self._safe(self.root/'output'/f'memory_paper_{suffix}')
        review = self.root/'submission'/f'memory-{suffix}-review'
        return run, paper, review, suffix

    def artifacts(self, run_id):
        run, paper, review, suffix = self._paths(run_id)
        candidates = {
            'paper': ('English manuscript', paper/'paper.pdf'),
            'latex': ('LaTeX source', paper/'paper.tex'),
            'manuscript': ('English manuscript · Markdown', paper/'paper.md'),
            'resources': ('Resource report', paper/'resources.json'),
            'results': ('Experiment results', run/'results.jsonl'),
            'summary': ('Experiment summary', run/'summary.json'),
            'review': ('Original AI review', review.with_suffix('.txt')),
            'review-summary': ('Review metadata', Path(str(review)+'-summary.json')),
            'patch': ('Framework contribution patch', self.root/'submission'/f'空梦轮年-优化版-{suffix}'/'framework_contribution.patch'),
            'bundle': ('Competition submission bundle', self.root/'submission'/f'空梦轮年-优化版-{suffix}.zip'),
        }
        return [{'id': key, 'title': title, 'filename': path.name, 'bytes': path.stat().st_size,
                 'private': key == 'bundle'} for key, (title, path) in candidates.items()
                if self._safe(path).is_file()]

    def artifact_path(self, run_id, artifact_id):
        # Construct only known paths, never interpret request text as a file path.
        run, paper, review, suffix = self._paths(run_id)
        paths = {'paper': paper/'paper.pdf', 'latex': paper/'paper.tex', 'manuscript': paper/'paper.md',
                 'resources': paper/'resources.json', 'results': run/'results.jsonl', 'summary': run/'summary.json',
                 'review': review.with_suffix('.txt'), 'review-summary': Path(str(review)+'-summary.json'),
                 'patch': self.root/'submission'/f'空梦轮年-优化版-{suffix}'/'framework_contribution.patch',
                 'bundle': self.root/'submission'/f'空梦轮年-优化版-{suffix}.zip'}
        if artifact_id not in paths:
            raise KeyError('Unknown artifact')
        path = self._safe(paths[artifact_id])
        if not path.is_file():
            raise KeyError('Missing artifact')
        return path

    def overview(self, run_id):
        run, paper, review_base, _ = self._paths(run_id)
        manifest = self._json(run/'manifest.json', {})
        summary = self._json(run/'summary.json', {})
        resources = self._json(paper/'resources.json', {'end_to_end': summary.get('resources', {})})
        if not isinstance(resources.get('end_to_end'), dict):
            raise ValueError('Missing resource ledger')
        methods = summary.get('methods', [])
        if not isinstance(methods, list) or any(not isinstance(row, dict) for row in methods):
            raise ValueError('Invalid method summary')
        for row in methods:
            if any(not isinstance(row.get(key), str) for key in ('split', 'policy')) or any(
                    not isinstance(row.get(key), (int, float)) for key in
                    ('budget', 'tasks', 'exact_correct', 'exact_accuracy', 'actual_total_tokens')):
                raise ValueError('Incomplete method summary')
        review = self._json(Path(str(review_base)+'-summary.json'), {'score': None, 'scale': 10})
        review_path = self._safe(review_base.with_suffix('.txt'))
        raw = review_path.read_text(encoding='utf-8') if review_path.is_file() else ''
        # Feedback controls are UI chrome, not reviewer prose.
        raw = raw.split('\nWe Value Your Feedback')[0]
        dataset = self._json(run/'dataset.json', [])
        files = self.artifacts(run_id)
        paper_path = self._safe(paper/'paper.pdf')
        pdf_hash = hashlib.sha256(paper_path.read_bytes()).hexdigest() if paper_path.is_file() else None
        frozen_hash = review.get('paper_sha256')
        return {
            'id': run_id, 'label': run_id.removeprefix('memory_live_'),
            'model': manifest.get('model'), 'protocol': manifest.get('protocol'),
            'limits': {'tokens': manifest.get('max_total_tokens'), 'main_budget': manifest.get('main_budget', 256)},
            'grid_count': len(manifest.get('grid', [])), 'tasks': len(dataset),
            'test_tasks': sum(t.get('split') == 'test' for t in dataset),
            'dev_tasks': sum(t.get('split') == 'dev' for t in dataset),
            'complete': summary.get('evaluation_complete', False),
            'methods': methods, 'resources': resources,
            'review': {**review, 'text': raw, 'matches_paper': bool(frozen_hash and frozen_hash == pdf_hash)},
            'paper_sha256': pdf_hash,
            'availability': {'summary': bool(summary), 'paper': paper_path.is_file(), 'review': bool(raw)},
            'artifacts': files, 'limitations': manifest.get('limitations', []),
        }

    def cases(self, run_id):
        run = self._run(run_id)
        dataset = {t['id']: t for t in self._json(run/'dataset.json', [])}
        path = self._safe(run/'results.jsonl')
        if not path.is_file(): raise FileNotFoundError('Experiment results artifact missing')
        return [{**row, 'task': dataset.get(row['task_id'])} for line in path.read_text(encoding='utf-8').splitlines()
                if line.strip() for row in [json.loads(line)]]
