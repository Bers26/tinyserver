"""Framework-compatible snapshot wrapper for power.status.ro."""

from __future__ import annotations

import json
from typing import Any

from tinyserver_collectors.power_status import collect_power_status

TTL_SEC = 180
RULESET_VERSION = "1.0"

CHECK_SPECS = {
    "power.apcupsd.status": ("STATUS", "status"),
    "power.apcupsd.battery_charge": ("BCHARGE", "battery charge"),
    "power.apcupsd.runtime": ("TIMELEFT", "runtime"),
    "power.apcupsd.input_voltage": ("LINEV", "input voltage"),
    "power.apcupsd.output_voltage": ("OUTPUTV", "output voltage"),
    "power.apcupsd.temperature": ("ITEMP", "temperature"),
    "power.apcupsd.load": ("LOADPCT", "load"),
    "power.apcupsd.selftest": ("SELFTEST", "self-test"),
    "power.apcupsd.battery_date": ("BATTDATE", "battery date"),
}

REQUIRED_CHECK_IDS = (
    "power.apcupsd.status",
    "power.apcupsd.battery_charge",
    "power.apcupsd.runtime",
    "power.apcupsd.input_voltage",
    "power.apcupsd.output_voltage",
    "power.apcupsd.temperature",
    "power.apcupsd.load",
)


def _number(value: Any, default: int | float = 0) -> int | float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _metrics(raw: dict[str, Any]) -> dict[str, int | float]:
    payload = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    return {key: value for key, value in payload.items() if isinstance(value, (int, float)) and not isinstance(value, bool)}


def _check(raw: dict[str, Any], check_id: str) -> dict[str, Any]:
    data = raw.get("apcupsd") if isinstance(raw.get("apcupsd"), dict) else {}
    source_key, label = CHECK_SPECS[check_id]
    observed = data.get(source_key)
    if observed is None or observed == "":
        state = "UNKNOWN"
        severity = 5
        confidence = "medium"
        summary = f"APC UPS {label} unknown."
    else:
        state = str(raw.get("state") or "UNKNOWN").upper() if check_id == "power.apcupsd.status" else "OK"
        severity = int(_number(raw.get("severity_code"), 5)) if check_id == "power.apcupsd.status" else 0
        confidence = "high"
        summary = f"APC UPS {label}: {observed}."
    return {
        "state": state,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
        "rule_id": check_id,
        "ruleset_version": RULESET_VERSION,
        "evidence": {
            "source": str(raw.get("source") or "apcupsd"),
            "source_type": str(raw.get("source_type") or "unknown"),
            "command_class": "read_only",
            "observed_value": str(observed if observed is not None else raw.get("command_error") or "missing"),
            "collected_at": str(raw.get("collected_at") or ""),
        },
    }


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("apcupsd") if isinstance(raw.get("apcupsd"), dict) else {}
    check_ids = list(REQUIRED_CHECK_IDS)
    for optional_id in ("power.apcupsd.selftest", "power.apcupsd.battery_date"):
        source_key = CHECK_SPECS[optional_id][0]
        if data.get(source_key):
            check_ids.append(optional_id)
    return {check_id: _check(raw, check_id) for check_id in check_ids}


def to_framework_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN"}:
        state = "UNKNOWN"
    return {
        "schema_version": "1.0",
        "agent_id": "power.status.ro",
        "product": "Tiny Agent Framework",
        "domain": "power",
        "display_name": "Power Status RO",
        "version": "0.1",
        "collected_at": str(raw.get("collected_at") or ""),
        "ttl_sec": TTL_SEC,
        "state": state,
        "severity": int(_number(raw.get("severity_code"), 5)),
        "summary": str(raw.get("summary") or "Power source status: UNKNOWN"),
        "checks": _checks(raw),
        "metrics": _metrics(raw),
        "links": [],
        "capabilities": {"read_only": True, "actions": []},
    }


def collect(output_root: object | None = None) -> dict[str, Any]:
    return to_framework_snapshot(collect_power_status())


def main() -> int:
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
