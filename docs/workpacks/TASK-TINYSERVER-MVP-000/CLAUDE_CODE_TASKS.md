# TASK-TINYSERVER-MVP-000 — Claude Code Tasks

Claude Code is used for local OS, config, runtime and repo operations.

Required global skills:

```text
systematic-debugging
writing-plans
vibesec
```

## CLAUDE-TASK-001 — local repo state verify

Scope:

```text
read-only verify local tinyserver, tiny-agent-framework and serverguard clones
```

Forbidden:

```text
file changes
runtime changes
push
secrets
```

DoD:

```text
branch/head/status reported for each repo
remote verified
no dirty tree ignored
```

## CLAUDE-TASK-002 — numeric semantics placement inspect

Repo: `tiny-agent-framework`.

Scope:

```text
read docs/runtime, schemas, fixtures and tests enough to choose placement for telemetry-numeric-semantics-v0.1.md
```

Forbidden:

```text
code changes
schema changes
runtime changes
```

DoD:

```text
recommended file path and affected follow-up docs listed
```

## CLAUDE-TASK-003 — network reality inspect

Scope:

```text
read-only inspect interfaces, routes, DNS, gateway and VPN hints
```

Forbidden:

```text
VPN switch
network restart
DHCP/routing changes
valid action token
```

DoD:

```text
facts captured for network.link.ro design
no runtime mutation
```

## CLAUDE-TASK-004 — runtime wiring for accepted collector

Prerequisites:

```text
collector code/tests accepted
registry target identified
rollback plan ready
```

Scope:

```text
wire one collector into registry/runtime
```

Forbidden:

```text
secrets
Docker socket
VPN/DHCP changes
multiple collectors in one task
```

DoD:

```text
full registry run executes new stream
latest/history snapshots validate
previous streams still run
```

## CLAUDE-TASK-005 — vibesec security review before exporter/API exposure

Scope:

```text
use vibesec workflow to review security-sensitive changes
```

Apply before:

```text
Prometheus exporter production exposure
API/auth changes
operator adapters
Docker/runtime boundary changes
```

DoD:

```text
findings recorded
accepted fixes or explicit risk acceptance documented
```
