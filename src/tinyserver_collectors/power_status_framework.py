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




def _diag_evidence(raw: dict[str, Any], observed_value: str) -> dict[str, Any]:
    return {
        "source": "apcupsd/apcaccess + systemctl show + /proc",
        "source_type": "derived",
        "command_class": "read_only",
        "observed_value": observed_value,
        "collected_at": str(raw.get("collected_at") or ""),
    }


def _diagnostic_check(state: str, severity: int, confidence: str, summary: str, rule_id: str, raw: dict[str, Any], observed: str) -> dict[str, Any]:
    return {
        "state": state,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
        "rule_id": rule_id,
        "ruleset_version": RULESET_VERSION,
        "evidence": _diag_evidence(raw, observed),
    }


def _command_check(raw: dict[str, Any]) -> dict[str, Any]:
    command = raw.get("command") if isinstance(raw.get("command"), dict) else {}
    ok = command.get("apcaccess_ok") is True
    rc = command.get("command_rc", raw.get("command_rc"))
    error_class = command.get("command_error_class", raw.get("command_error_class") or "unknown")
    error = command.get("command_error", raw.get("command_error") or "")
    if ok:
        state, severity, confidence = "OK", 0, "high"
        summary = "apcaccess command returned valid apcupsd telemetry."
    else:
        state, severity, confidence = "BAD", 4, "high" if rc not in (None, "") else "medium"
        summary = f"apcaccess command failed or returned invalid telemetry: class={error_class}."
    return _diagnostic_check(state, severity, confidence, summary, "power.apcupsd.command", raw, f"ok={ok} rc={rc} class={error_class} error={error}")


def _service_check(raw: dict[str, Any]) -> dict[str, Any]:
    service = raw.get("service") if isinstance(raw.get("service"), dict) else {}
    active = str(service.get("active_state") or "unknown")
    sub = str(service.get("sub_state") or "unknown")
    pid = service.get("main_pid")
    if active == "active" and sub == "running":
        state, severity, confidence = "OK", 0, "high"
        summary = "apcupsd service is active/running."
    elif active in {"failed", "inactive"}:
        state, severity, confidence = "BAD", 4, "high"
        summary = f"apcupsd service is not running: active_state={active}, sub_state={sub}."
    else:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = f"apcupsd service state unknown: active_state={active}, sub_state={sub}."
    return _diagnostic_check(state, severity, confidence, summary, "power.apcupsd.service", raw, f"active_state={active} sub_state={sub} main_pid={pid}")


def _tasks_check(raw: dict[str, Any]) -> dict[str, Any]:
    service = raw.get("service") if isinstance(raw.get("service"), dict) else {}
    tasks = service.get("tasks_current")
    if isinstance(tasks, (int, float)) and not isinstance(tasks, bool):
        if tasks >= 900:
            state, severity, summary = "WARN", 3, f"apcupsd tasks are high: tasks_current={tasks}."
        else:
            state, severity, summary = "OK", 0, f"apcupsd tasks are normal: tasks_current={tasks}."
        confidence = "high"
    else:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = "apcupsd tasks_current unavailable."
    return _diagnostic_check(state, severity, confidence, summary, "power.apcupsd.tasks", raw, f"tasks_current={tasks}")


def _fd_usage_check(raw: dict[str, Any]) -> dict[str, Any]:
    service = raw.get("service") if isinstance(raw.get("service"), dict) else {}
    available = service.get("fd_count_available") is True
    fd_count = service.get("fd_count")
    soft = service.get("limit_nofile_soft")
    ratio = service.get("fd_usage_ratio")
    error = service.get("fd_count_error") or ""
    if not available:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = f"apcupsd fd count unavailable: {error or "unknown error"}."
    elif isinstance(ratio, (int, float)) and ratio >= 0.95:
        state, severity, confidence = "WARN", 3, "high"
        summary = f"apcupsd fd usage near process soft limit: fd_count={fd_count}, soft_limit={soft}, ratio={ratio:.3f}."
    elif isinstance(ratio, (int, float)):
        state, severity, confidence = "OK", 0, "high"
        summary = f"apcupsd fd usage normal: fd_count={fd_count}, soft_limit={soft}, ratio={ratio:.3f}."
    else:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = f"apcupsd fd usage unknown: fd_count={fd_count}, soft_limit={soft}."
    return _diagnostic_check(state, severity, confidence, summary, "power.apcupsd.fd_usage", raw, f"available={available} fd_count={fd_count} soft_limit={soft} ratio={ratio} error={error}")


def _diagnosis_layer_check(raw: dict[str, Any]) -> dict[str, Any]:
    layer = raw.get("diagnosis_layer") if isinstance(raw.get("diagnosis_layer"), dict) else {}
    likely = str(layer.get("likely_layer") or "unknown")
    reason = str(layer.get("reason") or "diagnosis unavailable")
    confidence = str(layer.get("confidence") or "low")
    if likely == "ups_hardware" and str(raw.get("state") or "UNKNOWN").upper() == "OK":
        state, severity = "OK", 0
    elif likely in {"service", "command"}:
        state, severity = "WARN", 3
    elif likely == "ups_hardware":
        state, severity = str(raw.get("state") or "UNKNOWN").upper(), int(_number(raw.get("severity_code"), 5))
    else:
        state, severity = "UNKNOWN", 5
    return _diagnostic_check(state, severity, confidence, reason, "power.apcupsd.diagnosis_layer", raw, f"likely_layer={likely} reason={reason}")

def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("apcupsd") if isinstance(raw.get("apcupsd"), dict) else {}
    check_ids = list(REQUIRED_CHECK_IDS)
    for optional_id in ("power.apcupsd.selftest", "power.apcupsd.battery_date"):
        source_key = CHECK_SPECS[optional_id][0]
        if data.get(source_key):
            check_ids.append(optional_id)
    checks = {check_id: _check(raw, check_id) for check_id in check_ids}
    checks.update(
        {
            "power.apcupsd.command": _command_check(raw),
            "power.apcupsd.service": _service_check(raw),
            "power.apcupsd.tasks": _tasks_check(raw),
            "power.apcupsd.fd_usage": _fd_usage_check(raw),
            "power.apcupsd.diagnosis_layer": _diagnosis_layer_check(raw),
        }
    )
    return checks


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
