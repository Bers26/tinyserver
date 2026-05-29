"""Read-only network.transport.ro snapshot and curl probe helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

BOOL_TRUE = 1
BOOL_FALSE = 0
BOOL_UNKNOWN = -1

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}

DEFAULT_SOCKS_PROXY = "socks5h://127.0.0.1:9050"
GITHUB_API_URL = "https://api.github.com/rate_limit"
GSTATIC_URL = "https://www.gstatic.com/generate_204"

REQUIRED_OUTPUT_FIELDS = (
    "agent_id", "collected_at", "direct_github_api_ok", "direct_github_api_ok_value",
    "socks_github_api_ok", "socks_github_api_ok_value", "direct_gstatic_ok",
    "direct_gstatic_ok_value", "socks_gstatic_ok", "socks_gstatic_ok_value",
    "socks_port_alive", "socks_port_alive_value", "direct_github_http_code",
    "socks_github_http_code", "direct_gstatic_http_code", "socks_gstatic_http_code",
    "direct_github_time_ms", "socks_github_time_ms", "direct_gstatic_time_ms",
    "socks_gstatic_time_ms", "transport_success_count", "transport_checked_count",
    "transport_hint", "state", "state_code", "severity", "severity_code",
    "freshness", "freshness_code", "operation_state", "operation_state_code",
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


CommandRunner = Callable[[Sequence[str], int | float], CommandResult]


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
        if normalized in {"1", "true", "yes", "y", "present", "ok", "up"}:
            return BOOL_TRUE
        if normalized in {"0", "false", "no", "n", "absent", "bad", "down"}:
            return BOOL_FALSE
        if normalized in {"", "unknown", "none", "null", "unreadable"}:
            return BOOL_UNKNOWN
    return BOOL_UNKNOWN


def as_bool(value: Any) -> bool | None:
    projected = bool_value(value)
    if projected == BOOL_TRUE:
        return True
    if projected == BOOL_FALSE:
        return False
    return None


def number(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _http_ok(value: Any) -> bool | None:
    code = number(value)
    if code is None or code <= 0:
        return None if code is None else False
    return 200 <= int(code) < 400


def parse_curl_probe(output: str, returncode: int) -> tuple[int | None, float | None, bool]:
    parts = output.strip().split()
    http_code: int | None = None
    time_ms: float | None = None
    if parts:
        try:
            http_code = int(parts[-2] if len(parts) >= 2 else parts[-1])
        except ValueError:
            http_code = None
    if len(parts) >= 2:
        try:
            time_ms = round(float(parts[-1]) * 1000, 3)
        except ValueError:
            time_ms = None
    ok = returncode == 0 and http_code is not None and 200 <= http_code < 400
    return http_code, time_ms, ok


def classify_state(facts: Mapping[str, Any]) -> tuple[str, int, str, int]:
    if as_bool(facts.get("collector_error")) is True:
        return "ERROR", STATE_CODES["ERROR"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]

    checked = int(number(facts.get("transport_checked_count"), 0) or 0)
    success = int(number(facts.get("transport_success_count"), 0) or 0)
    if checked <= 0:
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]

    direct_ok = as_bool(facts.get("direct_github_api_ok")) is True and as_bool(facts.get("direct_gstatic_ok")) is True
    socks_ok = as_bool(facts.get("socks_github_api_ok")) is True and as_bool(facts.get("socks_gstatic_ok")) is True
    github_ok = as_bool(facts.get("direct_github_api_ok")) is True or as_bool(facts.get("socks_github_api_ok")) is True
    gstatic_ok = as_bool(facts.get("direct_gstatic_ok")) is True or as_bool(facts.get("socks_gstatic_ok")) is True

    if direct_ok or socks_ok:
        return "OK", STATE_CODES["OK"], "normal", SEVERITY_CODES["normal"]
    if success <= 0:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
    if github_ok or gstatic_ok:
        return "WARN", STATE_CODES["WARN"], "degraded", SEVERITY_CODES["degraded"]
    return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]


def build_snapshot(facts: Mapping[str, Any], collected_at: str | None = None) -> dict[str, Any]:
    snapshot: dict[str, Any] = dict(facts)
    snapshot.setdefault("agent_id", "network.transport.ro")
    snapshot.setdefault("collected_at", collected_at or utc_now_iso())

    for key in (
        "direct_github_api_ok",
        "socks_github_api_ok",
        "direct_gstatic_ok",
        "socks_gstatic_ok",
        "socks_port_alive",
    ):
        snapshot[f"{key}_value"] = bool_value(snapshot.get(key))

    checked_keys = (
        "direct_github_api_ok",
        "socks_github_api_ok",
        "direct_gstatic_ok",
        "socks_gstatic_ok",
    )
    snapshot.setdefault("transport_checked_count", sum(1 for key in checked_keys if as_bool(snapshot.get(key)) is not None))
    snapshot.setdefault("transport_success_count", sum(1 for key in checked_keys if as_bool(snapshot.get(key)) is True))
    snapshot.setdefault("transport_hint", "not_evaluated")
    snapshot.setdefault("freshness", "fresh")
    snapshot.setdefault("freshness_code", FRESHNESS_CODES["fresh"])
    snapshot.setdefault("operation_state", "completed")
    snapshot.setdefault("operation_state_code", OPERATION_STATE_CODES["completed"])

    state, state_code, severity, severity_code = classify_state(snapshot)
    snapshot.update({"state": state, "state_code": state_code, "severity": severity, "severity_code": severity_code})

    defaults = {
        "direct_github_api_ok": None,
        "socks_github_api_ok": None,
        "direct_gstatic_ok": None,
        "socks_gstatic_ok": None,
        "socks_port_alive": None,
        "direct_github_http_code": None,
        "socks_github_http_code": None,
        "direct_gstatic_http_code": None,
        "socks_gstatic_http_code": None,
        "direct_github_time_ms": None,
        "socks_github_time_ms": None,
        "direct_gstatic_time_ms": None,
        "socks_gstatic_time_ms": None,
    }
    for key, value in defaults.items():
        snapshot.setdefault(key, value)
    for key in REQUIRED_OUTPUT_FIELDS:
        snapshot.setdefault(key, None)
    return {key: snapshot[key] for key in REQUIRED_OUTPUT_FIELDS}


def _curl_command(url: str, *, socks_proxy: str | None = None) -> tuple[str, ...]:
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--location",
        "--max-time",
        "5",
        "--connect-timeout",
        "3",
        "--output",
        "/dev/null",
        "--write-out",
        "%{http_code} %{time_total}",
    ]
    if socks_proxy:
        command.extend(["--proxy", socks_proxy])
    command.append(url)
    return tuple(command)


def _run_probe(command_runner: CommandRunner, command: tuple[str, ...], timeout: int | float) -> tuple[int | None, float | None, bool]:
    result = command_runner(command, timeout)
    return parse_curl_probe(result.stdout, result.returncode)


def collect_network_transport(
    command_runner: CommandRunner,
    *,
    timeout: int | float = 7,
    socks_proxy: str = DEFAULT_SOCKS_PROXY,
    collected_at: str | None = None,
) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "agent_id": "network.transport.ro",
        "transport_hint": "not_evaluated",
    }

    try:
        direct_github_code, direct_github_ms, direct_github_ok = _run_probe(
            command_runner, _curl_command(GITHUB_API_URL), timeout
        )
        socks_github_code, socks_github_ms, socks_github_ok = _run_probe(
            command_runner, _curl_command(GITHUB_API_URL, socks_proxy=socks_proxy), timeout
        )
        direct_gstatic_code, direct_gstatic_ms, direct_gstatic_ok = _run_probe(
            command_runner, _curl_command(GSTATIC_URL), timeout
        )
        socks_gstatic_code, socks_gstatic_ms, socks_gstatic_ok = _run_probe(
            command_runner, _curl_command(GSTATIC_URL, socks_proxy=socks_proxy), timeout
        )

        facts.update(
            {
                "direct_github_api_ok": direct_github_ok,
                "socks_github_api_ok": socks_github_ok,
                "direct_gstatic_ok": direct_gstatic_ok,
                "socks_gstatic_ok": socks_gstatic_ok,
                "socks_port_alive": (
                    (socks_github_code is not None and socks_github_code > 0)
                    or (socks_gstatic_code is not None and socks_gstatic_code > 0)
                ),
                "direct_github_http_code": direct_github_code,
                "socks_github_http_code": socks_github_code,
                "direct_gstatic_http_code": direct_gstatic_code,
                "socks_gstatic_http_code": socks_gstatic_code,
                "direct_github_time_ms": direct_github_ms,
                "socks_github_time_ms": socks_github_ms,
                "direct_gstatic_time_ms": direct_gstatic_ms,
                "socks_gstatic_time_ms": socks_gstatic_ms,
            }
        )
        facts["transport_hint"] = "transport_available" if any(
            (direct_github_ok, socks_github_ok, direct_gstatic_ok, socks_gstatic_ok)
        ) else "transport_unavailable"
    except Exception as exc:
        facts["collector_error"] = True
        facts["transport_hint"] = f"collector_error:{type(exc).__name__}"
        snapshot = build_snapshot(facts, collected_at=collected_at)
        snapshot["operation_state"] = "failed"
        snapshot["operation_state_code"] = OPERATION_STATE_CODES["failed"]
        return snapshot

    return build_snapshot(facts, collected_at=collected_at)
