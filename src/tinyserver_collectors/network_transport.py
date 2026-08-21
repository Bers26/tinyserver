"""Read-only network.transport.ro snapshot and transport probe helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse
import ipaddress

BOOL_TRUE = 1
BOOL_FALSE = 0
BOOL_UNKNOWN = -1

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}

DEFAULT_SOCKS_PROXY = "socks5h://127.0.0.1:10808"
GITHUB_API_URL = "https://api.github.com/rate_limit"
GSTATIC_URL = "https://www.gstatic.com/generate_204"
TELEGRAM_API_URL = "https://api.telegram.org/"
DNS_TARGETS = ("github.com", "ssh.github.com", "api.telegram.org")
TCP_TARGETS = (("github.com", 443), ("ssh.github.com", 443), ("api.telegram.org", 443))
HTTPS_TARGETS = (
    ("direct_github_api", GITHUB_API_URL, None),
    ("socks_github_api", GITHUB_API_URL, "socks"),
    ("direct_gstatic", GSTATIC_URL, None),
    ("socks_gstatic", GSTATIC_URL, "socks"),
    ("direct_telegram_api", TELEGRAM_API_URL, None),
    ("socks_telegram_api", TELEGRAM_API_URL, "socks"),
)
RU_GOV_TARGETS = (
    "gosuslugi.ru",
    "www.gosuslugi.ru",
    "esia.gosuslugi.ru",
    "nalog.gov.ru",
    "www.nalog.gov.ru",
)
VPN_ROUTE_DEV_PREFIXES = ("tun", "tap", "wg", "sing", "tailscale", "zt")
DIRECT_ROUTE_DEV_PREFIXES = ("en", "eth", "wlan")

REQUIRED_OUTPUT_FIELDS = (
    "agent_id", "collected_at", "schema_version", "collector_version", "attempts",
    "socks_proxy_configured", "git_probe_configured", "direct_github_api_ok",
    "direct_github_api_ok_value", "socks_github_api_ok", "socks_github_api_ok_value",
    "direct_gstatic_ok", "direct_gstatic_ok_value", "socks_gstatic_ok",
    "socks_gstatic_ok_value", "socks_port_alive", "socks_port_alive_value",
    "direct_telegram_api_ok", "direct_telegram_api_ok_value",
    "socks_telegram_api_ok", "socks_telegram_api_ok_value",
    "dns_github_ok", "dns_github_ok_value", "dns_ssh_github_ok",
    "dns_ssh_github_ok_value", "dns_telegram_ok", "dns_telegram_ok_value",
    "tcp_github_443_ok", "tcp_github_443_ok_value",
    "tcp_ssh_github_443_ok", "tcp_ssh_github_443_ok_value",
    "tcp_telegram_443_ok", "tcp_telegram_443_ok_value",
    "socks_ssh_github_443_ok", "socks_ssh_github_443_ok_value",
    "git_transport_ok", "git_transport_ok_value", "git_transport_state",
    "direct_github_http_code", "socks_github_http_code", "direct_gstatic_http_code",
    "socks_gstatic_http_code", "direct_github_time_ms", "socks_github_time_ms",
    "direct_gstatic_time_ms", "socks_gstatic_time_ms", "transport_success_count",
    "direct_telegram_http_code", "socks_telegram_http_code",
    "direct_telegram_time_ms", "socks_telegram_time_ms",
    "transport_checked_count", "failed_targets", "likely_failure_layer", "burst",
    "transport_hint", "ru_gov_targets", "ru_gov_checked_count", "ru_gov_reachable_count",
    "ru_gov_success_rate", "ru_gov_direct_route_count", "ru_gov_vpn_leak_count",
    "ru_gov_failed_targets", "ru_gov_route_leak_targets", "ru_gov_reachable_value",
    "ru_gov_direct_route_value", "reachability_split_hint", "route_policy_hint",
    "state", "state_code", "severity", "severity_code", "freshness",
    "freshness_code", "operation_state", "operation_state_code",
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
        if normalized in {"", "unknown", "none", "null", "unreadable", "disabled"}:
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


def _safe_attempts(value: Any) -> int:
    try:
        attempts = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(attempts, 10))


def _socks_host_port(proxy: str) -> tuple[str, int]:
    parsed = urlparse(proxy)
    return parsed.hostname or "127.0.0.1", parsed.port or 10808


def _target_key(prefix: str, host: str, port: int | None = None) -> str:
    host_labels = {
        "github.com": "github",
        "ssh.github.com": "ssh_github",
        "api.telegram.org": "telegram",
    }
    normalized_host = host_labels.get(host, host.replace(".", "_").replace("-", "_"))
    if port is None:
        return f"{prefix}_{normalized_host}"
    return f"{prefix}_{normalized_host}_{port}"


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


def parse_ru_gov_curl_probe(output: str, returncode: int) -> tuple[int | None, float | None, bool, bool]:
    http_code, time_ms, _ok = parse_curl_probe(output, returncode)
    reachable = (
        returncode == 0
        and http_code is not None
        and (200 <= http_code < 400 or http_code in {401, 403, 429} or 500 <= http_code < 600)
    )
    degraded = returncode == 0 and http_code is not None and 500 <= http_code < 600
    return http_code, time_ms, reachable, degraded


def _simple_ok(result: CommandResult) -> bool:
    return result.returncode == 0


def _dns_ok(result: CommandResult) -> bool:
    return result.returncode == 0 and bool(result.stdout.strip())


def _stats(outcomes: Sequence[bool | None], collected_at: str) -> dict[str, Any]:
    checked = [value for value in outcomes if value is not None]
    success_count = sum(1 for value in checked if value is True)
    failure_count = sum(1 for value in checked if value is False)
    consecutive_failures = 0
    for value in reversed(checked):
        if value is False:
            consecutive_failures += 1
        else:
            break
    success_rate = None if not checked else round(success_count / len(checked), 3)
    return {
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": success_rate,
        "consecutive_failures": consecutive_failures,
        "last_ok_at": collected_at if success_count else None,
        "last_fail_at": collected_at if failure_count else None,
    }


def _last_bool(outcomes: Sequence[bool | None]) -> bool | None:
    for value in reversed(outcomes):
        if value is not None:
            return value
    return None


def _run_attempts(
    command_runner: CommandRunner,
    command: tuple[str, ...],
    timeout: int | float,
    attempts: int,
    parser: Callable[[CommandResult], bool | None],
) -> tuple[list[bool | None], list[CommandResult]]:
    outcomes: list[bool | None] = []
    results: list[CommandResult] = []
    for _ in range(_safe_attempts(attempts)):
        result = command_runner(command, timeout)
        results.append(result)
        outcomes.append(parser(result))
    return outcomes, results


def _dns_command(host: str) -> tuple[str, ...]:
    return ("getent", "hosts", host)


def _tcp_command(host: str, port: int) -> tuple[str, ...]:
    script = (
        "import socket,sys;"
        "host=sys.argv[1];port=int(sys.argv[2]);timeout=float(sys.argv[3]);"
        "s=socket.create_connection((host,port),timeout);s.close()"
    )
    return ("python3", "-c", script, host, str(port), "3")


def _socks_target_command(proxy: str, host: str, port: int) -> tuple[str, ...]:
    proxy_host, proxy_port = _socks_host_port(proxy)
    return ("nc", "-X", "5", "-x", f"{proxy_host}:{proxy_port}", "-z", "-w", "3", host, str(port))


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


def _git_command(url: str) -> tuple[str, ...]:
    return ("git", "ls-remote", "--heads", url)


def _route_command(ip_address: str) -> tuple[str, ...]:
    return ("ip", "route", "get", ip_address)


def _first_resolved_ip(output: str) -> str | None:
    for token in output.replace("\n", " " ).split():
        try:
            ipaddress.ip_address(token)
        except ValueError:
            continue
        return token
    return None


def _parse_route_output(output: str) -> dict[str, Any]:
    tokens = output.replace("\n", " " ).split()
    route_dev: str | None = None
    if "dev" in tokens:
        index = tokens.index("dev")
        if index + 1 < len(tokens):
            route_dev = tokens[index + 1]
    route_src_present = "src" in tokens
    route_via_vpn = (
        any(route_dev.startswith(prefix) for prefix in VPN_ROUTE_DEV_PREFIXES)
        if route_dev
        else None
    )
    direct_route = (
        any(route_dev.startswith(prefix) for prefix in DIRECT_ROUTE_DEV_PREFIXES)
        if route_dev
        else None
    )
    return {
        "route_dev": route_dev,
        "route_src_present_value": bool_value(route_src_present),
        "route_via_vpn_value": bool_value(route_via_vpn),
        "direct_route_value": bool_value(direct_route),
        "route_raw": output.strip(),
    }


def _run_http_probe(
    command_runner: CommandRunner,
    command: tuple[str, ...],
    timeout: int | float,
    attempts: int,
) -> tuple[list[bool | None], int | None, float | None]:
    last_code: int | None = None
    last_ms: float | None = None

    def parser(result: CommandResult) -> bool | None:
        nonlocal last_code, last_ms
        code, elapsed_ms, ok = parse_curl_probe(result.stdout, result.returncode)
        last_code = code
        last_ms = elapsed_ms
        return ok

    outcomes, _results = _run_attempts(command_runner, command, timeout, attempts, parser)
    return outcomes, last_code, last_ms


def _run_ru_gov_http_probe(
    command_runner: CommandRunner,
    command: tuple[str, ...],
    timeout: int | float,
    attempts: int,
) -> tuple[list[bool | None], int | None, float | None, bool]:
    last_code: int | None = None
    last_ms: float | None = None
    degraded = False

    def parser(result: CommandResult) -> bool | None:
        nonlocal last_code, last_ms, degraded
        code, elapsed_ms, reachable, is_degraded = parse_ru_gov_curl_probe(result.stdout, result.returncode)
        last_code = code
        last_ms = elapsed_ms
        degraded = is_degraded
        return reachable

    outcomes, _results = _run_attempts(command_runner, command, timeout, attempts, parser)
    return outcomes, last_code, last_ms, degraded


def _failed_targets(burst: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return [target for target, stats in burst.items() if int(stats.get("failure_count") or 0) > 0]


def _likely_failure_layer(facts: Mapping[str, Any]) -> str:
    burst = facts.get("burst") if isinstance(facts.get("burst"), Mapping) else {}
    if any(
        isinstance(stats, Mapping)
        and stats.get("success_rate") is not None
        and 0 < float(stats.get("success_rate") or 0) < 1
        for stats in burst.values()
    ):
        return "mixed_flapping"
    if any(as_bool(facts.get(key)) is False for key in ("dns_github_ok", "dns_ssh_github_ok", "dns_telegram_ok")):
        return "dns"
    if any(as_bool(facts.get(key)) is False for key in ("tcp_github_443_ok", "tcp_ssh_github_443_ok", "tcp_telegram_443_ok")):
        return "tcp_direct"
    if as_bool(facts.get("socks_port_alive")) is False or as_bool(facts.get("socks_ssh_github_443_ok")) is False:
        return "socks_proxy"
    https_values = (
        as_bool(facts.get("direct_github_api_ok")),
        as_bool(facts.get("socks_github_api_ok")),
        as_bool(facts.get("direct_gstatic_ok")),
        as_bool(facts.get("socks_gstatic_ok")),
        as_bool(facts.get("direct_telegram_api_ok")),
        as_bool(facts.get("socks_telegram_api_ok")),
    )
    if any(value is False for value in https_values):
        return "https"
    if str(facts.get("git_transport_state") or "").lower() == "failed":
        return "git_transport"
    return "unknown"


def _ru_gov_failed_targets(targets: Sequence[Mapping[str, Any]]) -> list[str]:
    failed: list[str] = []
    for target in targets:
        host = str(target.get("host") or "")
        if not host:
            continue
        if (
            as_bool(target.get("dns_ok")) is False
            or as_bool(target.get("tcp_443_ok")) is False
            or as_bool(target.get("https_reachable")) is False
        ):
            failed.append(host)
    return failed


def _ru_gov_route_leak_targets(targets: Sequence[Mapping[str, Any]]) -> list[str]:
    leaked: list[str] = []
    for target in targets:
        host = str(target.get("host") or "")
        if host and as_bool(target.get("route_via_vpn_value")) is True:
            leaked.append(host)
    return leaked


def _route_policy_hint(facts: Mapping[str, Any]) -> str:
    checked = int(number(facts.get("ru_gov_checked_count"), 0) or 0)
    if checked <= 0:
        return "no_ru_gov_evidence"
    if int(number(facts.get("ru_gov_vpn_leak_count"), 0) or 0) > 0:
        return "ru_gov_route_leak"
    if int(number(facts.get("ru_gov_direct_route_count"), 0) or 0) == checked:
        return "ru_gov_direct_ok"
    return "ru_gov_route_unknown"


def _reachability_split_hint(facts: Mapping[str, Any]) -> str:
    ru_checked = int(number(facts.get("ru_gov_checked_count"), 0) or 0)
    if ru_checked <= 0:
        return "no_evidence"

    transport_checked = int(number(facts.get("transport_checked_count"), 0) or 0)
    transport_success = int(number(facts.get("transport_success_count"), 0) or 0)
    ru_reachable = int(number(facts.get("ru_gov_reachable_count"), 0) or 0)
    ru_degraded = int(number(facts.get("ru_gov_degraded_count"), 0) or 0)

    external_ok = transport_checked > 0 and transport_success == transport_checked
    external_degraded = transport_checked > 0 and transport_success < transport_checked
    ru_ok = ru_reachable == ru_checked and ru_degraded == 0
    ru_has_degraded = ru_reachable < ru_checked or ru_degraded > 0

    if external_ok and ru_ok:
        return "external_and_ru_gov_ok"
    if external_degraded and ru_reachable == ru_checked:
        return "external_degraded_ru_gov_reachable"
    if external_ok and ru_has_degraded:
        return "external_ok_ru_gov_degraded"
    if external_degraded and ru_has_degraded:
        return "global_connectivity_degraded"
    if facts.get("likely_failure_layer") == "mixed_flapping":
        return "mixed_flapping"
    return "unknown"


def _ru_gov_aggregate(targets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked = len(targets)
    reachable_count = sum(1 for target in targets if as_bool(target.get("https_reachable")) is True)
    direct_route_count = sum(1 for target in targets if as_bool(target.get("direct_route_value")) is True)
    vpn_leak_count = sum(1 for target in targets if as_bool(target.get("route_via_vpn_value")) is True)
    degraded_count = sum(1 for target in targets if as_bool(target.get("https_degraded")) is True)
    failed_targets = _ru_gov_failed_targets(targets)
    route_leak_targets = _ru_gov_route_leak_targets(targets)
    success_rate = None if checked <= 0 else round(reachable_count / checked, 3)
    if checked <= 0:
        reachable_value = BOOL_UNKNOWN
        direct_route_value = BOOL_UNKNOWN
    else:
        reachable_value = bool_value(reachable_count == checked)
        direct_route_value = bool_value(direct_route_count == checked)
        if direct_route_count <= 0 and vpn_leak_count <= 0:
            direct_route_value = BOOL_UNKNOWN
    return {
        "ru_gov_checked_count": checked,
        "ru_gov_reachable_count": reachable_count,
        "ru_gov_success_rate": success_rate,
        "ru_gov_direct_route_count": direct_route_count,
        "ru_gov_vpn_leak_count": vpn_leak_count,
        "ru_gov_degraded_count": degraded_count,
        "ru_gov_failed_targets": failed_targets,
        "ru_gov_route_leak_targets": route_leak_targets,
        "ru_gov_reachable_value": reachable_value,
        "ru_gov_direct_route_value": direct_route_value,
    }


def classify_state(facts: Mapping[str, Any]) -> tuple[str, int, str, int]:
    if as_bool(facts.get("collector_error")) is True:
        return "ERROR", STATE_CODES["ERROR"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]

    checked = int(number(facts.get("transport_checked_count"), 0) or 0)
    success = int(number(facts.get("transport_success_count"), 0) or 0)
    if checked <= 0:
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]

    failed_targets = facts.get("failed_targets")
    has_failed_targets = (
        bool(failed_targets)
        if isinstance(failed_targets, Sequence) and not isinstance(failed_targets, str)
        else False
    )
    has_failed = has_failed_targets or success < checked
    flapping = facts.get("likely_failure_layer") == "mixed_flapping"
    if success == checked and not has_failed:
        return "OK", STATE_CODES["OK"], "normal", SEVERITY_CODES["normal"]
    if success <= 0:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
    if flapping or has_failed:
        return "WARN", STATE_CODES["WARN"], "degraded", SEVERITY_CODES["degraded"]
    return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]


def build_snapshot(facts: Mapping[str, Any], collected_at: str | None = None) -> dict[str, Any]:
    snapshot: dict[str, Any] = dict(facts)
    now = collected_at or str(snapshot.get("collected_at") or utc_now_iso())
    snapshot.setdefault("agent_id", "network.transport.ro")
    snapshot.setdefault("collected_at", now)
    snapshot.setdefault("schema_version", "1.0")
    snapshot.setdefault("collector_version", "0.2")
    snapshot["attempts"] = _safe_attempts(snapshot.get("attempts", 1))
    snapshot.setdefault("socks_proxy_configured", True)
    snapshot.setdefault("git_probe_configured", False)
    snapshot.setdefault("git_transport_state", "disabled")
    snapshot.setdefault("burst", {})

    bool_keys = (
        "direct_github_api_ok", "socks_github_api_ok", "direct_gstatic_ok", "socks_gstatic_ok",
        "direct_telegram_api_ok", "socks_telegram_api_ok",
        "socks_port_alive", "dns_github_ok", "dns_ssh_github_ok", "tcp_github_443_ok",
        "dns_telegram_ok", "tcp_ssh_github_443_ok", "tcp_telegram_443_ok",
        "socks_ssh_github_443_ok", "git_transport_ok",
    )
    for key in bool_keys:
        snapshot[f"{key}_value"] = bool_value(snapshot.get(key))

    checked_keys = (
        "dns_github_ok", "dns_ssh_github_ok", "tcp_github_443_ok", "tcp_ssh_github_443_ok",
        "dns_telegram_ok", "tcp_telegram_443_ok",
        "socks_port_alive", "socks_ssh_github_443_ok", "direct_github_api_ok", "socks_github_api_ok",
        "direct_gstatic_ok", "socks_gstatic_ok", "direct_telegram_api_ok", "socks_telegram_api_ok",
        "git_transport_ok",
    )
    snapshot.setdefault("transport_checked_count", sum(1 for key in checked_keys if as_bool(snapshot.get(key)) is not None))
    snapshot.setdefault("transport_success_count", sum(1 for key in checked_keys if as_bool(snapshot.get(key)) is True))
    snapshot.setdefault("failed_targets", _failed_targets(snapshot["burst"]) if isinstance(snapshot.get("burst"), Mapping) else [])
    snapshot.setdefault("likely_failure_layer", _likely_failure_layer(snapshot))
    snapshot.setdefault("transport_hint", "not_evaluated")
    snapshot.setdefault("freshness", "fresh")
    snapshot.setdefault("freshness_code", FRESHNESS_CODES["fresh"])
    snapshot.setdefault("operation_state", "completed")
    snapshot.setdefault("operation_state_code", OPERATION_STATE_CODES["completed"])

    state, state_code, severity, severity_code = classify_state(snapshot)
    snapshot.update({"state": state, "state_code": state_code, "severity": severity, "severity_code": severity_code})

    defaults = {
        "direct_github_api_ok": None, "socks_github_api_ok": None, "direct_gstatic_ok": None,
        "socks_gstatic_ok": None, "socks_port_alive": None, "dns_github_ok": None,
        "dns_ssh_github_ok": None, "tcp_github_443_ok": None, "tcp_ssh_github_443_ok": None,
        "socks_ssh_github_443_ok": None, "git_transport_ok": None, "direct_github_http_code": None,
        "socks_github_http_code": None, "direct_gstatic_http_code": None, "socks_gstatic_http_code": None,
        "direct_github_time_ms": None, "socks_github_time_ms": None, "direct_gstatic_time_ms": None,
        "socks_gstatic_time_ms": None,
        "direct_telegram_api_ok": None, "socks_telegram_api_ok": None,
        "dns_telegram_ok": None, "tcp_telegram_443_ok": None,
        "direct_telegram_http_code": None, "socks_telegram_http_code": None,
        "direct_telegram_time_ms": None, "socks_telegram_time_ms": None,
    }
    for key, value in defaults.items():
        snapshot.setdefault(key, value)
    for key in REQUIRED_OUTPUT_FIELDS:
        snapshot.setdefault(key, None)
    return {key: snapshot[key] for key in REQUIRED_OUTPUT_FIELDS}


def collect_network_transport(
    command_runner: CommandRunner,
    *,
    timeout: int | float = 7,
    socks_proxy: str = DEFAULT_SOCKS_PROXY,
    git_probe_url: str | None = None,
    attempts: int = 1,
    collected_at: str | None = None,
) -> dict[str, Any]:
    now = collected_at or utc_now_iso()
    attempt_count = _safe_attempts(attempts)
    facts: dict[str, Any] = {
        "agent_id": "network.transport.ro",
        "collected_at": now,
        "attempts": attempt_count,
        "socks_proxy_configured": bool(socks_proxy),
        "git_probe_configured": bool(git_probe_url),
        "git_transport_state": "disabled" if not git_probe_url else "configured",
        "transport_hint": "not_evaluated",
    }
    burst: dict[str, dict[str, Any]] = {}

    try:
        for host in DNS_TARGETS:
            key = _target_key("dns", host)
            outcomes, _results = _run_attempts(command_runner, _dns_command(host), timeout, attempt_count, _dns_ok)
            burst[key] = _stats(outcomes, now)
            facts[f"{key}_ok"] = _last_bool(outcomes)

        for host, port in TCP_TARGETS:
            key = _target_key("tcp", host, port)
            outcomes, _results = _run_attempts(command_runner, _tcp_command(host, port), timeout, attempt_count, _simple_ok)
            burst[key] = _stats(outcomes, now)
            facts[f"{key}_ok"] = _last_bool(outcomes)

        socks_host, socks_port = _socks_host_port(socks_proxy)
        outcomes, _results = _run_attempts(command_runner, _tcp_command(socks_host, socks_port), timeout, attempt_count, _simple_ok)
        burst["socks_port"] = _stats(outcomes, now)
        facts["socks_port_alive"] = _last_bool(outcomes)

        outcomes, _results = _run_attempts(
            command_runner,
            _socks_target_command(socks_proxy, "ssh.github.com", 443),
            timeout,
            attempt_count,
            _simple_ok,
        )
        burst["socks_ssh_github_443"] = _stats(outcomes, now)
        facts["socks_ssh_github_443_ok"] = _last_bool(outcomes)

        for key, url, proxy_mode in HTTPS_TARGETS:
            command = _curl_command(url, socks_proxy=socks_proxy if proxy_mode == "socks" else None)
            outcomes, http_code, elapsed_ms = _run_http_probe(command_runner, command, timeout, attempt_count)
            burst[key] = _stats(outcomes, now)
            facts[f"{key}_ok"] = _last_bool(outcomes)
            metric_prefix = key.replace("_api", "")
            facts[f"{metric_prefix}_http_code"] = http_code
            facts[f"{metric_prefix}_time_ms"] = elapsed_ms

        if git_probe_url:
            outcomes, _results = _run_attempts(command_runner, _git_command(git_probe_url), timeout, attempt_count, _simple_ok)
            burst["git_transport"] = _stats(outcomes, now)
            facts["git_transport_ok"] = _last_bool(outcomes)
            facts["git_transport_state"] = "ok" if facts["git_transport_ok"] is True else "failed"
        else:
            facts["git_transport_ok"] = None
            facts["git_transport_state"] = "disabled"

        ru_gov_targets: list[dict[str, Any]] = []
        for host in RU_GOV_TARGETS:
            target: dict[str, Any] = {"host": host}

            dns_outcomes, dns_results = _run_attempts(
                command_runner,
                _dns_command(host),
                timeout,
                attempt_count,
                _dns_ok,
            )
            target["dns_ok"] = _last_bool(dns_outcomes)
            resolved_ip = _first_resolved_ip(dns_results[-1].stdout if dns_results else "")

            tcp_outcomes, _tcp_results = _run_attempts(
                command_runner,
                _tcp_command(host, 443),
                timeout,
                attempt_count,
                _simple_ok,
            )
            target["tcp_443_ok"] = _last_bool(tcp_outcomes)

            https_outcomes, http_code, elapsed_ms, degraded = _run_ru_gov_http_probe(
                command_runner,
                _curl_command(f"https://{host}/"),
                timeout,
                attempt_count,
            )
            target["https_reachable"] = _last_bool(https_outcomes)
            target["https_degraded"] = degraded
            target["https_http_code"] = http_code
            target["https_time_ms"] = elapsed_ms

            if resolved_ip:
                route_result = command_runner(_route_command(resolved_ip), timeout)
                route_values = _parse_route_output(route_result.stdout if route_result.returncode == 0 else route_result.stderr)
                target.update(route_values)
            else:
                target.update(
                    {
                        "route_dev": None,
                        "route_src_present_value": BOOL_UNKNOWN,
                        "route_via_vpn_value": BOOL_UNKNOWN,
                        "direct_route_value": BOOL_UNKNOWN,
                        "route_raw": "",
                    }
                )

            ru_gov_targets.append(target)

        facts["ru_gov_targets"] = ru_gov_targets
        facts.update(_ru_gov_aggregate(ru_gov_targets))

        split_checked_keys = (
            "dns_github_ok", "dns_ssh_github_ok", "tcp_github_443_ok", "tcp_ssh_github_443_ok",
            "dns_telegram_ok", "tcp_telegram_443_ok",
            "socks_port_alive", "socks_ssh_github_443_ok", "direct_github_api_ok", "socks_github_api_ok",
            "direct_gstatic_ok", "socks_gstatic_ok", "direct_telegram_api_ok", "socks_telegram_api_ok",
            "git_transport_ok",
        )
        facts["transport_checked_count"] = sum(
            1 for key in split_checked_keys if as_bool(facts.get(key)) is not None
        )
        facts["transport_success_count"] = sum(
            1 for key in split_checked_keys if as_bool(facts.get(key)) is True
        )
        facts["reachability_split_hint"] = _reachability_split_hint(facts)
        facts["route_policy_hint"] = _route_policy_hint(facts)

        facts["burst"] = burst
        facts["failed_targets"] = _failed_targets(burst)
        facts["likely_failure_layer"] = _likely_failure_layer(facts)
        facts["transport_hint"] = "transport_available" if any(
            as_bool(facts.get(key)) is True
            for key in (
                "direct_github_api_ok", "socks_github_api_ok", "direct_gstatic_ok", "socks_gstatic_ok",
                "direct_telegram_api_ok", "socks_telegram_api_ok",
                "tcp_github_443_ok", "tcp_ssh_github_443_ok", "socks_ssh_github_443_ok",
            )
        ) else "transport_unavailable"
    except Exception as exc:
        facts["collector_error"] = True
        facts["transport_hint"] = f"collector_error:{type(exc).__name__}"
        snapshot = build_snapshot(facts, collected_at=now)
        snapshot["operation_state"] = "failed"
        snapshot["operation_state_code"] = OPERATION_STATE_CODES["failed"]
        return snapshot

    return build_snapshot(facts, collected_at=now)
