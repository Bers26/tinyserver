"""Read-only serverguard.server.ro collector helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import shutil
import socket
from typing import Any

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_uptime(path: str | Path = "/proc/uptime") -> float | None:
    try:
        first = Path(path).read_text(encoding="utf-8").split()[0]
        return float(first)
    except (OSError, IndexError, ValueError):
        return None


def read_loadavg(path: str | Path = "/proc/loadavg") -> tuple[float | None, float | None, float | None]:
    try:
        parts = Path(path).read_text(encoding="utf-8").split()
        return float(parts[0]), float(parts[1]), float(parts[2])
    except (OSError, IndexError, ValueError):
        return None, None, None


def read_meminfo(path: str | Path = "/proc/meminfo") -> dict[str, int]:
    data: dict[str, int] = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return data
    for line in lines:
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.strip().split()
        if not parts:
            continue
        try:
            value = int(parts[0])
        except ValueError:
            continue
        data[key] = value * 1024 if len(parts) > 1 and parts[1].lower() == "kb" else value
    return data


def _used_percent(total: int | None, available: int | None) -> float | None:
    if not total or total <= 0 or available is None:
        return None
    return round(((total - available) / total) * 100, 3)


def _classify(load_1m: float | None, cpu_count: int, memory_used_percent: float | None, root_used_percent: float | None) -> tuple[str, int, str, int]:
    if load_1m is None or memory_used_percent is None or root_used_percent is None:
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]
    load_per_cpu = load_1m / max(cpu_count, 1)
    if root_used_percent >= 95 or memory_used_percent >= 95 or load_per_cpu >= 4:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
    if root_used_percent >= 85 or memory_used_percent >= 90 or load_per_cpu >= 2:
        return "WARN", STATE_CODES["WARN"], "degraded", SEVERITY_CODES["degraded"]
    if root_used_percent >= 75 or memory_used_percent >= 80 or load_per_cpu >= 1:
        return "WARN", STATE_CODES["WARN"], "warning", SEVERITY_CODES["warning"]
    return "OK", STATE_CODES["OK"], "normal", SEVERITY_CODES["normal"]


def collect_serverguard_server(
    *,
    uptime_path: str | Path = "/proc/uptime",
    loadavg_path: str | Path = "/proc/loadavg",
    meminfo_path: str | Path = "/proc/meminfo",
    root_path: str | Path = "/",
) -> dict[str, Any]:
    uptime_seconds = read_uptime(uptime_path)
    load_1m, load_5m, load_15m = read_loadavg(loadavg_path)
    meminfo = read_meminfo(meminfo_path)
    cpu_count = os.cpu_count() or 1
    memory_total = meminfo.get("MemTotal")
    memory_available = meminfo.get("MemAvailable")
    memory_used_percent = _used_percent(memory_total, memory_available)
    disk = shutil.disk_usage(root_path)
    root_used_percent = round((disk.used / disk.total) * 100, 3) if disk.total > 0 else None
    uname = platform.uname()
    hostname = socket.gethostname()
    state, state_code, severity, severity_code = _classify(load_1m, cpu_count, memory_used_percent, root_used_percent)
    metrics: dict[str, int | float] = {
        "cpu_count": cpu_count,
        "freshness_code": FRESHNESS_CODES["fresh"],
        "operation_state_code": OPERATION_STATE_CODES["completed"],
    }
    for key, value in {
        "uptime_seconds": uptime_seconds,
        "load_1m": load_1m,
        "load_5m": load_5m,
        "load_15m": load_15m,
        "memory_total_bytes": memory_total,
        "memory_available_bytes": memory_available,
        "memory_used_percent": memory_used_percent,
        "root_used_percent": root_used_percent,
    }.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            metrics[key] = value
    return {
        "agent_id": "serverguard.server.ro",
        "collected_at": utc_now_iso(),
        "hostname": hostname,
        "uptime_seconds": uptime_seconds,
        "load": {"1m": load_1m, "5m": load_5m, "15m": load_15m},
        "cpu_count": cpu_count,
        "memory": {
            "total_bytes": memory_total,
            "available_bytes": memory_available,
            "used_percent": memory_used_percent,
        },
        "root_disk": {
            "path": str(root_path),
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "used_percent": root_used_percent,
        },
        "platform": {
            "system": uname.system,
            "node": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
        },
        "state": state,
        "state_code": state_code,
        "severity": severity,
        "severity_code": severity_code,
        "summary": f"Server {hostname}: load={load_1m}, memory={memory_used_percent}%, root={root_used_percent}%.",
        "freshness": "fresh",
        "freshness_code": FRESHNESS_CODES["fresh"],
        "operation_state": "completed",
        "operation_state_code": OPERATION_STATE_CODES["completed"],
        "metrics": metrics,
    }
