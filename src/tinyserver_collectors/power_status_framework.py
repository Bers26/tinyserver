"""Framework-compatible read-only NUT UPS snapshot for power.status.ro."""

from __future__ import annotations

import json
from typing import Any

from tinyserver_collectors.power_status import collect_power_status

TTL_SEC = 180
RULESET_VERSION = "1.0"

CHECK_SPECS = {
    "power.nut.status": ("ups.status", "status"),
    "power.nut.battery_charge": ("battery.charge", "battery charge"),
    "power.nut.runtime": ("battery.runtime", "runtime seconds"),
    "power.nut.input_voltage": ("input.voltage", "input voltage"),
    "power.nut.output_voltage": ("output.voltage", "output voltage"),
    "power.nut.temperature": ("ups.temperature", "temperature"),
    "power.nut.load": ("ups.load", "load percent"),
    "power.nut.model": ("device.model", "model"),
}
REQUIRED_CHECK_IDS = (
    "power.nut.status", "power.nut.battery_charge", "power.nut.runtime",
)


def _number(value: Any, default: int | float = 0) -> int | float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _metrics(raw: dict[str, Any]) -> dict[str, int | float]:
    payload = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    return {k: v for k, v in payload.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def _evidence(raw: dict[str, Any], observed: object, source_type: str = "derived") -> dict[str, str]:
    return {
        "source": str(raw.get("source") or "NUT/upsc"),
        "source_type": source_type,
        "command_class": "read_only",
        "observed_value": str(observed),
        "collected_at": str(raw.get("collected_at") or ""),
    }


def _result(raw: dict[str, Any], check_id: str, state: str, severity: int, summary: str,
            observed: object, confidence: str = "high") -> dict[str, Any]:
    return {
        "state": state, "severity": severity, "confidence": confidence,
        "summary": summary, "rule_id": check_id,
        "ruleset_version": RULESET_VERSION,
        "evidence": _evidence(raw, observed),
    }


def _sensor_check(raw: dict[str, Any], check_id: str) -> dict[str, Any]:
    data = raw.get("nut") if isinstance(raw.get("nut"), dict) else {}
    key, label = CHECK_SPECS[check_id]
    observed = data.get(key)
    if observed is None or observed == "":
        return _result(raw, check_id, "UNKNOWN", 5, f"UPS {label} unavailable from NUT.", "missing", "medium")
    if check_id == "power.nut.status":
        state = str(raw.get("state") or "UNKNOWN").upper()
        severity = int(_number(raw.get("severity_code"), 5))
    else:
        state, severity = "OK", 0
    return _result(raw, check_id, state, severity, f"NUT UPS {label}: {observed}.", observed)


def _command_check(raw: dict[str, Any]) -> dict[str, Any]:
    command = raw.get("command") if isinstance(raw.get("command"), dict) else {}
    ok = command.get("upsc_ok") is True
    err = command.get("command_error_class", "unknown")
    rc = command.get("command_rc")
    if ok:
        state, severity, summary = "OK", 0, "upsc returned fresh NUT UPS status."
    elif err == "data_stale":
        state, severity, summary = "STALE", 5, "NUT driver telemetry is stale (DATA-STALE)."
    else:
        state, severity, summary = "BAD", 4, f"upsc telemetry unavailable: {err}."
    return _result(raw, "power.nut.command", state, severity, summary, f"ok={ok} rc={rc} class={err}")


def _service_check(raw: dict[str, Any]) -> dict[str, Any]:
    service = raw.get("service") if isinstance(raw.get("service"), dict) else {}
    active = str(service.get("active_state") or "unknown")
    sub = str(service.get("sub_state") or "unknown")
    if active == "active" and sub == "running":
        state, severity, summary = "OK", 0, "nut-server.service active/running."
    elif active in {"inactive", "failed"}:
        state, severity, summary = "BAD", 4, f"nut-server.service inactive: {active}/{sub}."
    else:
        state, severity, summary = "UNKNOWN", 5, f"nut-server.service state unknown: {active}/{sub}."
    return _result(raw, "power.nut.service", state, severity, summary, f"{active}/{sub}")


def _tasks_check(raw: dict[str, Any]) -> dict[str, Any]:
    service = raw.get("service") if isinstance(raw.get("service"), dict) else {}
    value = service.get("tasks_current")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        state, severity = ("WARN", 3) if value >= 900 else ("OK", 0)
        summary = f"nut-server tasks_current={value}."
    else:
        state, severity, summary = "UNKNOWN", 5, "nut-server tasks_current unknown."
    return _result(raw, "power.nut.tasks", state, severity, summary, value)


def _fd_check(raw: dict[str, Any]) -> dict[str, Any]:
    service = raw.get("service") if isinstance(raw.get("service"), dict) else {}
    count = service.get("fd_count")
    soft = service.get("limit_nofile_soft")
    ratio = service.get("fd_usage_ratio")
    if service.get("fd_count_available") is not True or not isinstance(ratio, (int, float)):
        state, severity, summary = "UNKNOWN", 5, "nut-server FD usage unavailable."
    elif ratio >= 0.95:
        state, severity, summary = "WARN", 3, f"nut-server near FD limit ({count}/{soft})."
    else:
        state, severity, summary = "OK", 0, f"nut-server FD usage normal ({count}/{soft})."
    return _result(raw, "power.nut.fd_usage", state, severity, summary, f"fd={count} soft={soft} ratio={ratio}")


def _diagnosis_check(raw: dict[str, Any]) -> dict[str, Any]:
    layer = raw.get("diagnosis_layer") if isinstance(raw.get("diagnosis_layer"), dict) else {}
    kind = str(layer.get("likely_layer") or "unknown")
    reason = str(layer.get("reason") or "diagnosis unavailable")
    state = str(raw.get("state") or "UNKNOWN").upper()
    if kind == "ups_hardware":
        check_state, severity = state, int(_number(raw.get("severity_code"), 5))
    elif kind == "driver" and raw.get("command_error_class") == "data_stale":
        check_state, severity = "STALE", 5
    elif kind in {"driver", "service", "transport", "command"}:
        check_state, severity = "WARN", 3
    else:
        check_state, severity = "UNKNOWN", 5
    return _result(raw, "power.nut.diagnosis_layer", check_state, severity, reason, kind,
                   str(layer.get("confidence") or "medium"))


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("nut") if isinstance(raw.get("nut"), dict) else {}
    ids = list(REQUIRED_CHECK_IDS)
    for optional_id in CHECK_SPECS:
        if optional_id in REQUIRED_CHECK_IDS:
            continue
        if data.get(CHECK_SPECS[optional_id][0]):
            ids.append(optional_id)
    checks = {key: _sensor_check(raw, key) for key in ids}
    checks.update({
        "power.nut.command": _command_check(raw),
        "power.nut.service": _service_check(raw),
        "power.nut.tasks": _tasks_check(raw),
        "power.nut.fd_usage": _fd_check(raw),
        "power.nut.diagnosis_layer": _diagnosis_check(raw),
    })
    return checks


def to_framework_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN", "STALE"}:
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
        "summary": str(raw.get("summary") or "UPS status unknown"),
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
