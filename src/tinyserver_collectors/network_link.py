"""Read-only network.link.ro snapshot and live fact helpers.

The pure functions build and classify Agent RO snapshots. The live helper keeps
host reads behind an injectable command runner and an injectable sysfs root so
unit tests never depend on the real network.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

BOOL_TRUE = 1
BOOL_FALSE = 0
BOOL_UNKNOWN = -1

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}

DNS_DOMAINS = {
    "github": "github.com",
    "google": "google.com",
    "telegram": "api.telegram.org",
}

REQUIRED_OUTPUT_FIELDS = (
    "agent_id", "collected_at", "interface", "operstate", "carrier", "carrier_value",
    "speed_mbps", "duplex", "rx_errors", "tx_errors", "rx_dropped", "tx_dropped",
    "gateway_ip_present", "gateway_ip_present_value", "gateway_ping_ok",
    "gateway_ping_ok_value", "gateway_ping_ms_min", "gateway_ping_ms_avg",
    "gateway_ping_ms_max", "gateway_ping_loss_percent", "dns_ok", "dns_ok_value",
    "dns_checked_domains_count", "dns_success_count", "dns_github_ok_value",
    "dns_google_ok_value", "dns_telegram_ok_value", "vpn_interface_present",
    "vpn_interface_present_value", "vpn_dns_present", "vpn_dns_present_value",
    "wan_hint", "vpn_hint", "state", "state_code", "severity", "severity_code",
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
        if normalized in {"1", "true", "yes", "y", "up", "present", "ok"}:
            return BOOL_TRUE
        if normalized in {"0", "false", "no", "n", "down", "absent", "bad"}:
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


def integer(value: Any, default: int = 0) -> int:
    parsed = number(value)
    return default if parsed is None else int(parsed)


def classify_state(facts: Mapping[str, Any]) -> tuple[str, int, str, int]:
    if as_bool(facts.get("collector_error")) is True:
        return "ERROR", STATE_CODES["ERROR"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]
    if not facts.get("interface"):
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]

    operstate = str(facts.get("operstate") or "").strip().lower()
    carrier = as_bool(facts.get("carrier"))
    gateway_ip_present = as_bool(facts.get("gateway_ip_present"))
    gateway_loss = number(facts.get("gateway_ping_loss_percent"))
    gateway_ping_ok = as_bool(facts.get("gateway_ping_ok"))
    dns_success_count = integer(facts.get("dns_success_count"), 0)
    gateway_ping_ms_max = number(facts.get("gateway_ping_ms_max"), 0.0)
    speed_mbps = number(facts.get("speed_mbps"))
    expected_speed_mbps = number(facts.get("expected_speed_mbps"))
    rx_errors_increased = as_bool(facts.get("rx_errors_increased"))
    tx_errors_increased = as_bool(facts.get("tx_errors_increased"))

    if carrier is None or not operstate or gateway_ip_present is None or gateway_loss is None:
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]
    if carrier is False or operstate == "down" or gateway_ip_present is False:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
    if gateway_loss > 5 and dns_success_count == 0:
        severity = "critical" if gateway_loss > 20 else "degraded"
        return "BAD", STATE_CODES["BAD"], severity, SEVERITY_CODES[severity]
    if gateway_ping_ok is False and dns_success_count == 0:
        return "BAD", STATE_CODES["BAD"], "degraded", SEVERITY_CODES["degraded"]
    if gateway_ping_ms_max is not None and gateway_ping_ms_max >= 1000 and dns_success_count == 0:
        return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]

    warn_conditions = [
        dns_success_count == 0,
        gateway_loss > 20,
        5 < gateway_loss <= 20,
        0 < gateway_loss <= 5,
        gateway_ping_ok is False,
        gateway_ping_ms_max is not None and 100 <= gateway_ping_ms_max < 1000,
        gateway_ping_ms_max is not None and gateway_ping_ms_max >= 1000,
        expected_speed_mbps is not None and speed_mbps is not None and 0 < speed_mbps < expected_speed_mbps,
        (rx_errors_increased is True or tx_errors_increased is True) and gateway_ping_ok is True and dns_success_count > 0,
    ]
    if any(warn_conditions):
        severity = "degraded" if gateway_loss > 20 or gateway_ping_ok is False else "warning"
        return "WARN", STATE_CODES["WARN"], severity, SEVERITY_CODES[severity]
    if carrier is True and operstate == "up" and gateway_loss == 0 and gateway_ping_ok is True and dns_success_count >= 1:
        return "OK", STATE_CODES["OK"], "normal", SEVERITY_CODES["normal"]
    return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]


def build_snapshot(facts: Mapping[str, Any], collected_at: str | None = None) -> dict[str, Any]:
    snapshot: dict[str, Any] = dict(facts)
    snapshot.setdefault("agent_id", "network.link.ro")
    snapshot.setdefault("collected_at", collected_at or utc_now_iso())

    for key in ("carrier", "gateway_ip_present", "gateway_ping_ok", "dns_ok", "vpn_interface_present", "vpn_dns_present"):
        snapshot[f"{key}_value"] = bool_value(snapshot.get(key))

    dns_values = {
        "dns_github_ok_value": bool_value(snapshot.get("dns_github_ok")),
        "dns_google_ok_value": bool_value(snapshot.get("dns_google_ok")),
        "dns_telegram_ok_value": bool_value(snapshot.get("dns_telegram_ok")),
    }
    snapshot.update(dns_values)
    snapshot.setdefault("dns_checked_domains_count", sum(1 for value in dns_values.values() if value != BOOL_UNKNOWN))
    snapshot.setdefault("dns_success_count", sum(1 for value in dns_values.values() if value == BOOL_TRUE))
    if "dns_ok" not in snapshot:
        snapshot["dns_ok"] = snapshot["dns_success_count"] >= 1
        snapshot["dns_ok_value"] = bool_value(snapshot["dns_ok"])

    snapshot.setdefault("wan_hint", "not_evaluated")
    snapshot.setdefault("vpn_hint", "not_evaluated")
    snapshot.setdefault("freshness", "fresh")
    snapshot.setdefault("freshness_code", FRESHNESS_CODES["fresh"])
    snapshot.setdefault("operation_state", "completed")
    snapshot.setdefault("operation_state_code", OPERATION_STATE_CODES["completed"])

    state, state_code, severity, severity_code = classify_state(snapshot)
    snapshot.update({"state": state, "state_code": state_code, "severity": severity, "severity_code": severity_code})

    defaults = {
        "interface": None, "operstate": "unknown", "carrier": None, "speed_mbps": None,
        "duplex": "unknown", "rx_errors": 0, "tx_errors": 0, "rx_dropped": 0,
        "tx_dropped": 0, "gateway_ip_present": None, "gateway_ping_ok": None,
        "gateway_ping_ms_min": None, "gateway_ping_ms_avg": None,
        "gateway_ping_ms_max": None, "gateway_ping_loss_percent": None,
        "dns_ok": None, "dns_checked_domains_count": 0, "dns_success_count": 0,
        "vpn_interface_present": None, "vpn_dns_present": None,
    }
    for key, value in defaults.items():
        snapshot.setdefault(key, value)
    for key in REQUIRED_OUTPUT_FIELDS:
        snapshot.setdefault(key, None)
    return {key: snapshot[key] for key in REQUIRED_OUTPUT_FIELDS}


def parse_default_route(output: str) -> tuple[str | None, str | None]:
    for line in output.splitlines():
        parts = line.split()
        if not parts or parts[0] != "default":
            continue
        iface = None
        gateway = None
        for index, part in enumerate(parts):
            if part == "dev" and index + 1 < len(parts):
                iface = parts[index + 1]
            if part == "via" and index + 1 < len(parts):
                gateway = parts[index + 1]
        return iface, gateway
    return None, None


def parse_ping_summary(output: str) -> dict[str, float | bool | None]:
    result: dict[str, float | bool | None] = {
        "gateway_ping_ok": None,
        "gateway_ping_loss_percent": None,
        "gateway_ping_ms_min": None,
        "gateway_ping_ms_avg": None,
        "gateway_ping_ms_max": None,
    }
    loss_match = re.search(r"([0-9]+(?:\.[0-9]+)?)%\s*packet loss", output)
    if loss_match:
        loss_percent = float(loss_match.group(1))
        result["gateway_ping_loss_percent"] = loss_percent
        result["gateway_ping_ok"] = loss_percent < 100

    rtt_match = re.search(r"=\s*([0-9.]+)/([0-9.]+)/([0-9.]+)/", output)
    if rtt_match:
        result["gateway_ping_ms_min"] = float(rtt_match.group(1))
        result["gateway_ping_ms_avg"] = float(rtt_match.group(2))
        result["gateway_ping_ms_max"] = float(rtt_match.group(3))
    return result


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def read_int(path: Path) -> int | None:
    text = read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def interface_names(sysfs_root: Path) -> list[str]:
    try:
        return sorted(path.name for path in sysfs_root.iterdir())
    except OSError:
        return []


def collect_network_link(
    command_runner: CommandRunner,
    sysfs_root: str | Path = "/sys/class/net",
    timeout: int | float = 5,
    collected_at: str | None = None,
) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "agent_id": "network.link.ro",
        "wan_hint": "not_evaluated",
        "vpn_hint": "not_evaluated",
    }
    root = Path(sysfs_root)

    try:
        route = command_runner(("ip", "route", "show", "default"), timeout)
        iface, gateway = parse_default_route(route.stdout)
        facts["interface"] = iface
        facts["gateway_ip_present"] = gateway is not None

        if not iface:
            return build_snapshot(facts, collected_at=collected_at)

        iface_path = root / iface
        stats_path = iface_path / "statistics"
        facts["operstate"] = read_text(iface_path / "operstate") or "unknown"
        facts["carrier"] = read_text(iface_path / "carrier")
        facts["speed_mbps"] = read_int(iface_path / "speed")
        facts["duplex"] = read_text(iface_path / "duplex") or "unknown"
        for key in ("rx_errors", "tx_errors", "rx_dropped", "tx_dropped"):
            facts[key] = read_int(stats_path / key) or 0

        if gateway:
            ping = command_runner(("ping", "-c", "5", "-W", "1", gateway), timeout)
            facts.update(parse_ping_summary(ping.stdout))
            if facts.get("gateway_ping_ok") is None:
                facts["gateway_ping_ok"] = ping.returncode == 0
            if facts.get("gateway_ping_loss_percent") is None:
                facts["gateway_ping_loss_percent"] = 0.0 if ping.returncode == 0 else 100.0
        else:
            facts["gateway_ping_ok"] = False
            facts["gateway_ping_loss_percent"] = 100.0

        dns_success = 0
        dns_checked = 0
        for label, domain in DNS_DOMAINS.items():
            dns_checked += 1
            result = command_runner(("getent", "hosts", domain), timeout)
            ok = result.returncode == 0 and bool(result.stdout.strip())
            facts[f"dns_{label}_ok"] = ok
            if ok:
                dns_success += 1
        facts["dns_checked_domains_count"] = dns_checked
        facts["dns_success_count"] = dns_success
        facts["dns_ok"] = dns_success >= 1

        names = interface_names(root)
        facts["vpn_interface_present"] = any(name.startswith(("tun", "tap", "wg")) for name in names)
        resolver = command_runner(("resolvectl", "status"), timeout)
        facts["vpn_dns_present"] = "tun" in resolver.stdout and "DNS Servers:" in resolver.stdout
        facts["wan_hint"] = "dns_reachable" if facts["dns_ok"] else "dns_unreachable"
        facts["vpn_hint"] = "vpn_interface_present" if facts["vpn_interface_present"] else "no_vpn_interface_detected"
    except Exception as exc:
        facts["collector_error"] = True
        facts["wan_hint"] = f"collector_error:{type(exc).__name__}"
        facts["vpn_hint"] = "collector_error"
        snapshot = build_snapshot(facts, collected_at=collected_at)
        snapshot["operation_state"] = "failed"
        snapshot["operation_state_code"] = OPERATION_STATE_CODES["failed"]
        return snapshot

    return build_snapshot(facts, collected_at=collected_at)
