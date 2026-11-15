"""Approval policy: which operations need approval and which are denied."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dir_ai.approval import ApprovalKind


class PolicyMode(StrEnum):
    ASK_ALL = "ask-all"
    AUTO_READ = "auto-read"
    READ_ONLY = "read-only"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool


@dataclass(frozen=True, slots=True)
class ApprovalPolicy:
    mode: PolicyMode = PolicyMode.AUTO_READ

    def decide(self, kind: ApprovalKind) -> PolicyDecision:
        if kind is ApprovalKind.READ:
            return PolicyDecision(
                allowed=True,
                requires_approval=self.mode is PolicyMode.ASK_ALL,
            )
        if self.mode is PolicyMode.READ_ONLY:
            return PolicyDecision(allowed=False, requires_approval=False)
        return PolicyDecision(allowed=True, requires_approval=True)
