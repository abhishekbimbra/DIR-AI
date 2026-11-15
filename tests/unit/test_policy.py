from __future__ import annotations

import pytest

from dir_ai.approval import ApprovalKind
from dir_ai.policy import ApprovalPolicy, PolicyMode


@pytest.mark.parametrize(
    ("mode", "kind", "allowed", "needs_approval"),
    [
        (PolicyMode.ASK_ALL, ApprovalKind.READ, True, True),
        (PolicyMode.ASK_ALL, ApprovalKind.WRITE, True, True),
        (PolicyMode.ASK_ALL, ApprovalKind.EDIT, True, True),
        (PolicyMode.ASK_ALL, ApprovalKind.COMMAND, True, True),
        (PolicyMode.AUTO_READ, ApprovalKind.READ, True, False),
        (PolicyMode.AUTO_READ, ApprovalKind.WRITE, True, True),
        (PolicyMode.AUTO_READ, ApprovalKind.EDIT, True, True),
        (PolicyMode.AUTO_READ, ApprovalKind.COMMAND, True, True),
        (PolicyMode.READ_ONLY, ApprovalKind.READ, True, False),
        (PolicyMode.READ_ONLY, ApprovalKind.WRITE, False, False),
        (PolicyMode.READ_ONLY, ApprovalKind.EDIT, False, False),
        (PolicyMode.READ_ONLY, ApprovalKind.COMMAND, False, False),
    ],
)
def test_decision_matrix(
    mode: PolicyMode, kind: ApprovalKind, allowed: bool, needs_approval: bool
) -> None:
    decision = ApprovalPolicy(mode=mode).decide(kind)
    assert decision.allowed is allowed
    assert decision.requires_approval is needs_approval


def test_default_is_auto_read() -> None:
    assert ApprovalPolicy().mode is PolicyMode.AUTO_READ
