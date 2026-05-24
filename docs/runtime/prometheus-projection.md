# Prometheus projection for Tinyserver Agent RO

Status: DRAFT tinyserver projection spec.
Created: 2026-05-24.

## Canonical dependency

This document applies the framework numeric semantics from:

```text
repo: Bers26/tiny-agent-framework
file: docs/runtime/telemetry-numeric-semantics-v0.1.md
canonical adoption in tinyserver: docs/runtime/telemetry-numeric-semantics.md
```

## Purpose

Prometheus and Grafana need numeric, low-cardinality, stable metrics.

Agent RO snapshots may contain rich JSON facts for UI, Telegram, supervisor and diagnostics. Prometheus projection must extract only the stable numeric signals needed for dashboards and alerts.

## Non-goals

This document does not implement:

```text
exporter code
Grafana dashboard JSON
alert rules
runtime wiring
collector code
```

## Metric prefix

Use the framework-level prefix:

```text
agent_ro_
```

Do not create framework-level metrics named `serverguard_*` when labels can identify the contour.

## Required labels

Every projected metric should include:

```text
contour="serverguard"
stream="<stream>"
```

Examples:

```text
contour="serverguard"
stream="network.link"
```

Use `agent_id` only when preserving legacy runtime identity is necessary.

## Label policy

Allowed labels:

```text
contour
stream
interface
mount
service
collector
```

Allowed only when low-cardinality and non-sensitive:

```text
device
ups_model
filesystem_type
```

Forbidden labels:

```text
secrets
tokens
raw private paths
IP addresses unless explicitly approved
hostnames unless explicitly approved
URLs with credentials
error text
command output
user data
high-cardinality dynamic values
```

Rule: if a value can explode cardinality or leak private context, it is a sample value or log detail, not a Prometheus label.

## Base stream metrics

Every status stream should project these metrics:

```text
agent_ro_state_code{contour="serverguard",stream="..."}
agent_ro_severity_code{contour="serverguard",stream="..."}
agent_ro_freshness_code{contour="serverguard",stream="..."}
agent_ro_operation_state_code{contour="serverguard",stream="..."}
agent_ro_age_seconds{contour="serverguard",stream="..."}
```

Optional but useful:

```text
agent_ro_collected_timestamp_seconds{contour="serverguard",stream="..."}
agent_ro_operation_elapsed_seconds{contour="serverguard",stream="..."}
```

## Boolean projection

Use the framework boolean model:

```text
true=1
false=0
unknown=-1
```

Examples:

```text
agent_ro_network_carrier_value{contour="serverguard",stream="network.link",interface="enp6s0"} 1
agent_ro_network_gateway_ping_ok_value{contour="serverguard",stream="network.link"} 1
agent_ro_network_dns_ok_value{contour="serverguard",stream="network.link"} 1
agent_ro_storage_readonly_value{contour="serverguard",stream="storage.status",mount="/srv/storage"} 0
```

## State projection

Use framework state codes:

```text
OK=0
WARN=1
BAD=2
UNKNOWN=3
STALE=4
ERROR=5
DISABLED=6
```

Example:

```text
agent_ro_state_code{contour="serverguard",stream="network.link"} 0
```

## Severity projection

Use framework severity codes:

```text
normal=0
info=1
warning=2
degraded=3
critical=4
unknown_or_error=5
```

Example:

```text
agent_ro_severity_code{contour="serverguard",stream="storage.status"} 2
```

## Freshness projection

Use framework freshness codes:

```text
fresh=0
aging=1
stale=2
expired=3
unknown=4
```

Examples:

```text
agent_ro_freshness_code{contour="serverguard",stream="network.link"} 0
agent_ro_age_seconds{contour="serverguard",stream="network.link"} 12
```

Rule: dashboards must show stale/expired data even when the last known state was OK.

## Operation projection

Use framework operation state codes:

```text
idle=0
queued=1
running=2
slow=3
timed_out=4
failed=5
completed=6
unknown=7
```

Examples:

```text
agent_ro_operation_state_code{contour="serverguard",stream="network.link"} 6
agent_ro_operation_elapsed_seconds{contour="serverguard",stream="network.link"} 0.18
```

Rule: a timed-out refresh is not proof that the monitored service is BAD. It means current verification failed or is missing.

## network.link metrics

Minimum projection:

```text
agent_ro_network_carrier_value{contour="serverguard",stream="network.link",interface="enp6s0"}
agent_ro_network_speed_mbps{contour="serverguard",stream="network.link",interface="enp6s0"}
agent_ro_network_rx_errors_total{contour="serverguard",stream="network.link",interface="enp6s0"}
agent_ro_network_tx_errors_total{contour="serverguard",stream="network.link",interface="enp6s0"}
agent_ro_network_rx_dropped_total{contour="serverguard",stream="network.link",interface="enp6s0"}
agent_ro_network_tx_dropped_total{contour="serverguard",stream="network.link",interface="enp6s0"}
agent_ro_network_gateway_ping_ok_value{contour="serverguard",stream="network.link"}
agent_ro_network_gateway_ping_ms{contour="serverguard",stream="network.link"}
agent_ro_network_dns_ok_value{contour="serverguard",stream="network.link"}
```

Do not expose raw DNS resolver addresses as labels by default.

## storage.status metrics

Minimum projection:

```text
agent_ro_storage_mount_present_value{contour="serverguard",stream="storage.status",mount="/srv/storage"}
agent_ro_storage_readonly_value{contour="serverguard",stream="storage.status",mount="/srv/storage"}
agent_ro_storage_free_bytes{contour="serverguard",stream="storage.status",mount="/srv/storage"}
agent_ro_storage_used_bytes{contour="serverguard",stream="storage.status",mount="/srv/storage"}
agent_ro_storage_size_bytes{contour="serverguard",stream="storage.status",mount="/srv/storage"}
agent_ro_storage_used_ratio{contour="serverguard",stream="storage.status",mount="/srv/storage"}
```

Mount labels are allowed only for approved stable monitored mount points.

## service.health metrics

Minimum projection:

```text
agent_ro_service_up_value{contour="serverguard",stream="service.health",service="agent-ro-registry.timer"}
agent_ro_service_state_code{contour="serverguard",stream="service.health",service="agent-ro-registry.timer"}
agent_ro_service_severity_code{contour="serverguard",stream="service.health",service="agent-ro-registry.timer"}
```

Service labels must come from a fixed allowlist, not runtime discovery spam.

## container.status metrics

Agent RO must not mount Docker socket.

Projection must come from host-generated read-only facts.

Minimum projection:

```text
agent_ro_container_running_count{contour="serverguard",stream="container.status"}
agent_ro_container_unhealthy_count{contour="serverguard",stream="container.status"}
agent_ro_container_docker_socket_mounted_value{contour="serverguard",stream="container.status"} 0
```

Container names as labels are allowed only from an explicit allowlist.

## Exporter behavior

The exporter should be dumb and deterministic:

```text
read latest snapshots
apply numeric projection rules
emit metrics
never mutate runtime
never call actions
never read secrets
never infer missing contract fields silently
```

If a required numeric field is absent:

```text
export agent_ro_projection_error_value 1
record projection error in logs/output
keep the original Agent RO snapshot unchanged
```

## Dashboard behavior

Grafana dashboards should separate:

```text
last known data state
data freshness
current operation state
severity
```

Do not show stale OK as current OK.

## Review rule

Before exporter production exposure, run `vibesec` review because exporter/API boundaries may expose telemetry outside the local process.

## Next step

After this spec is accepted:

```text
TASK-SG-DESIGN-003
Design network.link.ro collector from real read-only network state.
```
