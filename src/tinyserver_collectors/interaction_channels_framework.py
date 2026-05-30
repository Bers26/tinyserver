"""Framework-compatible snapshot wrapper for interaction.channels.ro."""

from __future__ import annotations

from typing import Any

from tinyserver_collectors.interaction_channels import collect_interaction_channels

TTL_SEC = 300
RULESET_VERSION = "1.0"
REQUIRED_CHECK_IDS = {
    "interaction.telegram.channel",
    "interaction.big_ui.channel",
    "interaction.llm.channel",
    "interaction.voice.channel",
}
SOURCE_TYPE_MAP = {
    "api": "api",
    "local_http": "api",
    "command": "command",
    "file": "file",
    "derived": "derived",
    "collector": "derived",
    "static": "static",
    "injected_fact": "static",
    "none": "static",
    "deferred": "static",
    "unknown": "static",
}


def _contract_severity(value: Any, default: int = 4) -> int:
    try:
        severity = int(value)
    except (TypeError, ValueError):
        severity = default
    if severity < 0:
        return 0
    if severity > 4:
        return 4
    return severity


def _metrics(raw: dict[str, Any]) -> dict[str, int | float]:
    payload = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    keys = [
        "channels_total",
        "channels_ok",
        "channels_warn",
        "channels_bad",
        "channels_unknown",
        "channels_deferred",
        "operation_state_code",
    ]
    metrics = {key: raw.get(key, payload.get(key)) for key in keys}
    return {
        key: value
        for key, value in metrics.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def _schema_source_type(value: Any) -> str:
    return SOURCE_TYPE_MAP.get(str(value or "unknown"), "static")


def _command_class(source_type: str) -> str:
    if source_type == "api":
        return "api_read"
    if source_type == "command":
        return "read_only"
    if source_type == "file":
        return "local_file_read"
    if source_type == "derived":
        return "derived"
    return "static"


def _check(raw: dict[str, Any], *, channel_id: str, channel: dict[str, Any]) -> dict[str, Any]:
    state = str(channel.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN"}:
        state = "UNKNOWN"

    source_type = _schema_source_type(channel.get("source_type"))
    command_class = _command_class(source_type)

    return {
        "state": state,
        "severity": _contract_severity(channel.get("severity_code"), 4),
        "confidence": "high" if state in {"OK", "BAD"} else "medium",
        "summary": str(channel.get("summary") or f"{channel_id} channel status unknown."),
        "rule_id": f"interaction.{channel_id}.channel",
        "ruleset_version": RULESET_VERSION,
        "evidence": {
            "source": str(channel.get("source") or "unknown"),
            "source_type": source_type,
            "command_class": command_class,
            "observed_value": (
                f"configured={channel.get('configured_value')} "
                f"ok={channel.get('ok_value')} "
                f"deferred={channel.get('deferred_value')} "
                f"critical={channel.get('critical_value')} "
                f"detail={channel.get('detail') or ''}"
            ),
            "collected_at": str(raw.get("collected_at") or ""),
        },
    }


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    channels = raw.get("channels") if isinstance(raw.get("channels"), dict) else {}
    return {
        f"interaction.{name}.channel": _check(
            raw,
            channel_id=name,
            channel=channels.get(name) if isinstance(channels.get(name), dict) else {},
        )
        for name in ("telegram", "big_ui", "llm", "voice")
    }


def to_framework_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN"}:
        state = "UNKNOWN"
    return {
        "schema_version": "1.0",
        "agent_id": "interaction.channels.ro",
        "product": "Tiny Agent Framework",
        "domain": "interaction",
        "display_name": "Interaction Channels RO",
        "version": "0.1",
        "collected_at": str(raw.get("collected_at") or ""),
        "ttl_sec": TTL_SEC,
        "state": state,
        "severity": _contract_severity(raw.get("severity_code"), 4),
        "summary": str(raw.get("summary") or "Interaction channels UNKNOWN."),
        "checks": _checks(raw),
        "metrics": _metrics(raw),
        "links": [],
        "capabilities": {"read_only": True, "actions": []},
    }


def collect(output_root: object | None = None) -> dict[str, Any]:
    return to_framework_snapshot(collect_interaction_channels())
