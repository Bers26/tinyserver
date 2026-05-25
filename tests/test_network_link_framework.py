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
            "speed_mbps": 100,
            "gateway_ping_loss_percent": 0.0,
            "dns_success_count": 3,
            "carrier_value": 1,
            "gateway_ping_ok_value": 1,
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
