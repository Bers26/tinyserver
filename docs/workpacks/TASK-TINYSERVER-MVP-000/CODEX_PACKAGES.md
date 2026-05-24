# TASK-TINYSERVER-MVP-000 — Codex Packages

Codex is used only for code/API/tests inside repo.

Do not use Codex for local runtime wiring, Docker, VPN, secrets or deploy.

## CODEX-PKG-001 — network.link.ro collector

Prerequisites:

```text
canonical numeric semantics accepted
tinyserver adoption doc accepted
network reality inspect completed
collector design accepted
```

Scope:

```text
implement network.link.ro collector and tests
```

Forbidden:

```text
runtime wiring
Docker/VPN changes
secrets
systemd/timer changes
push without tests
```

Acceptance criteria:

```text
collector emits required fields
state_code/severity_code match numeric semantics
fixtures added
tests pass
no actions/no secrets
```

## CODEX-PKG-002 — storage.status.ro collector

Prerequisites:

```text
storage design accepted
mount paths verified by Claude Code read-only inspect
```

Scope:

```text
implement storage.status.ro collector and tests
```

Acceptance criteria:

```text
root filesystem state emitted
/srv/storage state emitted
readonly/free/used fields present
numeric projection present
fixtures/tests pass
```

## CODEX-PKG-003 — service.health.ro collector

Prerequisites:

```text
service list accepted
read-only endpoints/status checks designed
```

Scope:

```text
implement service.health.ro collector and tests
```

Acceptance criteria:

```text
service checks are read-only
state_code/severity_code present
fixtures/tests pass
no restart/no action
```

## CODEX-PKG-004 — Prometheus exporter/projection

Prerequisites:

```text
prometheus-projection.md accepted
sample telemetry snapshots available
vibesec review requested before production exposure
```

Scope:

```text
implement deterministic JSON to Prometheus projection if tinyserver owns exporter code
```

Acceptance criteria:

```text
agent_ro_ prefix
contour label
no secrets/sensitive labels
numeric values only for primary signal
tests pass
```
