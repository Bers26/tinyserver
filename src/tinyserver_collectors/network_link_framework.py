"""Framework-compatible snapshot wrapper for network.link.ro."""

from __future__ import annotations

import json
from typing import Any

from tinyserver_collectors.network_link_cli import collect_with_default_runner

TTL_SEC = 300
RULESET_VERSION = "1.0"


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _metric_subset(raw: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "carrier_value",
        "speed_mbps",
        "rx_errors",
        "tx_errors",
        "rx_dropped",
        "tx_dropped",
        "gateway_ip_present_value",
        "gateway_ping_ok_value",
        "gateway_ping_ms_min",
        "gateway_ping_ms_avg",
        "gateway_ping_ms_max",
        "gateway_ping_loss_percent",
        "dns_ok_value",
        "dns_checked_domains_count",
        "dns_success_count",
        "dns_github_ok_value",
        "dns_google_ok_value",
        "dns_telegram_ok_value",
        "vpn_interface_present_value",
        "vpn_dns_present_value",
        "freshness_code",
        "operation_state_code",
    ]
    return {key: raw.get(key) for key in keys if key in raw}


def _check(
    *,
    state: str,
    severity: int,
    confidence: str,
    summary: str,
    rule_id: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "state": state,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
        "rule_id": rule_id,
        "ruleset_version": RULESET_VERSION,
        "evidence": evidence,
    }


def _evidence(raw: dict[str, Any], *, source: str, source_type: str, command_class: str, observed_value: str) -> dict[str, Any]:
    return {
        "source": source,
        "source_type": source_type,
        "command_class": command_class,
        "observed_value": observed_value,
        "collected_at": str(raw.get("collected_at") or ""),
    }


def _link_check(raw: dict[str, Any]) -> dict[str, Any]:
    iface = raw.get("interface") or "unknown"
    operstate = str(raw.get("operstate") or "unknown")
    carrier = _int_value(raw.get("carrier_value"), -1)
    speed = raw.get("speed_mbps")
    duplex = raw.get("duplex") or "unknown"

    if not raw.get("interface") or carrier == -1:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = f"Link state unknown: iface={iface}, operstate={operstate}, carrier={carrier}."
    elif carrier == 0 or operstate == "down":
        state, severity, confidence = "BAD", 4, "high"
        summary = f"Link down: iface={iface}, operstate={operstate}, carrier={carrier}."
    else:
        state, severity, confidence = "OK", 0, "high"
        summary = f"Link up: iface={iface}, speed={speed}Mb/s, duplex={duplex}."

    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.link.carrier",
        evidence=_evidence(
            raw,
            source="/sys/class/net",
            source_type="file",
            command_class="local_file_read",
            observed_value=f"iface={iface} operstate={operstate} carrier={carrier} speed_mbps={speed} duplex={duplex}",
        ),
    )


def _gateway_ping_check(raw: dict[str, Any]) -> dict[str, Any]:
    gateway_present = _int_value(raw.get("gateway_ip_present_value"), -1)
    ping_ok = _int_value(raw.get("gateway_ping_ok_value"), -1)
    loss = _float_value(raw.get("gateway_ping_loss_percent"))
    avg_ms = _float_value(raw.get("gateway_ping_ms_avg"))
    max_ms = _float_value(raw.get("gateway_ping_ms_max"))

    if gateway_present == 0:
        state, severity, confidence = "BAD", 4, "high"
        summary = "Gateway missing from default route."
    elif gateway_present == -1 or loss is None or ping_ok == -1:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = "Gateway ping state unknown."
    elif loss == 0 and ping_ok == 1:
        state, severity, confidence = "OK", 0, "high"
        summary = f"Gateway ping OK: loss={loss}%, avg={avg_ms} ms, max={max_ms} ms."
    elif loss > 20 or ping_ok == 0:
        state, severity, confidence = "WARN", 3, "high"
        summary = f"Gateway ping degraded: loss={loss}%, avg={avg_ms} ms, max={max_ms} ms."
    else:
        state, severity, confidence = "WARN", 2, "high"
        summary = f"Gateway ping has minor loss/latency: loss={loss}%, avg={avg_ms} ms, max={max_ms} ms."

    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.gateway_ping",
        evidence=_evidence(
            raw,
            source="ping gateway",
            source_type="command",
            command_class="read_only",
            observed_value=f"gateway_present={gateway_present} ping_ok={ping_ok} loss_percent={loss} avg_ms={avg_ms} max_ms={max_ms}",
        ),
    )


