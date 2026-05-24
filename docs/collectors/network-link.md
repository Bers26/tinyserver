# network.link.ro design

Status: DRAFT pending live read-only network inspect.
Created: 2026-05-24.

## Purpose

`network.link.ro` is the first ServerGuard expansion stream after the v0.1 baseline streams.

It must describe local link, gateway and basic DNS/WAN reachability without mutating networking, VPN, Docker, DHCP, routing or system services.

## Canonical dependencies

```text
Bers26/tiny-agent-framework: docs/runtime/telemetry-numeric-semantics-v0.1.md
Bers26/tinyserver: docs/runtime/telemetry-numeric-semantics.md
Bers26/tinyserver: docs/runtime/prometheus-projection.md
```

## Status boundary

This file is not an accepted implementation design yet.

It becomes accepted only after live read-only network inspect confirms:

```text
primary interface name
route/gateway shape
available local commands
DNS check method
VPN diagnostic hints that are safe to read
expected output paths and runtime registry target
```

## Required read-only inspect

Executor: Claude Code or manual SSH block while Claude Code is unavailable.

Forbidden during inspect:

```text
network restart
VPN switch
DHCP changes
routing changes
systemd changes
Docker changes
valid action token
/api/actions/*
secrets/.env
```

Facts to capture:

```text
hostname
kernel/network tools availability
ip -json link
ip -json addr
ip route
resolvectl status or /etc/resolv.conf summary
primary interface
primary gateway
default route device
carrier
operstate
speed_mbps
duplex
rx_errors
tx_errors
rx_dropped
tx_dropped
gateway ping result and latency
DNS resolve result for fixed safe domains
VPN interface hints if visible without secrets
current Agent RO registry truth
```

## Candidate stream id

```text
agent_id: network.link.ro
stream: network.link
contour: serverguard
```

Current framework v0.1 still stores stream identity as `agent_id` in snapshots. Prometheus may expose it as `stream="network.link"`.

## Candidate collector facts

```text
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
gateway_ping_ms
dns_ok
dns_ok_value
dns_checked_domains_count
dns_success_count
wan_hint
vpn_hint
```

Do not expose raw resolver addresses, public IPs, VPN server names or private hostnames as Prometheus labels by default.

## Required status fields

```text
agent_id
collected_at
state
state_code
severity
severity_code
freshness
freshness_code
operation_state
operation_state_code
```

## Candidate state mapping

Initial mapping, pending live inspect:

```text
OK:
  carrier=true
  operstate=up
  gateway_ping_ok=true
  dns_ok=true

WARN:
  carrier=true and operstate=up, but DNS fails
  carrier=true and gateway ping fails, but DNS still works
  link speed lower than expected but usable
  rx/tx errors or drops increased above small threshold

BAD:
  carrier=false
  operstate=down
  no default gateway
  gateway ping fails and DNS fails

UNKNOWN:
  required commands unavailable
  interface cannot be determined
  gateway cannot be determined and no safe fallback exists

ERROR:
  collector exception or parse failure

STALE:
  latest sample exists but freshness policy expired
```

## Severity mapping

Initial mapping, pending live inspect:

```text
normal=0 for OK
warning=2 for WARN
degraded=3 for BAD-but-local-link-present
critical=4 for no carrier or no default route
unknown_or_error=5 for UNKNOWN/ERROR
```

## Operation model

Normal successful collector run:

```text
operation_state=completed
operation_state_code=6
```

Timeout:

```text
operation_state=timed_out
operation_state_code=4
state may remain last known state if writer/runtime supports that distinction
freshness must show stale/expired when applicable
```

## Prometheus projection

Expected metrics are defined in `docs/runtime/prometheus-projection.md`:

```text
agent_ro_network_carrier_value
agent_ro_network_speed_mbps
agent_ro_network_rx_errors_total
agent_ro_network_tx_errors_total
agent_ro_network_rx_dropped_total
agent_ro_network_tx_dropped_total
agent_ro_network_gateway_ping_ok_value
agent_ro_network_gateway_ping_ms
agent_ro_network_dns_ok_value
```

Required base metrics:

```text
agent_ro_state_code
agent_ro_severity_code
agent_ro_freshness_code
agent_ro_operation_state_code
agent_ro_age_seconds
```

## Codex package gate

Do not write collector code until:

```text
live inspect accepted
field list accepted
state mapping accepted
runtime target accepted
fixtures planned
rollback plan ready
```

## Runtime gate

Do not wire runtime until:

```text
collector code/tests accepted
registry target confirmed
module manifest path confirmed
full rollback plan ready
```

## Next step

Run live read-only network inspect and update this file from DRAFT to ACCEPTED DESIGN only if facts support it.
