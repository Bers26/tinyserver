# TASK-TINYSERVER-MVP-000 — Phases

## Phase 0 — Repo/process foundation

Status: mostly done.

DoD:

```text
repo exists
initial commit pushed
project-log exists
AGENTS.md exists
CLAUDE.md exists
required Claude Code skills installed and recorded
```

Current evidence:

```text
6a5bc73 Initialize tinyserver repository
1d02c9d Add project log
93ea63b Add next dialog instructions
8be567c Add Claude Code skills policy
7dc38d1 Record installed Claude Code skills
```

## Phase 1 — Canonical numeric semantics

Repo: `Bers26/tiny-agent-framework`.

Goal: define one numeric telemetry language for all collectors and consumers.

Files:

```text
docs/runtime/telemetry-numeric-semantics-v0.1.md
```

Must include:

```text
boolean true=1 false=0 unknown=-1
state_code OK=0 WARN=1 BAD=2 UNKNOWN=3 STALE=4 ERROR=5 DISABLED=6
severity_code 0 normal, 1 info, 2 warning, 3 degraded, 4 critical, 5 unknown/error
freshness model
operation state model
numeric projection rule
agent_ro_ metric prefix
contour label
examples for power.status.ro, network.link.ro, container.status.ro
```

## Phase 2 — Tinyserver adoption doc

Repo: `Bers26/tinyserver`.

Files:

```text
docs/runtime/telemetry-numeric-semantics.md
```

Goal: reference the framework canonical spec and define local adoption.

Must include:

```text
canonical source = tiny-agent-framework spec
tinyserver/serverguard contour label
first adopters = network.link.ro, storage.status.ro, service.health.ro
```

## Phase 3 — Prometheus/Grafana projection

Files:

```text
docs/runtime/prometheus-projection.md
```

Goal: define how JSON telemetry maps to Prometheus metrics.

Must include:

```text
metric naming
labels policy
numeric mapping
freshness metrics
operation metrics
sensitive data policy
examples
```

## Phase 4 — network.link.ro

Order:

```text
4A read-only network reality inspect
4B design collector fields
4C Codex package for collector/tests
4D Claude Code runtime wiring/proof
4E full registry run proof
```

Minimum fields:

```text
interface
operstate
carrier
speed_mbps
duplex
rx_errors
tx_errors
rx_dropped
tx_dropped
gateway_ping_ok
gateway_ping_ms
dns_ok
wan_hint
vpn_hint
state/state_code
severity/severity_code
freshness/freshness_code
operation_state
```

## Phase 5 — storage.status.ro

Goal: prove local disk/mount state.

Minimum fields:

```text
root filesystem
/srv/storage mount
free/used
readonly flag
filesystem type
state/state_code
severity/severity_code
freshness
```

## Phase 6 — service.health.ro

Goal: monitor key services without actions.

Minimum targets:

```text
serverguard API/UI
filebrowser
CUPS
agent-ro timer
apcupsd when relevant
```

## Phase 7 — container.status.ro design/proof

Rule:

```text
no docker.sock in Agent RO
host-generated docker_status.json
collector reads read-only fact file
```

## Phase 8 — runtime proof and MVP closure

DoD:

```text
full registry run executes baseline + new streams
latest snapshots validate
history snapshots validate
timer refresh verified
Prometheus projection examples validate
worktree clean
remote main synced
project-log updated
MVP closure doc committed
```
