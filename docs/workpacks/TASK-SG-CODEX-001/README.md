# TASK-SG-CODEX-001 — network.link.ro collector and tests

Status: READY FOR CODEX.
Created: 2026-05-24.
Executor: Codex.

## Tier

2

## Scope

Implement `network.link.ro` collector and unit tests inside `tinyserver` repo.

## Forbidden

```text
runtime wiring
systemd changes
Docker changes
VPN changes
DHCP/routing changes
secrets
.env
SSH keys
/api/actions/*
valid action token smoke
writes outside repo
actions or operator adapters
```

## DoD

```text
collector source exists
unit tests exist
fixtures for OK, WARN, BAD, UNKNOWN, ERROR exist
state_code/severity_code follow accepted design
boolean projections follow true=1 false=0 unknown=-1
collector is read-only
pytest passes
git diff --check passes
no runtime registry/module wiring
```

## Files to update

Recommended minimal repo structure:

```text
pyproject.toml
src/tinyserver_collectors/__init__.py
src/tinyserver_collectors/network_link.py
tests/test_network_link.py
tests/fixtures/network_link/ok.json
tests/fixtures/network_link/warn_loss.json
tests/fixtures/network_link/bad_loss.json
tests/fixtures/network_link/unknown.json
tests/fixtures/network_link/error.json
docs/project-log/TASKS.md
```

If Codex chooses different Python package names, it must keep names clear and update tests accordingly.

## Tests

```text
python -m pytest
python -m compileall src tests
git diff --check
```

## Rollback

Revert the code PR. No runtime wiring is allowed in this task.

## Canonical inputs

Read before coding:

```text
AGENTS.md
docs/project-log/ERRORS.md
docs/project-log/PREVENTION_RULES.md
docs/project-log/DECISIONS.md
docs/project-log/TASKS.md
docs/runtime/telemetry-numeric-semantics.md
docs/runtime/prometheus-projection.md
docs/collectors/network-link.md
```

## Accepted stream identity

```text
agent_id: network.link.ro
stream: network.link
contour: serverguard
```

## Required output fields

Collector output must include:

```text
agent_id
collected_at
interface
operstate
carrier
carrier_value
speed_mbps
duplex
rx_errors
tx_errors
rx_dropped
tx_dropped
gateway_ip_present
gateway_ip_present_value
gateway_ping_ok
gateway_ping_ok_value
gateway_ping_ms_min
gateway_ping_ms_avg
gateway_ping_ms_max
gateway_ping_loss_percent
dns_ok
dns_ok_value
dns_checked_domains_count
dns_success_count
dns_github_ok_value
dns_google_ok_value
dns_telegram_ok_value
vpn_interface_present
vpn_interface_present_value
vpn_dns_present
vpn_dns_present_value
wan_hint
vpn_hint
state
state_code
severity
severity_code
freshness
freshness_code
operation_state
operation_state_code
```

## Numeric constants

```text
boolean true=1 false=0 unknown=-1
state OK=0 WARN=1 BAD=2 UNKNOWN=3 STALE=4 ERROR=5 DISABLED=6
severity normal=0 info=1 warning=2 degraded=3 critical=4 unknown_or_error=5
freshness fresh=0 aging=1 stale=2 expired=3 unknown=4
operation completed=6 timed_out=4 failed=5 unknown=7
```

## Accepted state mapping

```text
OK:
  carrier=true
  operstate=up
  gateway_ping_loss_percent=0
  gateway_ping_ok=true
  dns_success_count>=1

WARN:
  carrier=true and operstate=up, but dns_success_count=0
  carrier=true and gateway_ping_loss_percent>0 and <=5
  gateway_ping_ms_max>=100 and <1000
  speed_mbps is lower than expected but link is usable
  tx_errors/rx_errors increased but gateway and DNS still mostly work

BAD:
  carrier=false
  operstate=down
  no default gateway
  gateway_ping_loss_percent>5
  gateway ping fails and DNS fails
  gateway_ping_ms_max>=1000 in the sampled window

UNKNOWN:
  required commands unavailable
  interface cannot be determined
  gateway cannot be determined and no safe fallback exists

ERROR:
  collector exception or parse failure
```

## Implementation guidance

Recommended approach:

```text
1. Write pure mapping functions first.
2. Test mapping functions with fixtures.
3. Keep shell command execution behind injectable helpers.
4. Use bounded commands only.
5. Do not mutate anything.
6. Do not wire runtime.
```

Suggested module functions:

```text
bool_value(value) -> int
classify_state(facts) -> tuple[state, state_code, severity, severity_code]
build_snapshot(facts, collected_at=None) -> dict
collect_network_link(command_runner=..., timeout=...) -> dict
```

The tests should focus on `build_snapshot` and `classify_state`. Runtime command execution can be lightly tested with fake command output, not real network dependencies.

## Important caveat

The local network showed intermittent packet loss before the accepted design was written. Do not assume that a single successful gateway ping means the LAN is stable. The collector must preserve loss percent and max latency.
