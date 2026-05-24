# TASK-TINYSERVER-MVP-000 — Acceptance

## MVP acceptance checklist

Tinyserver MVP is complete only when all items below are true.

```text
[ ] repo governance ready
[ ] project-log maintained in docs/project-log
[ ] AGENTS.md current
[ ] CLAUDE.md current
[ ] required Claude Code skills recorded
[ ] canonical numeric semantics exists in tiny-agent-framework
[ ] tinyserver adoption doc references canonical numeric spec
[ ] Prometheus projection spec exists
[ ] network.link.ro design complete
[ ] network.link.ro implementation/tests complete
[ ] network.link.ro runtime proof accepted
[ ] storage.status.ro implementation/tests or accepted design proof complete
[ ] service.health.ro implementation/tests or accepted design proof complete
[ ] container.status.ro boundary design accepted
[ ] full registry proof collected
[ ] latest/history snapshots validate
[ ] project-log updated after every accepted phase
[ ] worktree clean
[ ] remote main synced
[ ] final MVP closure doc committed
```

## Per-task acceptance criteria

Every technical task must include:

```text
Tier
Scope
Forbidden
DoD
Files to update
Tests
Rollback
Executor
Acceptance criteria
```

## Collector acceptance criteria

A collector is accepted only if it has:

```text
stable output fields
state/state_code
severity/severity_code
freshness/freshness_code
operation_state
schema or contract validation
fixture or unit tests
latest snapshot validation
history snapshot validation when wired
registry integration proof
no actions
no secrets
no root dependency unless explicitly scoped
```

## Runtime proof acceptance criteria

Runtime proof is accepted only if it shows:

```text
actual registry used
actual modules-dir used
enabled streams listed
executed count
skipped count
latest snapshot paths
history snapshot paths
validation results
timer/service status when applicable
no valid action token used in read-only proof
```

## Prometheus/Grafana acceptance criteria

Prometheus projection is accepted only if:

```text
all status-important fields have numeric projection
metric names use agent_ro_ prefix
product identity is expressed by contour label
sensitive values are not exported as labels
examples exist for power, network and container streams
```
