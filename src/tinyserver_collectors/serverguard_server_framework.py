"""Framework-compatible snapshot wrapper for serverguard.server.ro."""

from __future__ import annotations

import json
from typing import Any

from tinyserver_collectors.serverguard_server import collect_serverguard_server

TTL_SEC = 180
RULESET_VERSION = "1.0"


def _number(value: Any, default: int | float = 0) -> int | float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _metrics(raw: dict[str, Any]) -> dict[str, int | float]:
    payload = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    return {key: value for key, value in payload.items() if isinstance(value, (int, float)) and not isinstance(value, bool)}


def _check(raw: dict[str, Any], *, check_id: str, state: str, severity: int, confidence: str, summary: str, source: str, source_type: str, observed_value: str) -> dict[str, Any]:
    return {
        "state": state,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
        "rule_id": check_id,
        "ruleset_version": RULESET_VERSION,
        "evidence": {
            "source": source,
            "source_type": source_type,
            "command_class": "local_file_read" if source_type == "file" else "read_only",
            "observed_value": observed_value,
            "collected_at": str(raw.get("collected_at") or ""),
        },
    }


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    severity = int(_number(raw.get("severity_code"), 5))
    load = raw.get("load") if isinstance(raw.get("load"), dict) else {}
    memory = raw.get("memory") if isinstance(raw.get("memory"), dict) else {}
    root = raw.get("root_disk") if isinstance(raw.get("root_disk"), dict) else {}
    platform_info = raw.get("platform") if isinstance(raw.get("platform"), dict) else {}
    return {
        "server.hostname": _check(
            raw,
            check_id="server.hostname",
            state="OK" if raw.get("hostname") else "UNKNOWN",
            severity=0 if raw.get("hostname") else 5,
            confidence="high",
            summary=f"Hostname: {raw.get('hostname') or 'unknown'}.",
            source="socket.gethostname",
            source_type="derived",
            observed_value=str(raw.get("hostname") or "unknown"),
        ),
        "server.uptime": _check(
            raw,
            check_id="server.uptime",
            state="OK" if raw.get("uptime_seconds") is not None else "UNKNOWN",
            severity=0 if raw.get("uptime_seconds") is not None else 5,
            confidence="high" if raw.get("uptime_seconds") is not None else "medium",
            summary=f"Uptime seconds: {raw.get('uptime_seconds')}.",
            source="/proc/uptime",
            source_type="file",
            observed_value=f"uptime_seconds={raw.get('uptime_seconds')}",
        ),
        "server.load": _check(
            raw,
            check_id="server.load",
            state=state if load.get("1m") is not None else "UNKNOWN",
            severity=severity if load.get("1m") is not None else 5,
            confidence="high" if load.get("1m") is not None else "medium",
            summary=f"Load averages: 1m={load.get('1m')}, 5m={load.get('5m')}, 15m={load.get('15m')}.",
            source="/proc/loadavg",
            source_type="file",
            observed_value=f"load_1m={load.get('1m')} load_5m={load.get('5m')} load_15m={load.get('15m')}",
        ),
        "server.memory": _check(
            raw,
            check_id="server.memory",
            state=state if memory.get("used_percent") is not None else "UNKNOWN",
            severity=severity if memory.get("used_percent") is not None else 5,
            confidence="high" if memory.get("used_percent") is not None else "medium",
            summary=f"Memory used: {memory.get('used_percent')}%.",
            source="/proc/meminfo",
            source_type="file",
            observed_value=f"total={memory.get('total_bytes')} available={memory.get('available_bytes')} used_percent={memory.get('used_percent')}",
        ),
        "server.root_disk": _check(
            raw,
            check_id="server.root_disk",
            state=state if root.get("used_percent") is not None else "UNKNOWN",
            severity=severity if root.get("used_percent") is not None else 5,
            confidence="high" if root.get("used_percent") is not None else "medium",
            summary=f"Root disk used: {root.get('used_percent')}%.",
            source='shutil.disk_usage("/")',
            source_type="derived",
            observed_value=f"total={root.get('total_bytes')} used={root.get('used_bytes')} free={root.get('free_bytes')} used_percent={root.get('used_percent')}",
        ),
        "server.platform": _check(
            raw,
            check_id="server.platform",
            state="OK" if platform_info else "UNKNOWN",
            severity=0 if platform_info else 5,
            confidence="high" if platform_info else "medium",
            summary=f"Platform: {platform_info.get('system')} {platform_info.get('release')} {platform_info.get('machine')}.",
            source="platform.uname",
            source_type="derived",
            observed_value=(
                f"system={platform_info.get('system')} release={platform_info.get('release')} "
                f"machine={platform_info.get('machine')} processor={platform_info.get('processor')}"
            ),
        ),
    }


def to_framework_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN"}:
        state = "UNKNOWN"
    return {
        "schema_version": "1.0",
        "agent_id": "serverguard.server.ro",
        "product": "Tiny Agent Framework",
        "domain": "server",
        "display_name": "ServerGuard Server RO",
        "version": "0.1",
        "collected_at": str(raw.get("collected_at") or ""),
        "ttl_sec": TTL_SEC,
        "state": state,
        "severity": int(_number(raw.get("severity_code"), 5)),
        "summary": str(raw.get("summary") or "Server status UNKNOWN."),
        "checks": _checks(raw),
        "metrics": _metrics(raw),
        "links": [],
        "capabilities": {"read_only": True, "actions": []},
    }


def collect(output_root: object | None = None) -> dict[str, Any]:
    return to_framework_snapshot(collect_serverguard_server())


def main() -> int:
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
