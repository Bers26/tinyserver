"""Read-only service.health.ro collector helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import subprocess
from typing import Any, Iterable, Mapping

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}

EXPECTED_CORE_UNITS = (
    "agent-ro-registry.timer",
    "serverguard-agent-ro-prom.timer",
    "agent-ro-network-link-ro.timer",
    "agent-ro-storage-status-ro.timer",
)
DISCOVERY_PREFIXES = ("agent-ro-", "serverguard-agent-ro-")
DISCOVERY_SUFFIXES = (".service", ".timer")
IGNORED_DISCOVERY_UNITS = {
    # power.status.ro is refreshed by agent-ro-registry.timer in the current v0.1 runtime.
    # The old standalone timer may remain installed but disabled.
    "agent-ro-power-status-ro.timer",
}
UNIT_TYPE_CODES = {"service": 1, "timer": 2, "other": 0}


@dataclass(frozen=True)
class UnitFile:
    name: str
    state: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_metric_label(value: str) -> str:
    label = value.replace(".", "_").replace("-", "_").replace("@", "_")
    label = "_".join(part for part in label.split("_") if part)
    return label or "unknown"


def unit_type(unit: str) -> str:
    if unit.endswith(".service"):
        return "service"
    if unit.endswith(".timer"):
        return "timer"
    return "other"


def parse_unit_files(text: str) -> list[UnitFile]:
    rows: list[UnitFile] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("UNIT FILE"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        unit, state = parts[0], parts[1]
        rows.append(UnitFile(name=unit, state=state))
    return rows


def is_relevant_unit(unit: str) -> bool:
    return (
        unit not in IGNORED_DISCOVERY_UNITS
        and unit.endswith(DISCOVERY_SUFFIXES)
        and unit.startswith(DISCOVERY_PREFIXES)
    )


def discover_units(unit_files: Iterable[UnitFile]) -> list[str]:
    units = {item.name for item in unit_files if is_relevant_unit(item.name)}
    units.update(EXPECTED_CORE_UNITS)
    return sorted(units)


def parse_systemctl_show(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def run_command(args: list[str], timeout_sec: int = 5) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=timeout_sec, check=False)
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "timeout"
    except OSError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def classify_unit(unit: str, show: Mapping[str, str]) -> tuple[str, int, str, int, str]:
    load_state = show.get("LoadState", "unknown")
    active_state = show.get("ActiveState", "unknown")
    sub_state = show.get("SubState", "unknown")
    result = show.get("Result", "")
    kind = unit_type(unit)

    if load_state in {"not-found", "masked", "error"}:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"], f"{unit} load_state={load_state}."
    if active_state == "failed" or result not in {"", "success"}:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"], f"{unit} active_state={active_state}, sub_state={sub_state}, result={result}."
    if kind == "timer" and active_state != "active":
        return "WARN", STATE_CODES["WARN"], "degraded", SEVERITY_CODES["degraded"], f"{unit} timer is not active: active_state={active_state}, sub_state={sub_state}."
    if active_state == "unknown":
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"], f"{unit} active state unknown."
    return "OK", STATE_CODES["OK"], "normal", SEVERITY_CODES["normal"], f"{unit} load_state={load_state}, active_state={active_state}, sub_state={sub_state}."


def collect_unit(unit: str) -> dict[str, Any]:
    rc, stdout, stderr = run_command(
        [
            "systemctl",
            "show",
            unit,
            "--no-page",
            "--property=Id,LoadState,ActiveState,SubState,Result,UnitFileState",
        ]
    )
    show = parse_systemctl_show(stdout)
    state, state_code, severity, severity_code, summary = classify_unit(unit, show)
    active_state = show.get("ActiveState", "unknown")
    unit_file_state = show.get("UnitFileState", "unknown")
    return {
        "unit": unit,
        "unit_type": unit_type(unit),
        "unit_type_code": UNIT_TYPE_CODES.get(unit_type(unit), 0),
        "command_rc": rc,
        "load_state": show.get("LoadState", "unknown"),
        "active_state": active_state,
        "sub_state": show.get("SubState", "unknown"),
        "result": show.get("Result", ""),
        "unit_file_state": unit_file_state,
        "active_value": 1 if active_state == "active" else 0,
        "enabled_value": 1 if unit_file_state == "enabled" else 0,
        "state": state,
        "state_code": state_code,
        "severity": severity,
        "severity_code": severity_code,
        "summary": summary,
        "stderr": stderr.strip(),
    }


def classify_units(units: Iterable[Mapping[str, Any]]) -> tuple[str, int, str, int]:
    worst = "OK"
    worst_severity = "normal"
    seen = False
    for unit in units:
        seen = True
        state = str(unit.get("state") or "UNKNOWN").upper()
        if state == "BAD":
            return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
        if state == "WARN":
            worst = "WARN"
            worst_severity = "degraded"
        elif state == "UNKNOWN" and worst == "OK":
            worst = "UNKNOWN"
            worst_severity = "unknown_or_error"
    if not seen:
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]
    return worst, STATE_CODES[worst], worst_severity, SEVERITY_CODES[worst_severity]


def collect_service_health(units: Iterable[str] | None = None) -> dict[str, Any]:
    if units is None:
        _rc, stdout, _stderr = run_command(["systemctl", "list-unit-files", "--no-pager", "--plain"])
        selected = discover_units(parse_unit_files(stdout))
    else:
        selected = sorted(set(units))
    unit_rows = [collect_unit(unit) for unit in selected]
    state, state_code, severity, severity_code = classify_units(unit_rows)
    return {
        "agent_id": "service.health.ro",
        "collected_at": utc_now_iso(),
        "units": unit_rows,
        "unit_count": len(unit_rows),
        "state": state,
        "state_code": state_code,
        "severity": severity,
        "severity_code": severity_code,
        "freshness": "fresh",
        "freshness_code": FRESHNESS_CODES["fresh"],
        "operation_state": "completed",
        "operation_state_code": OPERATION_STATE_CODES["completed"],
    }