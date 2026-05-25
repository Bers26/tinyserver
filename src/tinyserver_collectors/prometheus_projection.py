"""Prometheus text projection for Agent RO latest snapshots.

Reads a registry and latest JSON snapshots, projects numeric values, and emits
Prometheus text exposition. It does not mutate runtime state and does not call
collectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
FRESHNESS_UNKNOWN = 4
OPERATION_UNKNOWN = 7

NETWORK_METRIC_NAMES = {
    "carrier_value": "agent_ro_network_carrier_value",
    "speed_mbps": "agent_ro_network_speed_mbps",
    "rx_errors": "agent_ro_network_rx_errors_total",
    "tx_errors": "agent_ro_network_tx_errors_total",
    "rx_dropped": "agent_ro_network_rx_dropped_total",
    "tx_dropped": "agent_ro_network_tx_dropped_total",
    "gateway_ip_present_value": "agent_ro_network_gateway_ip_present_value",
    "gateway_ping_ok_value": "agent_ro_network_gateway_ping_ok_value",
    "gateway_ping_loss_percent": "agent_ro_network_gateway_ping_loss_percent",
    "gateway_ping_ms_min": "agent_ro_network_gateway_ping_ms_min",
    "gateway_ping_ms_avg": "agent_ro_network_gateway_ping_ms_avg",
    "gateway_ping_ms_max": "agent_ro_network_gateway_ping_ms_max",
    "dns_ok_value": "agent_ro_network_dns_ok_value",
    "dns_checked_domains_count": "agent_ro_network_dns_checked_domains_count",
    "dns_success_count": "agent_ro_network_dns_success_count",
    "dns_github_ok_value": "agent_ro_network_dns_github_ok_value",
    "dns_google_ok_value": "agent_ro_network_dns_google_ok_value",
    "dns_telegram_ok_value": "agent_ro_network_dns_telegram_ok_value",
    "vpn_interface_present_value": "agent_ro_network_vpn_interface_present_value",
    "vpn_dns_present_value": "agent_ro_network_vpn_dns_present_value",
}

RESERVED_METRIC_KEYS = {"freshness_code", "operation_state_code"}


@dataclass(frozen=True)
class ProjectedMetric:
    name: str
    labels: dict[str, str]
    value: int | float


def render_prometheus_from_registry(
    registry_path: str | Path,
    *,
    now: datetime | None = None,
    contour: str = "serverguard",
) -> str:
    current = now or datetime.now(timezone.utc)
    metrics = list(project_registry(Path(registry_path), now=current, contour=contour))
    return render_prometheus(metrics)


def project_registry(registry_path: Path, *, now: datetime, contour: str) -> Iterable[ProjectedMetric]:
    registry = _read_json(registry_path)
    if not isinstance(registry, dict):
        yield _projection_error(contour, "unknown", 1)
        return

    agents = registry.get("agents")
    if not isinstance(agents, list):
        yield _projection_error(contour, "unknown", 1)
        return

    base_dir = registry_path.parent
    for entry in agents:
        if not isinstance(entry, dict) or entry.get("enabled") is False:
            continue

        agent_id = str(entry.get("agent_id") or "unknown")
        stream = _stream_from_agent_id(agent_id)
        labels = {"contour": contour, "stream": stream}
        latest = entry.get("latest_path")
        if not isinstance(latest, str) or not latest:
            yield _projection_error(contour, stream, 1)
            continue

        latest_path = Path(latest)
        if not latest_path.is_absolute():
            latest_path = base_dir / latest_path

        snapshot = _read_json(latest_path)
        if not isinstance(snapshot, dict):
            yield _projection_error(contour, stream, 1)
            continue

        yield from project_snapshot(snapshot, labels=labels, now=now)


def project_snapshot(snapshot: Mapping[str, Any], *, labels: Mapping[str, str], now: datetime) -> Iterable[ProjectedMetric]:
    metric_payload = snapshot.get("metrics") if isinstance(snapshot.get("metrics"), dict) else {}

    yield ProjectedMetric("agent_ro_state_code", dict(labels), _state_code(snapshot.get("state")))
    severity = _numeric_value(snapshot.get("severity"))
    yield ProjectedMetric("agent_ro_severity_code", dict(labels), severity if severity is not None else 5)

    freshness = _numeric_value(metric_payload.get("freshness_code"))
    yield ProjectedMetric("agent_ro_freshness_code", dict(labels), freshness if freshness is not None else FRESHNESS_UNKNOWN)

    operation = _numeric_value(metric_payload.get("operation_state_code"))
    yield ProjectedMetric("agent_ro_operation_state_code", dict(labels), operation if operation is not None else OPERATION_UNKNOWN)

    projection_error = 0
    collected = _parse_collected_at(snapshot.get("collected_at"))
    if collected is None:
        projection_error = 1
    else:
        collected_seconds = collected.timestamp()
        yield ProjectedMetric("agent_ro_collected_timestamp_seconds", dict(labels), collected_seconds)
        yield ProjectedMetric("agent_ro_age_seconds", dict(labels), max(0.0, now.timestamp() - collected_seconds))

    stream = labels.get("stream", "unknown")
    for key, value in sorted(metric_payload.items()):
        if key in RESERVED_METRIC_KEYS:
            continue
        numeric = _numeric_value(value)
        if numeric is None:
            continue
        yield ProjectedMetric(_metric_name(stream, key), dict(labels), numeric)

    yield ProjectedMetric("agent_ro_projection_error_value", dict(labels), projection_error)


def render_prometheus(metrics: Iterable[ProjectedMetric]) -> str:
    return "\n".join(
        f"{metric.name}{_labels(metric.labels)} {_format_value(metric.value)}"
        for metric in metrics
    ) + "\n"


def _metric_name(stream: str, key: str) -> str:
    if stream == "network.link" and key in NETWORK_METRIC_NAMES:
        return NETWORK_METRIC_NAMES[key]
    return f"agent_ro_{_safe_name(stream)}_{_safe_name(key)}"


def _projection_error(contour: str, stream: str, value: int) -> ProjectedMetric:
    return ProjectedMetric("agent_ro_projection_error_value", {"contour": contour, "stream": stream}, value)


def _stream_from_agent_id(agent_id: str) -> str:
    if agent_id.endswith(".ro"):
        return agent_id[:-3]
    return agent_id


def _state_code(value: Any) -> int:
    return STATE_CODES.get(str(value or "UNKNOWN").upper(), STATE_CODES["UNKNOWN"])


def _numeric_value(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    return None


def _parse_collected_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _labels(labels: Mapping[str, str]) -> str:
    if not labels:
        return ""
    rendered = ",".join(
        f'{_safe_label_name(key)}="{_escape_label_value(value)}"'
        for key, value in sorted(labels.items())
    )
    return "{" + rendered + "}"


def _safe_name(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_]", "_", value).strip("_").lower()
    if not name:
        return "unknown"
    if name[0].isdigit():
        return f"_{name}"
    return name


def _safe_label_name(value: str) -> str:
    return _safe_name(value)


def _escape_label_value(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_value(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    if value.is_integer():
        return str(int(value))
    return repr(value)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
