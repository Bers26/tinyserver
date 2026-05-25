from __future__ import annotations

import json
from pathlib import Path

from tinyserver_collectors.network_link import (
    BOOL_FALSE,
    BOOL_TRUE,
    BOOL_UNKNOWN,
    REQUIRED_OUTPUT_FIELDS,
    bool_value,
    build_snapshot,
    classify_state,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "network_link"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_bool_value_projection() -> None:
    assert bool_value(True) == BOOL_TRUE
    assert bool_value(False) == BOOL_FALSE
    assert bool_value(None) == BOOL_UNKNOWN
    assert bool_value("up") == BOOL_TRUE
    assert bool_value("down") == BOOL_FALSE
    assert bool_value("unknown") == BOOL_UNKNOWN


def test_required_output_fields_are_complete() -> None:
    fixture = load_fixture("ok.json")
    snapshot = build_snapshot(fixture["facts"], collected_at="2026-05-24T23:17:44+00:00")
    assert tuple(snapshot.keys()) == REQUIRED_OUTPUT_FIELDS
    assert set(snapshot) == set(REQUIRED_OUTPUT_FIELDS)


def test_ok_fixture_classification() -> None:
    fixture = load_fixture("ok.json")
    snapshot = build_snapshot(fixture["facts"], collected_at="2026-05-24T23:17:44+00:00")
    assert snapshot["state"] == fixture["expected"]["state"]
    assert snapshot["state_code"] == fixture["expected"]["state_code"]
    assert snapshot["severity"] == fixture["expected"]["severity"]
    assert snapshot["severity_code"] == fixture["expected"]["severity_code"]
    assert snapshot["carrier_value"] == BOOL_TRUE
    assert snapshot["dns_ok_value"] == BOOL_TRUE
    assert snapshot["dns_success_count"] == 2


def test_warn_loss_fixture_classification() -> None:
    fixture = load_fixture("warn_loss.json")
    snapshot = build_snapshot(fixture["facts"], collected_at="2026-05-24T23:17:44+00:00")
    assert snapshot["state"] == "WARN"
    assert snapshot["state_code"] == 1
    assert snapshot["severity"] == "warning"
    assert snapshot["severity_code"] == 2
    assert snapshot["gateway_ping_loss_percent"] == 4.0


def test_bad_loss_fixture_classification() -> None:
    fixture = load_fixture("bad_loss.json")
    snapshot = build_snapshot(fixture["facts"], collected_at="2026-05-24T23:17:44+00:00")
    assert snapshot["state"] == "BAD"
    assert snapshot["state_code"] == 2
    assert snapshot["severity"] == "critical"
    assert snapshot["severity_code"] == 4
    assert snapshot["gateway_ping_loss_percent"] == 25.88


def test_unknown_fixture_classification() -> None:
    fixture = load_fixture("unknown.json")
    snapshot = build_snapshot(fixture["facts"], collected_at="2026-05-24T23:17:44+00:00")
    assert snapshot["state"] == "UNKNOWN"
    assert snapshot["state_code"] == 3
    assert snapshot["severity"] == "unknown_or_error"
    assert snapshot["severity_code"] == 5


def test_error_fixture_classification() -> None:
    fixture = load_fixture("error.json")
    snapshot = build_snapshot(fixture["facts"], collected_at="2026-05-24T23:17:44+00:00")
    assert snapshot["state"] == "ERROR"
    assert snapshot["state_code"] == 5
    assert snapshot["severity"] == "unknown_or_error"
    assert snapshot["severity_code"] == 5


def test_classify_state_warns_on_high_latency_without_loss() -> None:
    state, state_code, severity, severity_code = classify_state(
        {
            "interface": "enp6s0",
            "operstate": "up",
            "carrier": True,
            "gateway_ip_present": True,
            "gateway_ping_loss_percent": 0,
            "gateway_ping_ok": True,
            "gateway_ping_ms_max": 141,
            "dns_success_count": 1,
        }
    )
    assert (state, state_code, severity, severity_code) == ("WARN", 1, "warning", 2)


def test_classify_state_bad_on_no_carrier() -> None:
    state, state_code, severity, severity_code = classify_state(
        {
            "interface": "enp6s0",
            "operstate": "down",
            "carrier": False,
            "gateway_ip_present": True,
            "gateway_ping_loss_percent": 0,
            "gateway_ping_ok": False,
            "dns_success_count": 0,
        }
    )
    assert (state, state_code, severity, severity_code) == ("BAD", 2, "critical", 4)


def test_snapshot_defaults_are_read_only_not_runtime_wiring() -> None:
    fixture = load_fixture("ok.json")
    snapshot = build_snapshot(fixture["facts"], collected_at="2026-05-24T23:17:44+00:00")
    assert snapshot["agent_id"] == "network.link.ro"
    assert snapshot["freshness"] == "fresh"
    assert snapshot["freshness_code"] == 0
    assert snapshot["operation_state"] == "completed"
    assert snapshot["operation_state_code"] == 6
    assert snapshot["wan_hint"] == "not_evaluated"
    assert snapshot["vpn_hint"] == "not_evaluated"
