"""Framework-compatible snapshot wrapper for storage.status.ro."""

from __future__ import annotations

import json
from typing import Any

from tinyserver_collectors.storage_status import collect_storage_status

TTL_SEC = 300
RULESET_VERSION = "1.0"


def _metric_name(path: str, suffix: str) -> str:
    if path == "/":
        label = "root"
    else:
        label = path.strip("/").replace("/", "_").replace("-", "_") or "unknown"
    return f"storage_{label}_{suffix}"


def _number(value: Any, default: int | float = 0) -> int | float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_value(value: Any) -> int:
    if value is True:
        return 1
    if value is False:
        return 0
    return -1


def _device_label(device: str) -> str:
    label = device.removeprefix("/dev/").strip("/").replace("/", "_").replace("-", "_")
    return label or "unknown"


def _smart_metric_name(device: str, suffix: str) -> str:
    return f"storage_disk_{_device_label(device)}_{suffix}"


def _smart_devices(raw: dict[str, Any]) -> list[dict[str, Any]]:
    smart = raw.get("smart_devices")
    if not isinstance(smart, dict):
        return []
    devices = smart.get("devices")
    if not isinstance(devices, list):
        return []
    return [device for device in devices if isinstance(device, dict)]


def _metrics(raw: dict[str, Any]) -> dict[str, int | float]:
    metrics: dict[str, int | float] = {
        "target_count": _number(raw.get("target_count"), 0),
        "freshness_code": _number(raw.get("freshness_code"), 4),
        "operation_state_code": _number(raw.get("operation_state_code"), 7),
    }
    for target in raw.get("targets", []):
        if not isinstance(target, dict):
            continue
        path = str(target.get("path") or "unknown")
        metrics[_metric_name(path, "exists_value")] = _bool_value(target.get("exists"))
        metrics[_metric_name(path, "mount_present_value")] = _bool_value(target.get("mount_present"))
        metrics[_metric_name(path, "readonly_value")] = _bool_value(target.get("readonly"))
        for key in ("size_bytes", "used_bytes", "free_bytes", "available_bytes", "used_percent"):
            value = target.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[_metric_name(path, key)] = value
    for device in _smart_devices(raw):
        device_name = str(device.get("device") or "unknown")
        metrics[_smart_metric_name(device_name, "smart_available_value")] = _bool_value(device.get("available"))
        health_code = device.get("health_code")
        if isinstance(health_code, (int, float)) and not isinstance(health_code, bool):
            metrics[_smart_metric_name(device_name, "smart_health_code")] = health_code
        attributes = device.get("attributes")
        if not isinstance(attributes, dict):
            attributes = {}
        for key in (
            "temperature_c",
            "power_on_hours",
            "power_cycle_count",
            "reallocated_sector_count",
            "current_pending_sector",
            "offline_uncorrectable",
            "udma_crc_error_count",
            "wear_leveling_count",
        ):
            value = attributes.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[_smart_metric_name(device_name, key)] = value
    return metrics


def _check(*, state: str, severity: int, confidence: str, summary: str, rule_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": state,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
        "rule_id": rule_id,
        "ruleset_version": RULESET_VERSION,
        "evidence": evidence,
    }


def _target_check(target: dict[str, Any], collected_at: str) -> dict[str, Any]:
    path = str(target.get("path") or "unknown")
    exists = target.get("exists") is True
    mounted = target.get("mount_present") is True
    readonly = target.get("readonly") is True
    used_percent = target.get("used_percent")
    if not exists:
        state, severity, summary = "BAD", 4, f"Storage target {path} does not exist."
    elif not mounted:
        state, severity, summary = "BAD", 4, f"Storage target {path} is not a mountpoint."
    elif readonly:
        state, severity, summary = "WARN", 3, f"Storage target {path} is mounted read-only."
    elif isinstance(used_percent, (int, float)) and used_percent >= 95:
        state, severity, summary = "BAD", 4, f"Storage target {path} is critically full: {used_percent}%."
    elif isinstance(used_percent, (int, float)) and used_percent >= 85:
        state, severity, summary = "WARN", 3, f"Storage target {path} is degraded: {used_percent}% used."
    elif isinstance(used_percent, (int, float)) and used_percent >= 75:
        state, severity, summary = "WARN", 2, f"Storage target {path} usage warning: {used_percent}% used."
    elif isinstance(used_percent, (int, float)):
        state, severity, summary = "OK", 0, f"Storage target {path} OK: {used_percent}% used."
    else:
        state, severity, summary = "UNKNOWN", 5, f"Storage target {path} usage unknown."
    return _check(
        state=state,
        severity=severity,
        confidence="high" if exists and mounted else "medium",
        summary=summary,
        rule_id=f"storage.target.{_metric_name(path, 'health')}",
        evidence={
            "source": "/proc/mounts + statvfs",
            "source_type": "derived",
            "command_class": "read_only",
            "observed_value": (
                f"path={path} exists={target.get('exists')} mount_present={target.get('mount_present')} "
                f"fstype={target.get('fstype')} source={target.get('source')} readonly={target.get('readonly')} "
                f"used_percent={target.get('used_percent')} available_bytes={target.get('available_bytes')}"
            ),
            "collected_at": collected_at,
        },
    )


