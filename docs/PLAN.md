# Backend plan (committed summary)

The detailed plans are kept in `plans/` on the development machine. This file
records the committed contract and checkpoint order.

## Checkpoints

| Checkpoint | Scope | Gate tag |
| --- | --- | --- |
| CP0 | Baseline, packaging, config, test harness | `cp0-done` |
| CP1 | Sandbox hardening | `cp1-done` |
| CP2 | Typed tool layer | `cp2-done` |
| CP3 | Approval and policy engine | `cp3-done` |
| CP4 | Typed event stream | `cp4-done` |
| CP5 | Provider abstraction | `cp5-done` |
| CP6 | Native tool-calling agent loop | `cp6-done` |
| CP7 | Command execution | `cp7-done` |
| CP8 | Project context | `cp8-done` |
| CP9 | WebSocket server protocol | `cp9-done` |

## Rules

1. A checkpoint starts only after the previous gate passes.
2. Regression never touches the network. Scripted fake models, temp dirs, and
   mocked HTTP only.
3. Each gate runs every earlier test.
4. New ideas go to `docs/BACKLOG.md`; plan changes go to
   `docs/PLAN_CHANGES.md`.
5. Every gate is committed and tagged `cpN-done`.
