"""Base classes and schemas for the Multi-Agent QA Swarm.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AuditResult:
    agent_id: str
    agent_name: str
    passed: bool
    score: float
    max_score: float = 20.0
    summary: str = ""
    details: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "passed": self.passed,
            "score": self.score,
            "max_score": self.max_score,
            "summary": self.summary,
            "details": self.details,
            "metrics": self.metrics,
        }


class BaseAuditAgent(ABC):
    """Abstract base class for all QA Swarm specialized audit agents."""

    def __init__(self, agent_id: str, agent_name: str, max_score: float = 20.0) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.max_score = max_score

    @abstractmethod
    def run(self) -> AuditResult:
        """Executes the specific audit checks and returns an AuditResult."""
        pass
