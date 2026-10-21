"""Read-only power.status.ro collector helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import os
import re
import subprocess
from typing import Any, Mapping

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_nut_text(text: str) -> dict[str, str]:
    """Parse key: value lines from upsc; ignore malformed/unrecognised lines."""
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        if re.fullmatch(r"[a-z][a-z0-9_.-]{1,100}", key):
            data[key] = value.strip()
    return data


def parse_systemctl_show(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def _int_or_none(value: object) -> int | None:
    if value in (None, "", "infinity", "unlimited"):
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def parse_proc_limits(text: str) -> dict[str, int | None]:
    soft: int | None = None
    hard: int | None = None
    for line in text.splitlines():
        if not line.startswith("Max open files"):
            continue
        parts = line.split()
        if len(parts) >= 5:
            soft = _int_or_none(parts[3])
            hard = _int_or_none(parts[4])
        break
    return {"limit_nofile_soft": soft, "limit_nofile_hard": hard}


def safe_fd_count(pid: int | str | None) -> dict[str, Any]:
    pid_int = _int_or_none(pid)
    if pid_int is None or pid_int <= 0:
        return {"fd_count_available": False, "fd_count": None, "fd_count_error": "main_pid unavailable"}
    try:
        return {"fd_count_available": True, "fd_count": len(os.listdir(f"/proc/{pid_int}/fd")), "fd_count_error": ""}
    except OSError as exc:
        return {"fd_count_available": False, "fd_count": None, "fd_count_error": str(exc)}


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
    return str(data.get("ups.status") or "").strip().upper()


def classify_power(data: Mapping[str, str], error_class: str = "ok") -> tuple[str, int, str, int]:
    if error_class == "data_stale":
        return "STALE", STATE_CODES["STALE"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]
    flags = set(_status(data).split())
    if flags & {"LB", "FSD", "OFF", "ALARM"}:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
    if flags & {"OB", "RB"}:
        return "WARN", STATE_CODES["WARN"], "degraded", SEVERITY_CODES["degraded"]
    if "OL" in flags:
        return "OK", STATE_CODES["OK"], "normal", SEVERITY_CODES["normal"]
    return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]


def metrics_from_nut(data: Mapping[str, str], *, freshness_code: int = 0, operation_state_code: int = 6) -> dict[str, int | float]:
    import math

    metrics: dict[str, int | float] = {
        "freshness_code": freshness_code,
        "operation_state_code": operation_state_code,
    }
    mapping = {
        "battery_percent": "battery.charge",
        "runtime_min": "battery.runtime",
        "input_voltage": "input.voltage",
        "output_voltage": "output.voltage",
        "temperature_c": "ups.temperature",
        "load_percent": "ups.load",
    }
    for key, nut_key in mapping.items():
        value = data.get(nut_key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(number) or number < 0:
            continue
        metrics[key] = number / 60 if key == "runtime_min" else number
    return metrics


def run_command(args: list[str], timeout_sec: int = 5) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=timeout_sec, check=False)
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "timeout"
    except OSError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def run_upsc(timeout_sec: int = 5) -> tuple[int, str, str]:
    """Discover the UPS and perform only NUT read operations."""
    rc, out, err = run_command(["upsc", "-l", "localhost"], timeout_sec=timeout_sec)
    if rc != 0:
        return rc, out, err
    devices = [line.strip() for line in out.splitlines()
               if re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", line.strip())]
    if not devices:
        return 1, "", "no NUT UPS discovered"
    if "apc" in devices:
        name = "apc"
    elif len(devices) == 1:
        name = devices[0]
    else:
        return 1, "", "multiple NUT UPS: selection ambiguous"
    return run_command(["upsc", f"{name}@localhost"], timeout_sec=timeout_sec)


def run_systemctl_show_nut(timeout_sec: int = 5) -> tuple[int, str, str]:
    return run_command(
        ["systemctl", "show", "nut-server.service", "--no-pager",
         "--property=ActiveState,SubState,MainPID,TasksCurrent,LimitNOFILE"],
        timeout_sec=timeout_sec,
    )


def _empty_service_status() -> dict[str, Any]:
    return {
        "active_state": "unknown",
        "sub_state": "unknown",
        "main_pid": None,
        "tasks_current": None,
        "limit_nofile_systemd": None,
        "limit_nofile_soft": None,
        "limit_nofile_hard": None,
        "fd_count_available": False,
        "fd_count": None,
        "fd_count_error": "service status not collected",
        "fd_usage_ratio": None,
    }


def _read_proc_limits(pid: int | None) -> dict[str, int | None]:
    if pid is None or pid <= 0:
        return {"limit_nofile_soft": None, "limit_nofile_hard": None}
    try:
        with open(f"/proc/{pid}/limits", encoding="utf-8") as handle:
            return parse_proc_limits(handle.read())
    except OSError:
        return {"limit_nofile_soft": None, "limit_nofile_hard": None}


def collect_nut_service_status() -> dict[str, Any]:
    rc, stdout, stderr = run_systemctl_show_nut()
    show = parse_systemctl_show(stdout)
    pid = _int_or_none(show.get("MainPID"))
    limits = _read_proc_limits(pid)
    fd_info = safe_fd_count(pid)
    soft = limits["limit_nofile_soft"]
    ratio = fd_info["fd_count"] / soft if fd_info["fd_count"] is not None and soft and soft > 0 else None
    return {
        "active_state": show.get("ActiveState") or "unknown",
        "sub_state": show.get("SubState") or "unknown",
        "main_pid": pid,
        "tasks_current": _int_or_none(show.get("TasksCurrent")),
        "limit_nofile_systemd": _int_or_none(show.get("LimitNOFILE")),
        "limit_nofile_soft": soft,
        "limit_nofile_hard": limits["limit_nofile_hard"],
        "fd_count_available": fd_info["fd_count_available"],
        "fd_count": fd_info["fd_count"],
        "fd_count_error": fd_info["fd_count_error"],
        "fd_usage_ratio": ratio,
        "command_rc": rc,
        "command_error": stderr.strip(),
    }


def classify_upsc_error(rc: int, stdout: str = "", stderr: str = "") -> str:
    message = (str(stdout) + "\n" + str(stderr)).lower()
    if "data-stale" in message or "data stale" in message:
        return "data_stale"
    if "driver-not-connected" in message or "driver not connected" in message:
        return "driver_disconnected"
    if rc == 0:
        return "ok" if stdout.strip() else "empty_output"
    if rc == 124 or "timeout" in message or "timed out" in message:
        return "timeout"
    if rc == 127 or "not found" in message or "no such file" in message:
        return "command_not_found"
    if "connection reset" in message:
        return "connection_reset"
    if "permission denied" in message:
        return "permission_denied"
    if "connection refused" in message or "unavailable" in message:
        return "unavailable"
    return "command_failed"


def build_diagnosis_layer(command: Mapping[str, Any], service: Mapping[str, Any], nut: Mapping[str, str]) -> dict[str, Any]:
    status = _status(nut)
    error_class = str(command.get("command_error_class") or "unknown")
    active = str(service.get("active_state") or "unknown")
    ratio = service.get("fd_usage_ratio")
    tasks = _int_or_none(service.get("tasks_current"))
    if error_class == "data_stale":
        return {
            "likely_layer": "driver", "confidence": "high",
            "reason": "NUT reports DATA-STALE; driver telemetry is not fresh, not evidence of UPS hardware failure.",
            "next_read_only_check": "Inspect upsc status and NUT driver/unit logs without restarting anything.",
        }
    if error_class == "driver_disconnected":
        return {
            "likely_layer": "driver", "confidence": "high",
            "reason": "NUT reports DRIVER-NOT-CONNECTED.",
            "next_read_only_check": "Inspect USB connection and NUT driver service state read-only.",
        }
    if active in {"failed", "inactive"}:
        return {
            "likely_layer": "service", "confidence": "high",
            "reason": f"nut-server.service is not running: active_state={active}.",
            "next_read_only_check": "Inspect nut-server.service and its recent journal.",
        }
    if (isinstance(ratio, (int, float)) and ratio >= 0.95) or (tasks is not None and tasks >= 900):
        return {
            "likely_layer": "service", "confidence": "high",
            "reason": f"NUT service resource pressure: fd_ratio={ratio}, tasks_current={tasks}.",
            "next_read_only_check": "Inspect nut-server process fd count, limits and tasks.",
        }
    if command.get("upsc_ok") is True and status:
        return {
            "likely_layer": "ups_hardware", "confidence": "high",
            "reason": f"NUT fresh telemetry reports UPS status {status}.",
            "next_read_only_check": "Compare ups.status, battery.charge and battery.runtime from upsc.",
        }
    if error_class in {"timeout", "connection_reset", "unavailable"}:
        return {
            "likely_layer": "transport", "confidence": "medium",
            "reason": f"NUT read failed: {error_class}; UPS hardware state unknown.",
            "next_read_only_check": "Inspect NUT socket and driver status read-only.",
        }
    return {
        "likely_layer": "command", "confidence": "medium",
        "reason": f"Unable to obtain valid NUT telemetry: {error_class}.",
        "next_read_only_check": "Run upsc -l localhost and upsc apc@localhost read-only.",
    }



def collect_power_status(text: str | None = None, service_status: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Read-only NUT collector. Text injection is for deterministic offline tests."""
    collected_at = utc_now_iso()
    if text is None:
        command_rc, stdout, stderr = run_upsc()
        source = "upsc NUT localhost"
        source_type = "command"
        data = parse_nut_text(stdout) if command_rc == 0 else {}
        command_error = stderr.strip()
    else:
        source = "NUT provided text"
        source_type = "provided_text"
        command_rc, stdout, command_error = 0, text, ""
        data = parse_nut_text(text)

    error_class = classify_upsc_error(command_rc, stdout, command_error)
    status = _status(data)
    if error_class == "ok" and not status:
        error_class = "invalid_status"
    command = {
        "upsc_ok": error_class == "ok" and bool(status),
        "command_rc": command_rc,
        "command_error": command_error,
        "command_error_class": error_class,
    }
    if service_status is not None:
        service = dict(service_status)
    elif text is None:
        service = collect_nut_service_status()
    else:
        service = _empty_service_status()
    state, state_code, severity, severity_code = classify_power(data, error_class)
    freshness = "stale" if error_class == "data_stale" else "fresh" if command["upsc_ok"] else "unknown"
    freshness_code = FRESHNESS_CODES[freshness]
    operation = "completed" if command["upsc_ok"] else "unknown"
    operation_code = OPERATION_STATE_CODES[operation]
    diagnosis = build_diagnosis_layer(command, service, data)
    return {
        "agent_id": "power.status.ro",
        "collected_at": collected_at,
        "provider": "nut/upsc",
        "source": source, "source_type": source_type,
        "command": command, "command_rc": command_rc,
        "command_error": command_error, "command_error_class": error_class,
        "service": service, "diagnosis_layer": diagnosis,
        "nut": dict(data),
        "state": state, "state_code": state_code,
        "severity": severity, "severity_code": severity_code,
        "summary": f"UPS status via NUT: {status or error_class.upper()}",
        "freshness": freshness, "freshness_code": freshness_code,
        "source_freshness": "nut_driver_live" if freshness == "fresh" else freshness,
        "operation_state": operation, "operation_state_code": operation_code,
        "metrics": metrics_from_nut(
            data, freshness_code=freshness_code, operation_state_code=operation_code
        ),
    }
