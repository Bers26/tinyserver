# TASK-TINYSERVER-MVP-000 — Tinyserver MVP Workpack

Status: DRAFT workpack.
Created: 2026-05-24.
Repo: `Bers26/tinyserver`.

## Goal

Bring `tinyserver` to MVP as a small managed home-server platform, not a pile of scripts.

MVP means:

- repo governance is stable;
- project log is repo-native;
- Agent RO boundary is explicit;
- numeric telemetry semantics are defined canonically;
- Prometheus/Grafana projection is designed;
- first real ServerGuard telemetry streams are designed and proven;
- runtime proof is collected before closure.

## Execution model

Use staged tasks, not one giant mutation.

```text
ChatGPT = planning, task packaging, review, synthesis
Claude Code = local OS/config/runtime/repo operations
Codex = code/API/tests inside repo
GitHub connector = docs-only branch/PR work while local executor is unavailable
```

## Current baseline

```text
tinyserver main: 7dc38d1 Record installed Claude Code skills
project log: docs/project-log/
required Claude Code skills: systematic-debugging, writing-plans, vibesec
```

## Read before work

```text
docs/project-log/NEXT_DIALOG_INSTRUCTIONS.md
docs/project-log/ERRORS.md
docs/project-log/PREVENTION_RULES.md
docs/project-log/DECISIONS.md
docs/project-log/TASKS.md
```

## Immediate next task after this workpack

```text
TASK-SG-DESIGN-001A
Add canonical telemetry numeric semantics to Bers26/tiny-agent-framework.
```
