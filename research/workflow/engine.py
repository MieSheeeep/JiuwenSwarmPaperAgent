"""Persistent stage orchestration, verified artifacts, review routing and pause."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import uuid

from research.artifacts import digest, save_json

STAGES = ('topic', 'literature', 'question', 'design', 'implementation', 'pilot',
          'experiment', 'analysis', 'writing', 'review', 'export')
REQUIRED = {
    'topic': ('topic', 'constraints'),
    'literature': ('sources', 'comparison', 'limitations'),
    'question': ('question', 'hypothesis', 'source_ids', 'falsification'),
    'design': ('dataset', 'split', 'methods', 'metrics', 'budget', 'acceptance'),
    'implementation': ('adapter', 'version', 'capabilities'),
    'pilot': ('passed', 'diagnostics'),
    'experiment': ('results', 'protocol_hash', 'resources'),
    'analysis': ('metrics', 'claims', 'limitations'),
    'writing': ('title', 'sections', 'evidence_hash', 'references'),
    'review': ('decision', 'issues'),
    'export': ('files', 'checks'),
}


def now():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StageResult:
    payload: dict
    usage: dict = field(default_factory=lambda: {'calls': 0, 'tokens': 0})


@dataclass
class Context:
    stage: str
    inputs: dict
    feedback: list
    directory: Path
    remaining: dict
    tools: object


class Workflow:
    """One workspace per research project. Executors supply science; engine owns state."""
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.state_path = self.directory / 'workflow.json'
        self.state = json.loads(self.state_path.read_text(encoding='utf-8'))
        if self.state.get('schema') != 1:
            raise ValueError('Unsupported workflow schema')

    @classmethod
    def create(cls, directory, topic, *, constraints=None, max_calls=200, max_tokens=250000, max_revisions=2):
        directory = Path(directory).resolve()
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError('A research topic is required')
        if any(type(x) is not int or x <= 0 for x in (max_calls, max_tokens, max_revisions)):
            raise ValueError('Positive integer limits required')
        if directory.exists() and any(directory.iterdir()):
            raise ValueError('New project directory must be empty')
        directory.mkdir(parents=True, exist_ok=True)
        state = {'schema': 1, 'id': uuid.uuid4().hex, 'created_at': now(), 'status': 'ready',
                 'stages': {s: {'status': 'pending', 'attempts': 0} for s in STAGES},
                 'limits': {'calls': max_calls, 'tokens': max_tokens, 'revisions': max_revisions},
                 'usage': {'calls': 0, 'tokens': 0}, 'revisions': 0, 'feedback': [],
                 'pause_requested': False, 'events': []}
        save_json(directory / 'workflow.json', state)
        workflow = cls(directory)
        workflow.accept('topic', StageResult({'topic': topic, 'constraints': constraints or {}}))
        return workflow

    def _save(self, event, **details):
        self.state['events'].append({'time': now(), 'event': event, **details})
        save_json(self.state_path, self.state)

    def artifact(self, stage):
        row = self.state['stages'][stage]
        if row['status'] != 'completed':
            raise ValueError('Stage has no completed artifact: ' + stage)
        value = json.loads((self.directory / row['artifact']).read_text(encoding='utf-8'))
        if digest(value) != row['sha256']:
            raise ValueError('Artifact integrity mismatch: ' + stage)
        expected = {s: self.state['stages'][s].get('sha256') for s in STAGES[:STAGES.index(stage)]}
        if value['inputs'] != expected:
            raise ValueError('Artifact inputs changed: ' + stage)
        return value

    def verify(self):
        for stage in STAGES:
            if self.state['stages'][stage]['status'] == 'completed':
                self.artifact(stage)

    def next_stage(self):
        return next((s for s in STAGES if self.state['stages'][s]['status'] != 'completed'), None)

    def _validate(self, stage, payload):
        if not isinstance(payload, dict) or any(k not in payload for k in REQUIRED[stage]):
            raise ValueError('Missing ' + stage + ' fields: ' + ', '.join(REQUIRED[stage]))
        if stage == 'literature':
            sources = payload['sources']
            if not isinstance(sources, list) or not sources or any(
                not isinstance(p, dict) or not all(p.get(k) for k in ('id', 'title', 'url', 'reading_scope'))
                for p in sources):
                raise ValueError('Literature requires identified sources and reading scope')
        if stage == 'question':
            sources = self.artifact('literature')['payload']['sources']
            if not payload['source_ids'] or not set(payload['source_ids']) <= {s['id'] for s in sources}:
                raise ValueError('Question references unknown literature')
        if stage == 'pilot' and type(payload['passed']) is not bool:
            raise ValueError('Pilot passed must be boolean')
        if stage == 'experiment' and payload['protocol_hash'] != self.state['stages']['design']['sha256']:
            raise ValueError('Experiment must bind frozen design artifact')
        if stage == 'experiment' and not self.artifact('pilot')['payload']['passed']:
            raise ValueError('A passed pilot is required')
        if stage == 'writing':
            if payload['evidence_hash'] != self.state['stages']['analysis']['sha256']:
                raise ValueError('Manuscript must bind current analysis')
            if not isinstance(payload['sections'], list) or not payload['sections']:
                raise ValueError('Manuscript sections required')
        if stage == 'review':
            if payload['decision'] not in ('accept', 'revise', 'stop'):
                raise ValueError('Review decision must be accept, revise or stop')
            if payload['decision'] == 'revise' and payload.get('target') not in STAGES[1:9]:
                raise ValueError('Revision requires a literature-to-writing target')
        if stage == 'export':
            if self.artifact('review')['payload']['decision'] != 'accept':
                raise ValueError('Accepted internal review required for export')
            if not isinstance(payload['checks'], dict) or not payload['checks'] or not all(
                    value is True for value in payload['checks'].values()):
                raise ValueError('Export checks must explicitly pass')
            if not isinstance(payload['files'], dict) or not payload['files']:
                raise ValueError('Export needs files with SHA256 values')
            for name, expected in payload['files'].items():
                path = (self.directory / name).resolve()
                if not path.is_relative_to(self.directory) or not path.is_file():
                    raise ValueError('Export file outside project or absent')
                from research.artifacts import file_digest
                if file_digest(path) != expected:
                    raise ValueError('Export file hash mismatch')

    def accept(self, stage, result):
        if stage != self.next_stage():
            raise ValueError('Stage is out of sequence; expected ' + str(self.next_stage()))
        self.verify()
        self._validate(stage, result.payload)
        usage = result.usage
        if set(usage) != {'calls', 'tokens'} or any(type(v) is not int or v < 0 for v in usage.values()):
            raise ValueError('Known nonnegative usage required')
        if any(self.state['usage'][k]+usage[k] > self.state['limits'][k] for k in usage):
            self.state['status'] = 'budget_exceeded'
            self._save('budget_exceeded', stage=stage, reported_usage=usage)
            raise ValueError('Workflow budget exceeded')
        row = self.state['stages'][stage]
        attempt = row['attempts'] + 1
        artifact = {'stage': stage, 'payload': result.payload, 'usage': usage,
                    'inputs': {s: self.state['stages'][s]['sha256'] for s in STAGES[:STAGES.index(stage)]},
                    'created_at': now()}
        filename = f'artifacts/{stage}-{uuid.uuid4().hex}.json'
        save_json(self.directory / filename, artifact)
        row.update(status='completed', artifact=filename, sha256=digest(artifact), attempts=attempt)
        for key in usage: self.state['usage'][key] += usage[key]
        self.state['status'] = 'ready'
        self._save('stage_completed', stage=stage)
        if stage == 'pilot' and not result.payload['passed']:
            self.state['status'] = 'needs_input'
            self._save('pilot_failed', diagnostics=result.payload['diagnostics'])
        if stage == 'review':
            decision = result.payload['decision']
            if decision == 'stop':
                self.state['status'] = 'needs_input'; self._save('review_stopped')
            elif decision == 'revise':
                if self.state['revisions'] >= self.state['limits']['revisions']:
                    self.state['status'] = 'revision_limit'; self._save('revision_limit')
                else:
                    self.state['revisions'] += 1
                    self.state['feedback'].append({'round': self.state['revisions'], **result.payload})
                    self.invalidate(result.payload['target'], reason='review revision')
        if stage == 'export':
            self.state['status'] = 'completed'; self._save('workflow_completed')

    def invalidate(self, stage, *, reason):
        if stage not in STAGES or not reason:
            raise ValueError('Known stage and reason required')
        for name in STAGES[STAGES.index(stage):]:
            old = self.state['stages'][name]
            self.state['stages'][name] = {'status': 'pending', 'attempts': old['attempts']}
        self.state['status'] = 'ready'
        self._save('invalidated', stage=stage, reason=reason)

    def pause(self):
        self.state['pause_requested'] = True
        self.state['status'] = 'paused'
        self._save('pause_requested')

    def resume(self):
        self.verify()
        if self.state['status'] == 'budget_exceeded':
            raise ValueError('Budget reconciliation required')
        self.state['pause_requested'] = False; self.state['status'] = 'ready'
        self._save('resumed')

    async def run(self, registry, *, until=None):
        if until is not None and until not in STAGES: raise ValueError('Unknown stop stage')
        self.verify()
        while self.next_stage():
            # Reload control flags so a separate pause command takes effect at stage boundaries.
            disk = json.loads(self.state_path.read_text(encoding='utf-8'))
            if disk.get('pause_requested') or self.state['status'] in ('needs_input', 'revision_limit', 'budget_exceeded'):
                self.state = disk; break
            stage = self.next_stage()
            if stage not in registry.handlers:
                self.state['status'] = 'needs_input'
                self._save('missing_executor', stage=stage); break
            if (self.directory/'active.json').exists():
                self.state['status'] = 'needs_input'
                self._save('interrupted_stage_requires_reconciliation', stage=stage); break
            # Exclusive creation prevents two independent runners from starting a paid stage.
            with (self.directory/'active.json').open('x', encoding='utf-8') as stream:
                json.dump({'stage':stage,'started_at':now()},stream)
            self.state['status'] = 'running'; self._save('stage_started',stage=stage)
            context = Context(stage=stage,
                inputs={s:self.artifact(s)['payload'] for s in STAGES[:STAGES.index(stage)]},
                feedback=list(self.state['feedback']),directory=self.directory,
                remaining={k:self.state['limits'][k]-self.state['usage'][k] for k in ('calls','tokens')},
                tools=registry)
            try:
                value = registry.handlers[stage](context)
                result = await value if inspect.isawaitable(value) else value
                if not isinstance(result, StageResult): raise ValueError('Executor must return StageResult')
                self.accept(stage,result)
                (self.directory/'active.json').unlink()
            except Exception as error:
                self.state['status'] = 'needs_input'
                self._save('stage_failed',stage=stage,error_type=type(error).__name__,reason=str(error))
                # Keep active marker: an exception does not prove no billable call occurred.
                break
            if stage == until: break
        return self.status()

    def reconcile(self, *, usage, note):
        """Operator accounting after an interrupted handler; no automatic paid retry."""
        if not note or set(usage) != {'calls','tokens'} or any(type(v) is not int or v<0 for v in usage.values()):
            raise ValueError('Explicit usage and reconciliation note required')
        if not (self.directory/'active.json').exists(): raise ValueError('No interrupted stage')
        for key in usage: self.state['usage'][key] += usage[key]
        (self.directory/'active.json').unlink()
        self.state['status']='ready'
        self._save('reconciled',usage=usage,note=note)

    def status(self):
        return {'id':self.state['id'],'status':self.state['status'],'next_stage':self.next_stage(),
                'usage':self.state['usage'],'limits':self.state['limits'],'revisions':self.state['revisions'],
                'stages':{s:self.state['stages'][s]['status'] for s in STAGES},
                'interrupted':(self.directory/'active.json').exists()}
