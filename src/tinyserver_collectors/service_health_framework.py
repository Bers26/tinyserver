"""Framework-compatible snapshot wrapper for service.health.ro."""

from __future__ import annotations

import json
from typing import Any

from tinyserver_collectors.service_health import collect_service_health, safe_metric_label

TTL_SEC = 180
RULESET_VERSION = "1.0"


def _number(value: Any, default: int | float = 0) -> int | float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _metrics(raw: dict[str, Any]) -> dict[str, int | float]:
    metrics: dict[str, int | float] = {
        "unit_count": _number(raw.get("unit_count"), 0),
        "freshness_code": _number(raw.get("freshness_code"), 4),
        "operation_state_code": _number(raw.get("operation_state_code"), 7),
    }
    for unit in raw.get("units", []):
        if not isinstance(unit, dict):
            continue
        label = safe_metric_label(str(unit.get("unit") or "unknown"))
        metrics[f"unit_{label}_active_value"] = _number(unit.get("active_value"), 0)
        metrics[f"unit_{label}_enabled_value"] = _number(unit.get("enabled_value"), 0)
        metrics[f"unit_{label}_state_code"] = _number(unit.get("state_code"), 3)
        metrics[f"unit_{label}_severity_code"] = _number(unit.get("severity_code"), 5)
        metrics[f"unit_{label}_type_code"] = _number(unit.get("unit_type_code"), 0)
    return metrics


def _check(unit: dict[str, Any], collected_at: str) -> dict[str, Any]:
    name = str(unit.get("unit") or "unknown")
    label = safe_metric_label(name)
    return {
        "state": str(unit.get("state") or "UNKNOWN").upper(),
        "severity": int(_number(unit.get("severity_code"), 5)),
        "confidence": "high" if unit.get("command_rc") == 0 else "medium",
        "summary": str(unit.get("summary") or ""),
        "rule_id": f"service.unit.{label}",
        "ruleset_version": RULESET_VERSION,
        "evidence": {
            "source": "systemctl show",
            "source_type": "command",
            "command_class": "read_only",
            "observed_value": (
                f"unit={name} load_state={unit.get('load_state')} active_state={unit.get('active_state')} "
                f"sub_state={unit.get('sub_state')} result={unit.get('result')} unit_file_state={unit.get('unit_file_state')}"
            ),
            "collected_at": collected_at,
        },
    }


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    collected_at = str(raw.get("collected_at") or "")
    checks: dict[str, Any] = {}
    for unit in raw.get("units", []):
        if not isinstance(unit, dict):
            continue
        label = safe_metric_label(str(unit.get("unit") or "unknown"))
        checks[f"service_{label}_health"] = _check(unit, collected_at)
    return checks


def _summary(raw: dict[str, Any]) -> str:
    state = str(raw.get("state") or "UNKNOWN").upper()
    counts: dict[str, int] = {}
    for unit in raw.get("units", []):
        if isinstance(unit, dict):
            key = str(unit.get("state") or "UNKNOWN").upper()
            counts[key] = counts.get(key, 0) + 1
    parts = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    return f"Service health {state}: {parts}"


def to_framework_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN"}:
        state = "UNKNOWN"
    return {
        "schema_version": "1.0",
        "agent_id": "service.health.ro",
        "product": "Tiny Agent Framework",
        "domain": "service",
        "display_name": "Service Health RO",
        "version": "0.1",
        "collected_at": str(raw.get("collected_at") or ""),
        "ttl_sec": TTL_SEC,
        "state": state,
        "severity": int(_number(raw.get("severity_code"), 5)),
        "summary": _summary(raw),
        "checks": _checks(raw),
        "metrics": _metrics(raw),
        "links": [],
        "capabilities": {"read_only": True, "actions": []},
    }


def collect(output_root: object | None = None) -> dict[str, Any]:
    return to_framework_snapshot(collect_service_health())


def main() -> int:
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
