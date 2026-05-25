"""Framework-compatible snapshot wrapper for network.link.ro."""

from __future__ import annotations

import json
from typing import Any

from tinyserver_collectors.network_link_cli import collect_with_default_runner

TTL_SEC = 300


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
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
        "checks": {},
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
