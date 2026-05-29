from __future__ import annotations

from tinyserver_collectors.network_transport_framework import to_framework_snapshot


def test_to_framework_snapshot_adds_required_contract_fields() -> None:
    snapshot = to_framework_snapshot(
        {
            "agent_id": "network.transport.ro",
            "collected_at": "2026-05-29T12:00:00+00:00",
            "state": "OK",
            "severity_code": 0,
            "direct_github_api_ok_value": 1,
            "socks_github_api_ok_value": 0,
            "direct_gstatic_ok_value": 1,
            "socks_gstatic_ok_value": 0,
            "socks_port_alive_value": 1,
            "direct_github_http_code": 200,
            "socks_github_http_code": 0,
            "direct_gstatic_http_code": 204,
            "socks_gstatic_http_code": 0,
            "direct_github_time_ms": 101.0,
            "socks_github_time_ms": 0.0,
            "direct_gstatic_time_ms": 55.5,
            "socks_gstatic_time_ms": 0.0,
            "transport_success_count": 2,
            "transport_checked_count": 4,
            "freshness_code": 0,
            "operation_state_code": 6,
        }
    )

    assert snapshot["schema_version"] == "1.0"
    assert snapshot["agent_id"] == "network.transport.ro"
    assert snapshot["product"] == "Tiny Agent Framework"
    assert snapshot["domain"] == "network"
    assert snapshot["display_name"] == "Network Transport RO"
    assert snapshot["ttl_sec"] == 300
    assert snapshot["state"] == "OK"
    assert snapshot["severity"] == 0
    assert snapshot["capabilities"] == {"read_only": True, "actions": []}
    assert sorted(snapshot["checks"]) == ["github_api", "gstatic", "socks_proxy", "transport_path"]
    assert snapshot["metrics"]["direct_github_api_ok_value"] == 1
    assert snapshot["metrics"]["direct_github_time_ms"] == 101.0
    assert snapshot["metrics"]["transport_success_count"] == 2


def test_to_framework_snapshot_marks_partial_transport_warn() -> None:
    snapshot = to_framework_snapshot(
        {
            "agent_id": "network.transport.ro",
            "collected_at": "2026-05-29T12:00:00+00:00",
            "state": "WARN",
            "severity_code": 3,
            "direct_github_api_ok_value": 1,
            "socks_github_api_ok_value": 0,
            "direct_gstatic_ok_value": 0,
            "socks_gstatic_ok_value": 0,
            "socks_port_alive_value": 0,
            "direct_github_http_code": 200,
            "socks_github_http_code": 0,
            "direct_gstatic_http_code": 503,
            "socks_gstatic_http_code": 0,
            "transport_success_count": 1,
            "transport_checked_count": 4,
        }
    )

    assert snapshot["state"] == "WARN"
    assert snapshot["severity"] == 3
    assert snapshot["checks"]["github_api"]["state"] == "OK"
    assert snapshot["checks"]["gstatic"]["state"] == "BAD"
    assert snapshot["checks"]["socks_proxy"]["state"] == "WARN"
    assert snapshot["checks"]["transport_path"]["state"] == "WARN"


def test_to_framework_snapshot_clamps_unknown_state_and_severity() -> None:
    snapshot = to_framework_snapshot(
        {
            "collected_at": "2026-05-29T12:00:00+00:00",
            "state": "BROKEN",
            "severity_code": 5,
            "transport_success_count": 0,
            "transport_checked_count": 0,
        }
    )

    assert snapshot["state"] == "UNKNOWN"
    assert snapshot["severity"] == 4
    assert all(check["severity"] <= 4 for check in snapshot["checks"].values())


def test_checks_have_contract_evidence() -> None:
    snapshot = to_framework_snapshot(
        {
            "collected_at": "2026-05-29T12:00:00+00:00",
            "state": "BAD",
            "severity_code": 4,
            "direct_github_api_ok_value": 0,
            "socks_github_api_ok_value": 0,
            "direct_gstatic_ok_value": 0,
            "socks_gstatic_ok_value": 0,
            "socks_port_alive_value": 0,
            "transport_success_count": 0,
            "transport_checked_count": 4,
        }
    )

    for check in snapshot["checks"].values():
        assert {"state", "severity", "confidence", "summary", "rule_id", "ruleset_version", "evidence"} <= set(check)
        assert check["ruleset_version"] == "1.0"
        assert check["evidence"]["source"] == "curl"
        assert check["evidence"]["source_type"] == "command"
        assert check["evidence"]["command_class"] == "read_only"
        assert check["evidence"]["collected_at"] == "2026-05-29T12:00:00+00:00"
