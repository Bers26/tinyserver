"""Read-only power.status.ro collector helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import re
import subprocess
from typing import Any, Mapping

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_apcupsd_text(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()
        if key:
            data[key] = value
    return data


def _first_number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _status(data: Mapping[str, str]) -> str:
    return str(data.get("STATUS") or "").strip().upper()


def classify_power(data: Mapping[str, str]) -> tuple[str, int, str, int]:
    status = _status(data)
    if not status:
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]
    if "ONLINE" in status:
        return "OK", STATE_CODES["OK"], "normal", SEVERITY_CODES["normal"]
    if "ONBATT" in status or "LOWBATT" in status:
        return "WARN", STATE_CODES["WARN"], "degraded", SEVERITY_CODES["degraded"]
    if "COMMLOST" in status or "SHUTTING" in status:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
    return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]


def metrics_from_apcupsd(data: Mapping[str, str], *, freshness_code: int = 0, operation_state_code: int = 6) -> dict[str, int | float]:
    metrics: dict[str, int | float] = {
        "freshness_code": freshness_code,
        "operation_state_code": operation_state_code,
    }
    mapping = {
        "battery_percent": "BCHARGE",
        "runtime_min": "TIMELEFT",
        "input_voltage": "LINEV",
        "output_voltage": "OUTPUTV",
        "temperature_c": "ITEMP",
        "load_percent": "LOADPCT",
    }
    for metric_key, source_key in mapping.items():
        value = _first_number(data.get(source_key))
        if value is not None:
            metrics[metric_key] = value
    return metrics


def run_apcaccess(timeout_sec: int = 5) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(["apcaccess", "status"], text=True, capture_output=True, timeout=timeout_sec, check=False)
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "timeout"
    except OSError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def collect_power_status(text: str | None = None) -> dict[str, Any]:
    collected_at = utc_now_iso()
    if text is None:
        rc, stdout, stderr = run_apcaccess()
        source = "apcaccess status"
        source_type = "command"
        command_rc = rc
        command_error = stderr.strip()
        data = parse_apcupsd_text(stdout) if rc == 0 else {}
    else:
        source = "apcupsd text"
        source_type = "provided_text"
        command_rc = 0
        command_error = ""
        data = parse_apcupsd_text(text)

    state, state_code, severity, severity_code = classify_power(data)
    freshness_code = FRESHNESS_CODES["fresh"] if data else FRESHNESS_CODES["unknown"]
    operation_state_code = OPERATION_STATE_CODES["completed"] if data else OPERATION_STATE_CODES["unknown"]
    status = _status(data) or "UNKNOWN"
    return {
        "agent_id": "power.status.ro",
        "collected_at": collected_at,
        "source": source,
        "source_type": source_type,
        "command_rc": command_rc,
        "command_error": command_error,
        "apcupsd": dict(data),
        "state": state,
        "state_code": state_code,
        "severity": severity,
        "severity_code": severity_code,
        "summary": f"Power source status: {status}",
        "freshness": "fresh" if data else "unknown",
        "freshness_code": freshness_code,
        "operation_state": "completed" if data else "unknown",
        "operation_state_code": operation_state_code,
        "metrics": metrics_from_apcupsd(
            data,
            freshness_code=freshness_code,
            operation_state_code=operation_state_code,
        ),
    }
