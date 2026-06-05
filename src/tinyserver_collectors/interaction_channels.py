"""Read-only interaction.channels.ro collector helpers.

The collector only classifies local/injected channel facts. It does not read
secrets, call Telegram, call external LLM APIs, or execute actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BOOL_TRUE = 1
BOOL_FALSE = 0
BOOL_UNKNOWN = -1

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}

AGENT_ID = "interaction.channels.ro"
DEFAULT_BIG_UI_URL = "http://127.0.0.1:8787/api/health"
CHANNELS = ("telegram", "big_ui", "llm", "voice")
CRITICAL_CHANNELS = {"big_ui", "llm"}


@dataclass(frozen=True)
class ProbeResult:
    ok: bool | None
    status_code: int | None = None
    detail: str = ""


HttpProbe = Callable[[str, int | float], ProbeResult]


def default_http_probe(url: str, timeout: int | float) -> ProbeResult:
    """Run a bounded local HTTP GET and normalize the result."""
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = int(response.status)
            return ProbeResult(ok=200 <= status_code < 400, status_code=status_code)
    except HTTPError as exc:
        return ProbeResult(ok=False, status_code=int(exc.code), detail="http_error")
    except (OSError, URLError) as exc:
        return ProbeResult(ok=False, status_code=None, detail=type(exc).__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def bool_value(value: Any) -> int:
    if value is True:
        return BOOL_TRUE
    if value is False:
        return BOOL_FALSE
    if value is None:
        return BOOL_UNKNOWN
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return BOOL_TRUE
        if value == 0:
            return BOOL_FALSE
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "up", "present", "ok", "available", "configured"}:
            return BOOL_TRUE
        if normalized in {"0", "false", "no", "n", "down", "absent", "bad", "fail", "failed", "unavailable"}:
            return BOOL_FALSE
        if normalized in {"", "unknown", "none", "null", "unreadable", "unconfigured"}:
            return BOOL_UNKNOWN
    return BOOL_UNKNOWN


def as_bool(value: Any) -> bool | None:
    projected = bool_value(value)
    if projected == BOOL_TRUE:
        return True
    if projected == BOOL_FALSE:
        return False
    return None


def _state_code(state: str) -> int:
    return STATE_CODES.get(state, STATE_CODES["UNKNOWN"])


def _severity_for_state(state: str, *, critical: bool = False) -> tuple[str, int]:
    if state == "OK":
        return "normal", SEVERITY_CODES["normal"]
    if state == "BAD":
        severity = "critical" if critical else "warning"
        return severity, SEVERITY_CODES[severity]
    if state == "ERROR":
        return "unknown_or_error", SEVERITY_CODES["unknown_or_error"]
    return "unknown_or_error", SEVERITY_CODES["unknown_or_error"]


def _status_from_mapping(
    channel: str,
    value: Mapping[str, Any],
    *,
    default_source_type: str,
    default_source: str,
) -> dict[str, Any]:
    configured = as_bool(value.get("configured"))
    deferred = as_bool(value.get("deferred")) is True
    ok = as_bool(value.get("ok", value.get("available")))
    source_type = str(value.get("source_type") or default_source_type)
    source = str(value.get("source") or default_source)
    detail = str(value.get("detail") or value.get("summary") or "")
    critical = channel in CRITICAL_CHANNELS

    if deferred:
        configured = False if configured is None else configured
        state = "UNKNOWN"
        summary = f"{channel} channel is deferred."
    elif ok is True:
        state = "OK"
        summary = f"{channel} channel is available."
        configured = True if configured is None else configured
    elif configured is False:
        state = "UNKNOWN"
        summary = f"{channel} channel is not configured."
    elif ok is False:
        if configured is True:
            state = "BAD"
            summary = f"{channel} channel is configured but unavailable."
        else:
            state = "UNKNOWN"
            summary = f"{channel} channel availability is unknown."
    else:
        state = "UNKNOWN"
        summary = f"{channel} channel has no status source."

    severity, severity_code = _severity_for_state(state, critical=critical)
    return {
        "name": channel,
        "state": state,
        "state_code": _state_code(state),
        "severity": severity,
        "severity_code": severity_code,
        "configured": configured,
        "configured_value": bool_value(configured),
        "ok": ok,
        "ok_value": bool_value(ok),
        "deferred": deferred,
        "deferred_value": bool_value(deferred),
        "critical": critical,
        "critical_value": bool_value(critical),
        "source": source,
        "source_type": source_type,
        "detail": detail,
        "summary": summary,
    }


def _unknown_channel(channel: str, *, source_type: str, source: str, deferred: bool = False) -> dict[str, Any]:
    return _status_from_mapping(
        channel,
        {"configured": False if source == "not_configured" else None, "ok": None, "deferred": deferred, "source_type": source_type, "source": source},
        default_source_type=source_type,
        default_source=source,
    )


def _big_ui_channel(http_probe: HttpProbe | None, target_url: str, timeout: int | float) -> dict[str, Any]:
    if http_probe is None:
        return _unknown_channel("big_ui", source_type="local_http", source=target_url)
    result = http_probe(target_url, timeout)
    return _status_from_mapping(
        "big_ui",
        {
            "configured": True,
            "ok": result.ok,
            "source_type": "local_http",
            "source": target_url,
            "detail": f"status_code={result.status_code} {result.detail}".strip(),
        },
        default_source_type="local_http",
        default_source=target_url,
    )


def classify_state(channels: Mapping[str, Mapping[str, Any]], *, collector_error: bool = False) -> tuple[str, int, str, int]:
    if collector_error:
        return "ERROR", STATE_CODES["ERROR"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]

    if any(
        channel.get("critical") is True and channel.get("configured") is True and channel.get("state") == "BAD"
        for channel in channels.values()
    ):
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]

    if any(
        channel.get("critical") is True
        and channel.get("deferred") is not True
        and channel.get("state") in {"BAD", "UNKNOWN"}
        for channel in channels.values()
    ):
        return "WARN", STATE_CODES["WARN"], "warning", SEVERITY_CODES["warning"]

    if any(
        channel.get("critical") is not True
        and channel.get("configured") is True
        and channel.get("state") == "BAD"
        for channel in channels.values()
    ):
        return "WARN", STATE_CODES["WARN"], "warning", SEVERITY_CODES["warning"]

    return "OK", STATE_CODES["OK"], "normal", SEVERITY_CODES["normal"]

def _counts(channels: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    values = list(channels.values())
    states = [str(channel.get("state") or "UNKNOWN").upper() for channel in values]
    critical_unknown = sum(
        1
        for channel in values
        if channel.get("critical") is True
        and channel.get("deferred") is not True
        and str(channel.get("state") or "UNKNOWN").upper() == "UNKNOWN"
    )
    not_configured = sum(
        1
        for channel in values
        if channel.get("configured") is False and channel.get("deferred") is not True
    )
    actionable_unknown = sum(
        1
        for channel in values
        if channel.get("deferred") is not True
        and str(channel.get("state") or "UNKNOWN").upper() == "UNKNOWN"
        and (channel.get("critical") is True or channel.get("configured") is True)
    )
    return {
        "channels_total": len(states),
        "channels_ok": states.count("OK"),
        "channels_warn": states.count("WARN"),
        "channels_bad": states.count("BAD"),
        "channels_unknown": states.count("UNKNOWN"),
        "channels_deferred": sum(1 for channel in values if channel.get("deferred") is True),
        "channels_critical_unknown": critical_unknown,
        "channels_not_configured": not_configured,
        "channels_actionable_unknown": actionable_unknown,
    }

def collect_interaction_channels(
    *,
    big_ui_probe: HttpProbe | None = None,
    big_ui_url: str = DEFAULT_BIG_UI_URL,
    telegram_status: Mapping[str, Any] | str | bool | None = None,
    llm_status: Mapping[str, Any] | str | bool | None = None,
    voice_status: Mapping[str, Any] | str | bool | None = None,
    timeout: int | float = 3,
    collected_at: str | None = None,
) -> dict[str, Any]:
    facts: dict[str, Any] = {"agent_id": AGENT_ID}
    try:
        channels: dict[str, dict[str, Any]] = {
            "telegram": _status_from_mapping(
                "telegram",
                telegram_status if isinstance(telegram_status, Mapping) else {"ok": telegram_status},
                default_source_type="injected_fact" if telegram_status is not None else "none",
                default_source="telegram_status",
            )
            if telegram_status is not None
            else _unknown_channel("telegram", source_type="none", source="not_configured"),
            "big_ui": _big_ui_channel(big_ui_probe, big_ui_url, timeout),
            "llm": _status_from_mapping(
                "llm",
                llm_status if isinstance(llm_status, Mapping) else {"ok": llm_status},
                default_source_type="injected_fact" if llm_status is not None else "none",
                default_source="llm_status",
            )
            if llm_status is not None
            else _unknown_channel("llm", source_type="none", source="llm_status"),
            "voice": _status_from_mapping(
                "voice",
                voice_status if isinstance(voice_status, Mapping) else {"ok": voice_status},
                default_source_type="injected_fact" if voice_status is not None else "deferred",
                default_source="voice_status",
            )
            if voice_status is not None
            else _unknown_channel("voice", source_type="deferred", source="voice_interface", deferred=True),
        }
        state, state_code, severity, severity_code = classify_state(channels)
    except Exception as exc:
        channels = {
            name: _unknown_channel(name, source_type="collector", source=f"collector_error:{type(exc).__name__}")
            for name in CHANNELS
        }
        state, state_code, severity, severity_code = classify_state(channels, collector_error=True)
        facts["collector_error"] = True

    counts = _counts(channels)
    metrics = {
        **counts,
        "freshness_code": FRESHNESS_CODES["fresh"],
        "operation_state_code": OPERATION_STATE_CODES["failed"] if facts.get("collector_error") else OPERATION_STATE_CODES["completed"],
    }
    facts.update(
        {
            "collected_at": collected_at or utc_now_iso(),
            "channels": channels,
            **counts,
            "state": state,
            "state_code": state_code,
            "severity": severity,
            "severity_code": severity_code,
            "summary": f"Interaction channels {state}: ok={counts['channels_ok']}, bad={counts['channels_bad']}, critical_unknown={counts['channels_critical_unknown']}, not_configured={counts['channels_not_configured']}, deferred={counts['channels_deferred']}.",
            "freshness": "fresh",
            "freshness_code": FRESHNESS_CODES["fresh"],
            "operation_state": "failed" if facts.get("collector_error") else "completed",
            "operation_state_code": metrics["operation_state_code"],
            "metrics": metrics,
        }
    )
    return facts
