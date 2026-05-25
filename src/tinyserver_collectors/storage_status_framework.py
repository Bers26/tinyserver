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


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    collected_at = str(raw.get("collected_at") or "")
    checks: dict[str, Any] = {}
    for target in raw.get("targets", []):
        if not isinstance(target, dict):
            continue
        path = str(target.get("path") or "unknown")
        check_id = _metric_name(path, "health")
        checks[check_id] = _target_check(target, collected_at)
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
