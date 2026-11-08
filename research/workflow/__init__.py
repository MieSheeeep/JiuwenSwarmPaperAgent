"""Topic-independent workflow control; no network or model calls on import."""
from .engine import Workflow, StageResult, STAGES
from .registry import Registry
from .gates import TopicGate, TopicCandidate, PilotGate, PilotDecision
from .conference_review import ConferenceReviewPanel, ReviewerReport
from .acceptance import StructuredAcceptance
from .tournament import TopicTournament, TournamentResult, AutonomousResearchOrchestrator
from .deep_revision import DeepRevisionManager, RevisionPlan

__all__ = [
    'Workflow', 'StageResult', 'STAGES', 'Registry',
    'TopicGate', 'TopicCandidate', 'PilotGate', 'PilotDecision',
    'ConferenceReviewPanel', 'ReviewerReport',
    'StructuredAcceptance',
    'TopicTournament', 'TournamentResult', 'AutonomousResearchOrchestrator',
    'DeepRevisionManager', 'RevisionPlan'
]
