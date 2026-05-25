from __future__ import annotations

from tinyserver_collectors.network_link_framework import to_framework_snapshot


def test_to_framework_snapshot_adds_required_contract_fields() -> None:
    snapshot = to_framework_snapshot(
        {
            "agent_id": "network.link.ro",
            "collected_at": "2026-05-25T09:28:07+00:00",
            "state": "OK",
            "severity_code": 0,
            "interface": "enp6s0",
            "operstate": "up",
            "speed_mbps": 100,
            "duplex": "full",
            "gateway_ip_present_value": 1,
            "gateway_ping_loss_percent": 0.0,
            "gateway_ping_ok_value": 1,
            "gateway_ping_ms_avg": 1.2,
            "gateway_ping_ms_max": 2.0,
            "dns_checked_domains_count": 3,
            "dns_success_count": 3,
            "dns_github_ok_value": 1,
            "dns_google_ok_value": 1,
            "dns_telegram_ok_value": 1,
            "carrier_value": 1,
            "vpn_interface_present_value": 1,
            "vpn_dns_present_value": 1,
            "rx_errors": 0,
            "tx_errors": 0,
            "rx_dropped": 0,
            "tx_dropped": 0,
        }
    )

    assert snapshot["schema_version"] == "1.0"
    assert snapshot["agent_id"] == "network.link.ro"
    assert snapshot["product"] == "Tiny Agent Framework"
    assert snapshot["domain"] == "network"
    assert snapshot["display_name"] == "Network Link RO"
    assert snapshot["ttl_sec"] == 300
    assert snapshot["state"] == "OK"
    assert snapshot["severity"] == 0
    assert snapshot["capabilities"] == {"read_only": True, "actions": []}
    assert isinstance(snapshot["checks"], dict)
    assert isinstance(snapshot["metrics"], dict)
    assert snapshot["metrics"]["carrier_value"] == 1


def test_to_framework_snapshot_adds_network_checks_dictionary() -> None:
    snapshot = to_framework_snapshot(
        {
            "agent_id": "network.link.ro",
            "collected_at": "2026-05-25T09:28:07+00:00",
            "state": "OK",
            "severity_code": 0,
            "interface": "enp6s0",
            "operstate": "up",
            "carrier_value": 1,
            "speed_mbps": 100,
            "duplex": "full",
            "gateway_ip_present_value": 1,
            "gateway_ping_ok_value": 1,
            "gateway_ping_loss_percent": 0.0,
            "gateway_ping_ms_avg": 1.2,
            "gateway_ping_ms_max": 2.0,
            "dns_checked_domains_count": 3,
            "dns_success_count": 3,
            "dns_github_ok_value": 1,
            "dns_google_ok_value": 1,
            "dns_telegram_ok_value": 1,
            "vpn_interface_present_value": 1,
            "vpn_dns_present_value": 1,
            "vpn_hint": "vpn_interface_present",
            "rx_errors": 0,
            "tx_errors": 0,
            "rx_dropped": 0,
            "tx_dropped": 0,
        }
    )

    checks = snapshot["checks"]
    assert sorted(checks) == ["dns", "gateway_ping", "interface_counters", "link", "vpn_hint"]
    assert checks["link"]["state"] == "OK"
    assert checks["gateway_ping"]["state"] == "OK"
    assert checks["dns"]["state"] == "OK"
    assert checks["vpn_hint"]["rule_id"] == "network.vpn_hint"
    assert checks["interface_counters"]["evidence"]["command_class"] == "local_file_read"
    for check in checks.values():
        assert {"state", "severity", "confidence", "summary", "rule_id", "ruleset_version", "evidence"} <= set(check)
        assert check["ruleset_version"] == "1.0"
        assert check["evidence"]["collected_at"] == "2026-05-25T09:28:07+00:00"


def test_to_framework_snapshot_marks_gateway_and_dns_checks_degraded() -> None:
    snapshot = to_framework_snapshot(
        {
            "agent_id": "network.link.ro",
            "collected_at": "2026-05-25T09:28:07+00:00",
            "state": "WARN",
            "severity_code": 3,
            "interface": "enp6s0",
            "operstate": "up",
            "carrier_value": 1,
            "speed_mbps": 100,
            "duplex": "full",
            "gateway_ip_present_value": 1,
            "gateway_ping_ok_value": 0,
            "gateway_ping_loss_percent": 100.0,
            "gateway_ping_ms_avg": None,
            "gateway_ping_ms_max": None,
            "dns_checked_domains_count": 3,
            "dns_success_count": 1,
            "dns_github_ok_value": 1,
            "dns_google_ok_value": 0,
            "dns_telegram_ok_value": 0,
            "vpn_interface_present_value": 0,
            "vpn_dns_present_value": 0,
            "rx_errors": 0,
            "tx_errors": 4,
            "rx_dropped": 0,
            "tx_dropped": 0,
        }
    )

    assert snapshot["checks"]["gateway_ping"]["state"] == "WARN"
    assert snapshot["checks"]["gateway_ping"]["severity"] == 3
    assert snapshot["checks"]["dns"]["state"] == "WARN"
    assert snapshot["checks"]["vpn_hint"]["state"] == "WARN"
    assert snapshot["checks"]["interface_counters"]["state"] == "OK"


def test_to_framework_snapshot_clamps_unknown_state() -> None:
    snapshot = to_framework_snapshot(
        {
            "collected_at": "2026-05-25T09:28:07+00:00",
            "state": "BROKEN",
            "severity_code": 5,
        }
    )

    assert snapshot["state"] == "UNKNOWN"
    assert snapshot["severity"] == 5
    assert isinstance(snapshot["checks"], dict)


def test_vpn_hint_source_type_is_contract_valid() -> None:
    from tinyserver_collectors.network_link_framework import to_framework_snapshot

    snapshot = to_framework_snapshot({
        "collected_at": "2026-05-25T21:45:00+00:00",
        "state": "OK",
        "severity_code": 0,
        "vpn_interface_present_value": 1,
        "vpn_dns_present_value": 1,
        "vpn_hint": "vpn_interface_present",
    })

    assert snapshot["checks"]["vpn_hint"]["evidence"]["source_type"] == "derived"