def _dns_check(raw: dict[str, Any]) -> dict[str, Any]:
    checked = _int_value(raw.get("dns_checked_domains_count"), 0)
    success = _int_value(raw.get("dns_success_count"), 0)

    if checked <= 0:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = "DNS checks were not executed."
    elif success == checked:
        state, severity, confidence = "OK", 0, "high"
        summary = f"DNS OK: {success}/{checked} targets resolved."
    elif success > 0:
        state, severity, confidence = "WARN", 2, "high"
        summary = f"DNS degraded: {success}/{checked} targets resolved."
    else:
        state, severity, confidence = "BAD", 4, "high"
        summary = f"DNS failed: {success}/{checked} targets resolved."

    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.dns_resolution",
        evidence=_evidence(
            raw,
            source="getent hosts",
            source_type="command",
            command_class="read_only",
            observed_value=(
                f"success={success} checked={checked} "
                f"github={raw.get('dns_github_ok_value')} google={raw.get('dns_google_ok_value')} "
                f"telegram={raw.get('dns_telegram_ok_value')}"
            ),
        ),
    )


def _vpn_hint_check(raw: dict[str, Any]) -> dict[str, Any]:
    vpn_iface = _int_value(raw.get("vpn_interface_present_value"), -1)
    vpn_dns = _int_value(raw.get("vpn_dns_present_value"), -1)
    hint = raw.get("vpn_hint") or "unknown"

    if vpn_iface == 1 and vpn_dns == 1:
        state, severity, confidence = "OK", 0, "medium"
        summary = "VPN interface and VPN DNS hint are present."
    elif vpn_iface == 1:
        state, severity, confidence = "WARN", 2, "medium"
        summary = "VPN interface is present, VPN DNS hint is absent."
    elif vpn_iface == 0:
        state, severity, confidence = "WARN", 2, "medium"
        summary = "VPN interface hint is absent."
    else:
        state, severity, confidence = "UNKNOWN", 5, "low"
        summary = "VPN hint state unknown."

    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.vpn_hint",
        evidence=_evidence(
            raw,
            source="interfaces/resolvectl",
            source_type="derived",
            command_class="read_only",
            observed_value=f"vpn_interface_present={vpn_iface} vpn_dns_present={vpn_dns} vpn_hint={hint}",
        ),
    )


def _interface_counters_check(raw: dict[str, Any]) -> dict[str, Any]:
    rx_errors = _int_value(raw.get("rx_errors"), 0)
    tx_errors = _int_value(raw.get("tx_errors"), 0)
    rx_dropped = _int_value(raw.get("rx_dropped"), 0)
    tx_dropped = _int_value(raw.get("tx_dropped"), 0)
    total = rx_errors + tx_errors + rx_dropped + tx_dropped

    if total == 0:
        state, severity, confidence = "OK", 0, "medium"
        summary = "Interface counters show no accumulated errors or drops."
    else:
        state, severity, confidence = "OK", 0, "medium"
        summary = f"Interface counters observed: rx_errors={rx_errors}, tx_errors={tx_errors}, rx_dropped={rx_dropped}, tx_dropped={tx_dropped}."

    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.interface_counters",
        evidence=_evidence(
            raw,
            source="/sys/class/net/*/statistics",
            source_type="file",
            command_class="local_file_read",
            observed_value=f"rx_errors={rx_errors} tx_errors={tx_errors} rx_dropped={rx_dropped} tx_dropped={tx_dropped}",
        ),
    )


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "link": _link_check(raw),
        "gateway_ping": _gateway_ping_check(raw),
        "dns": _dns_check(raw),
        "vpn_hint": _vpn_hint_check(raw),
        "interface_counters": _interface_counters_check(raw),
    }


def _summary(raw: dict[str, Any]) -> str:
    state = str(raw.get("state") or "UNKNOWN").upper()
    iface = raw.get("interface") or "unknown"
    loss = raw.get("gateway_ping_loss_percent")
    dns_success = raw.get("dns_success_count")
    speed = raw.get("speed_mbps")
    return f"Network link {state}: iface={iface}, speed={speed}Mb/s, loss={loss}%, dns_success={dns_success}."


def to_framework_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN"}:
        state = "UNKNOWN"
    severity = _int_value(raw.get("severity_code"), 5)
    return {
        "schema_version": "1.0",
        "agent_id": "network.link.ro",
        "product": "Tiny Agent Framework",
        "domain": "network",
        "display_name": "Network Link RO",
        "version": "0.1",
        "collected_at": str(raw.get("collected_at") or ""),
        "ttl_sec": TTL_SEC,
        "state": state,
        "severity": severity,
        "summary": _summary(raw),
        "checks": _checks(raw),
        "metrics": _metric_subset(raw),
        "links": [],
        "capabilities": {"read_only": True, "actions": []},
    }


def collect(output_root: object | None = None) -> dict[str, Any]:
    raw = collect_with_default_runner()
    return to_framework_snapshot(raw)


def main() -> int:
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
