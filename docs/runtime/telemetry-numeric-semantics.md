# Tinyserver telemetry numeric semantics adoption

Status: CURRENT tinyserver adoption note.
Created: 2026-05-24.

## Canonical source

Tinyserver adopts the canonical framework spec:

```text
repo: Bers26/tiny-agent-framework
file: docs/runtime/telemetry-numeric-semantics-v0.1.md
canonical commit at adoption: 50e9654a145ca843fa906292ca7ebfcda4f302c7
```

Do not fork numeric semantics locally.

If the framework spec changes, update this adoption note and affected collector/exporter docs.

## Local scope

Tinyserver applies the canonical numeric semantics to:

```text
ServerGuard Agent RO streams
Prometheus projection
Grafana dashboards
future UI/TG consumers
future supervisor/advisor consumers
```

## Contour labels

Tinyserver uses framework-level metrics with product identity as labels.

Current primary contour:

```text
contour="serverguard"
```

Do not create `serverguard_*` framework-level metric names when `agent_ro_*` plus `contour` is enough.

## First adopters

The first tinyserver/ServerGuard streams that must follow this spec:

```text
network.link.ro
storage.status.ro
service.health.ro
container.status.ro when added
```

## Required fields for status streams

Every status/health stream should expose:

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

Every status-important boolean must have a numeric projection:

```text
true=1
false=0
unknown=-1
```

## Network collector adoption

`network.link.ro` must include numeric projections for at least:

```text
carrier_value
gateway_ping_ok_value
dns_ok_value
state_code
severity_code
freshness_code
operation_state_code
```

Minimum candidate facts:

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
```

## Storage collector adoption

`storage.status.ro` must include numeric projections for at least:

```text
mount_present_value
readonly_value
state_code
severity_code
freshness_code
operation_state_code
```

Minimum candidate facts:

```text
root filesystem
/srv/storage mount
free_bytes
used_bytes
filesystem type
readonly
```

## Container collector adoption

`container.status.ro` must not mount Docker socket inside Agent RO.

Accepted design:

```text
host-generated docker_status.json
collector reads read-only fact file
```

Required numeric projections:

```text
docker_socket_mounted_value=0
containers_unhealthy
state_code
severity_code
freshness_code
operation_state_code
```

## Prometheus adoption

Prometheus projection must use:

```text
agent_ro_state_code{contour="serverguard",stream="network.link"}
agent_ro_severity_code{contour="serverguard",stream="network.link"}
agent_ro_freshness_code{contour="serverguard",stream="network.link"}
agent_ro_operation_state_code{contour="serverguard",stream="network.link"}
```

Sensitive values must not be exported as labels.

## Local rule

Do not start implementing `network.link.ro` until this adoption doc and the canonical framework spec are accepted.