def _smart_device_check(device: dict[str, Any], collected_at: str) -> dict[str, Any]:
    device_name = str(device.get("device") or "unknown")
    available = device.get("available") is True
    health = str(device.get("health") or "UNKNOWN").upper()
    attributes = device.get("attributes")
    if not isinstance(attributes, dict):
        attributes = {}
    counters = {
        key: _int_value(attributes.get(key), 0)
        for key in (
            "reallocated_sector_count",
            "current_pending_sector",
            "offline_uncorrectable",
            "udma_crc_error_count",
        )
    }

    if health == "FAILED":
        state, severity, summary = "BAD", 4, f"SMART health failed for {device_name}."
    elif not available:
        state, severity, summary = "UNKNOWN", 5, f"SMART unavailable for {device_name}."
    elif health == "PASSED" and any(value > 0 for value in counters.values()):
        state, severity, summary = "WARN", 3, f"SMART counters nonzero for {device_name}."
    elif health == "PASSED":
        state, severity, summary = "OK", 0, f"SMART health passed for {device_name}."
    else:
        state, severity, summary = "UNKNOWN", 5, f"SMART health unknown for {device_name}."

    return _check(
        state=state,
        severity=severity,
        confidence="high" if available else "medium",
        summary=summary,
        rule_id=f"storage.smart.{_smart_metric_name(device_name, 'health')}",
        evidence={
            "source": "smartctl",
            "source_type": "derived",
            "command_class": "read_only",
            "observed_value": (
                f"device={device_name} available={device.get('available')} status={device.get('status')} "
                f"health={device.get('health')} health_code={device.get('health_code')} counters={counters}"
            ),
            "collected_at": collected_at,
        },
    )


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    collected_at = str(raw.get("collected_at") or "")
    checks: dict[str, Any] = {}
    for target in raw.get("targets", []):
        if not isinstance(target, dict):
            continue
        path = str(target.get("path") or "unknown")
        check_id = _metric_name(path, "health")
        checks[check_id] = _target_check(target, collected_at)
    for device in _smart_devices(raw):
        device_name = str(device.get("device") or "unknown")
        checks[_smart_metric_name(device_name, "health")] = _smart_device_check(device, collected_at)
    return checks


def _summary(raw: dict[str, Any]) -> str:
    parts = []
    for target in raw.get("targets", []):
        if isinstance(target, dict):
            parts.append(f"{target.get('path')}={target.get('used_percent')}%")
    state = str(raw.get("state") or "UNKNOWN").upper()
    return f"Storage {state}: " + ", ".join(parts)


def to_framework_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN"}:
        state = "UNKNOWN"
    return {
        "schema_version": "1.0",
        "agent_id": "storage.status.ro",
        "product": "Tiny Agent Framework",
        "domain": "storage",
        "display_name": "Storage Status RO",
        "version": "0.1",
        "collected_at": str(raw.get("collected_at") or ""),
        "ttl_sec": TTL_SEC,
        "state": state,
        "severity": _int_value(raw.get("severity_code"), 5),
        "summary": _summary(raw),
        "checks": _checks(raw),
        "metrics": _metrics(raw),
        "links": [],
        "capabilities": {"read_only": True, "actions": []},
    }


def collect(output_root: object | None = None) -> dict[str, Any]:
    return to_framework_snapshot(collect_storage_status())


def main() -> int:
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
