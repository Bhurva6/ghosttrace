"""GhostTrace: replay synthetic incident logs, keep evidence apart from hypotheses."""
from .engine import analyze, load_events
__all__ = ["analyze", "load_events"]
