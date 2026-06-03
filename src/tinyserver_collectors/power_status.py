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


def run_command(args: list[str], timeout_sec: int = 5) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=timeout_sec, check=False)
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "timeout"
    except OSError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def run_apcaccess(timeout_sec: int = 5) -> tuple[int, str, str]:
    return run_command(["apcaccess", "status"], timeout_sec=timeout_sec)


def run_systemctl_show_apcupsd(timeout_sec: int = 5) -> tuple[int, str, str]:
    return run_command(
        [
            "systemctl",
            "show",
            "apcupsd.service",
            "--no-page",
            "--property=ActiveState,SubState,MainPID,TasksCurrent,LimitNOFILE",
        ],
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


def collect_apcupsd_service_status() -> dict[str, Any]:
    rc, stdout, stderr = run_systemctl_show_apcupsd()
    show = parse_systemctl_show(stdout)
    main_pid = _int_or_none(show.get("MainPID"))
    limits = _read_proc_limits(main_pid)
    fd_info = safe_fd_count(main_pid)
    soft_limit = limits["limit_nofile_soft"]
    fd_usage_ratio = None
    if fd_info["fd_count"] is not None and soft_limit and soft_limit > 0:
        fd_usage_ratio = fd_info["fd_count"] / soft_limit
    return {
        "active_state": show.get("ActiveState") or "unknown",
        "sub_state": show.get("SubState") or "unknown",
        "main_pid": main_pid,
        "tasks_current": _int_or_none(show.get("TasksCurrent")),
        "limit_nofile_systemd": _int_or_none(show.get("LimitNOFILE")),
        "limit_nofile_soft": soft_limit,
        "limit_nofile_hard": limits["limit_nofile_hard"],
        "fd_count_available": fd_info["fd_count_available"],
        "fd_count": fd_info["fd_count"],
        "fd_count_error": fd_info["fd_count_error"],
        "fd_usage_ratio": fd_usage_ratio,
        "command_rc": rc,
        "command_error": stderr.strip(),
    }


def classify_apcaccess_error(rc: int, stdout: str = "", stderr: str = "") -> str:
    if rc == 0:
        return "ok"
    text = (stdout + "\n" + stderr).lower()
    if rc == 124 or "timeout" in text or "timed out" in text:
        return "timeout"
    if rc == 127 or "not found" in text or "no such file" in text:
        return "command_not_found"
    if "connection reset by peer" in text:
        return "connection_reset"
    if "permission denied" in text or "operation not permitted" in text:
        return "permission_denied"
    if "connection refused" in text or "unavailable" in text:
        return "unavailable"
    return "command_failed"


def build_diagnosis_layer(command: Mapping[str, Any], service: Mapping[str, Any], apcupsd: Mapping[str, str]) -> dict[str, Any]:
    apcaccess_ok = command.get("apcaccess_ok") is True
    error_class = str(command.get("command_error_class") or "unknown")
    active_state = str(service.get("active_state") or "unknown")
    sub_state = str(service.get("sub_state") or "unknown")
    tasks_current = _int_or_none(service.get("tasks_current"))
    fd_count = _int_or_none(service.get("fd_count"))
    soft_limit = _int_or_none(service.get("limit_nofile_soft"))
    fd_ratio = service.get("fd_usage_ratio")
    status = _status(apcupsd)

    if apcaccess_ok and apcupsd:
        return {
            "likely_layer": "ups_hardware",
            "reason": f"apcupsd/apcaccess telemetry is valid and UPS reports {status or 'UNKNOWN'}.",
            "confidence": "high" if status else "medium",
            "next_read_only_check": "Compare STATUS, BCHARGE, TIMELEFT, LINEV and LOADPCT from apcaccess.",
        }

    service_running = active_state == "active" and sub_state == "running"
    fd_near_limit = isinstance(fd_ratio, (int, float)) and fd_ratio >= 0.95
    tasks_near_limit = tasks_current is not None and tasks_current >= 900
    if service_running and (error_class == "connection_reset" or fd_near_limit or tasks_near_limit):
        evidence = []
        if error_class == "connection_reset":
            evidence.append("apcaccess connection reset by peer")
        if fd_near_limit:
            evidence.append(f"apcupsd fd usage {fd_count}/{soft_limit}")
        if tasks_near_limit:
            evidence.append(f"apcupsd tasks_current={tasks_current}")
        return {
            "likely_layer": "service",
            "reason": "apcupsd service-layer failure: " + ", ".join(evidence) + ".",
            "confidence": "high",
            "next_read_only_check": "Read systemctl show apcupsd.service plus /proc/<MainPID>/limits and /proc/<MainPID>/fd.",
        }

    if active_state in {"failed", "inactive"}:
        return {
            "likely_layer": "service",
            "reason": f"apcupsd service is not running: active_state={active_state}, sub_state={sub_state}.",
            "confidence": "high",
            "next_read_only_check": "Read systemctl show apcupsd.service state fields.",
        }

    if error_class in {"command_not_found", "timeout", "permission_denied", "command_failed"}:
        return {
            "likely_layer": "command",
            "reason": f"apcaccess command failed with class={error_class}.",
            "confidence": "medium",
            "next_read_only_check": "Run read-only apcaccess status probe and capture rc/stdout/stderr.",
        }

    return {
        "likely_layer": "unavailable",
        "reason": f"Unable to classify power telemetry: apcaccess class={error_class}, service active_state={active_state}.",
        "confidence": "low",
        "next_read_only_check": "Collect apcaccess rc/stdout/stderr and systemctl show apcupsd.service.",
    }


def collect_power_status(text: str | None = None, service_status: Mapping[str, Any] | None = None) -> dict[str, Any]:
    collected_at = utc_now_iso()
    if text is None:
        rc, stdout, stderr = run_apcaccess()
        source = "apcaccess status"
        source_type = "command"
        command_rc = rc
        command_error = stderr.strip()
        command_stdout = stdout
        data = parse_apcupsd_text(stdout) if rc == 0 else {}
    else:
        source = "apcupsd text"
        source_type = "provided_text"
        command_rc = 0
        command_error = ""
        command_stdout = text
        data = parse_apcupsd_text(text)

    command_error_class = classify_apcaccess_error(command_rc, command_stdout, command_error)
    command = {
        "apcaccess_ok": command_rc == 0 and bool(data),
        "command_rc": command_rc,
        "command_error": command_error,
        "command_error_class": command_error_class,
    }
    if service_status is not None:
        service = dict(service_status)
    elif text is None:
        service = collect_apcupsd_service_status()
    else:
        service = _empty_service_status()
    diagnosis_layer = build_diagnosis_layer(command, service, data)

    state, state_code, severity, severity_code = classify_power(data)
    freshness_code = FRESHNESS_CODES["fresh"] if data else FRESHNESS_CODES["unknown"]
    operation_state_code = OPERATION_STATE_CODES["completed"] if data else OPERATION_STATE_CODES["unknown"]
    status = _status(data) or "UNKNOWN"
    return {
        "agent_id": "power.status.ro",
        "collected_at": collected_at,
        "provider": "apcupsd/apcaccess",
        "source": source,
        "source_type": source_type,
        "command": command,
        "command_rc": command_rc,
        "command_error": command_error,
        "command_error_class": command_error_class,
        "service": service,
        "diagnosis_layer": diagnosis_layer,
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
