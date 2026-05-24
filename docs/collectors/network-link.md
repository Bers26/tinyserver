# network.link.ro design

Status: ACCEPTED DESIGN, pending implementation.
Created: 2026-05-24.
Accepted from factual inspect: SGTS-067.

## Purpose

`network.link.ro` is the first ServerGuard expansion stream after the v0.1 baseline streams.

It describes local link, gateway and basic DNS/WAN reachability without mutating networking, VPN, Docker, DHCP, routing or system services.

## Canonical dependencies

```text
Bers26/tiny-agent-framework: docs/runtime/telemetry-numeric-semantics-v0.1.md
Bers26/tinyserver: docs/runtime/telemetry-numeric-semantics.md
Bers26/tinyserver: docs/runtime/prometheus-projection.md
```

## Factual inspect summary

SGTS-067 collected current facts from the server.

Observed baseline:

```text
host=agent
primary_interface=enp6s0
primary_gateway=10.1.1.1
default_route=default via 10.1.1.1 dev enp6s0 proto static
address=10.1.1.10/24
operstate=up
carrier=1
speed_mbps=100
duplex=full
mtu=1500
rx_errors=0
tx_errors=4
rx_dropped=0
tx_dropped=0
gateway_ping_60_packets=0_percent_loss
external_ping_1.1.1.1_10_packets=0_percent_loss
dns_github_rc=0
dns_google_rc=2
dns_telegram_rc=0
resolver_primary_enp6s0=1.1.1.1
resolver_enp6s0_servers=10.1.1.1,1.1.1.1,8.8.8.8
vpn_interface=tun0
vpn_dns=172.19.0.2
systemd_networkd=active
systemd_resolved=active
NetworkManager=inactive
```

Important caveat:

```text
Earlier long-running pings showed intermittent local packet loss:
Windows -> 10.1.1.1: about 4 percent loss, max latency about 3903 ms
Windows -> 10.1.1.10: about 4 percent loss, max latency about 3494 ms
server -> 10.1.1.1 earlier sample: about 25.88 percent loss
SGTS-067 short bounded sample later showed 0 percent loss to gateway.
```

Conclusion: the collector must detect intermittent degradation, not only current link-down state.

## Stream identity

```text
agent_id: network.link.ro
stream: network.link
contour: serverguard
```

Current framework v0.1 stores stream identity as `agent_id`. Prometheus may expose it as `stream="network.link"`.

## Accepted collector facts

Required facts:

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

STALE:
  latest sample exists but freshness policy expired
```

## Accepted severity mapping

```text
normal=0 for OK
warning=2 for WARN
degraded=3 for BAD with carrier still present
critical=4 for no carrier, no default route, or heavy gateway loss
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

Expected metrics are defined in `docs/runtime/prometheus-projection.md`.

Required network metrics:

```text
agent_ro_network_carrier_value
agent_ro_network_speed_mbps
agent_ro_network_rx_errors_total
agent_ro_network_tx_errors_total
agent_ro_network_rx_dropped_total
agent_ro_network_tx_dropped_total
agent_ro_network_gateway_ping_ok_value
agent_ro_network_gateway_ping_ms
agent_ro_network_gateway_ping_loss_percent
agent_ro_network_dns_ok_value
agent_ro_network_dns_success_count
agent_ro_network_vpn_interface_present_value
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

Collector code may be drafted after this accepted design.

Codex package must include:

```text
collector source
unit tests for state mapping
fixtures for OK, WARN, BAD, UNKNOWN, ERROR
no runtime wiring
no secrets
no network mutation
no Docker/VPN/systemd control
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

Create Codex package for `network.link.ro` collector and tests.
