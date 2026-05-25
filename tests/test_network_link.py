from __future__ import annotations

import json
from pathlib import Path

from tinyserver_collectors.network_link import (
    BOOL_FALSE,
    BOOL_TRUE,
    BOOL_UNKNOWN,
    CommandResult,
    REQUIRED_OUTPUT_FIELDS,
    bool_value,
    build_snapshot,
    classify_state,
    collect_network_link,
    parse_default_route,
    parse_ping_summary,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "network_link"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def write_sysfs(root: Path, iface: str = "enp6s0") -> None:
    iface_dir = root / iface
    stats_dir = iface_dir / "statistics"
    stats_dir.mkdir(parents=True)
    (iface_dir / "operstate").write_text("up", encoding="utf-8")
    (iface_dir / "carrier").write_text("1", encoding="utf-8")
    (iface_dir / "speed").write_text("100", encoding="utf-8")
    (iface_dir / "duplex").write_text("full", encoding="utf-8")
    for key, value in {
        "rx_errors": "0",
        "tx_errors": "4",
        "rx_dropped": "0",
        "tx_dropped": "0",
    }.items():
        (stats_dir / key).write_text(value, encoding="utf-8")


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], int | float]] = []

    def __call__(self, args, timeout):
        key = tuple(args)
        self.calls.append((key, timeout))
        if key not in self.responses:
            return CommandResult(127, "", "missing fake response")
        return self.responses[key]


def base_responses(loss_output: str | None = None) -> dict[tuple[str, ...], CommandResult]:
    ping_output = loss_output or """PING 10.1.1.1 (10.1.1.1) 56(84) bytes of data.

--- 10.1.1.1 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4000ms
rtt min/avg/max/mdev = 0.353/1.440/3.936/0.747 ms
"""
    return {
        ("ip", "route", "show", "default"): CommandResult(0, "default via 10.1.1.1 dev enp6s0 proto static\n"),
        ("ping", "-c", "5", "-W", "1", "10.1.1.1"): CommandResult(0, ping_output),
        ("getent", "hosts", "github.com"): CommandResult(0, "140.82.121.3 github.com\n"),
        ("getent", "hosts", "google.com"): CommandResult(2, ""),
        ("getent", "hosts", "api.telegram.org"): CommandResult(0, "2001:67c:4e8:f004::9 api.telegram.org\n"),
        ("resolvectl", "status"): CommandResult(0, "Link 624 (tun0)\n       DNS Servers: 172.19.0.2\n"),
    }


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


def test_classify_state_warns_on_transient_gateway_ping_failure_when_dns_works() -> None:
    state, state_code, severity, severity_code = classify_state(
        {
            "interface": "enp6s0",
            "operstate": "up",
            "carrier": True,
            "gateway_ip_present": True,
            "gateway_ping_loss_percent": 100,
            "gateway_ping_ok": False,
            "dns_success_count": 3,
        }
    )
    assert (state, state_code, severity, severity_code) == ("WARN", 1, "degraded", 3)


def test_classify_state_bad_when_gateway_and_dns_are_down() -> None:
    state, state_code, severity, severity_code = classify_state(
        {
            "interface": "enp6s0",
            "operstate": "up",
            "carrier": True,
            "gateway_ip_present": True,
            "gateway_ping_loss_percent": 100,
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


def test_parse_default_route() -> None:
    output = "default via 10.1.1.1 dev enp6s0 proto static\n"
    assert parse_default_route(output) == ("enp6s0", "10.1.1.1")


def test_parse_default_route_missing_default() -> None:
    assert parse_default_route("10.1.1.0/24 dev enp6s0 proto kernel\n") == (None, None)


def test_parse_ping_summary() -> None:
    output = """--- 10.1.1.1 ping statistics ---
60 packets transmitted, 60 received, 0% packet loss, time 29603ms
rtt min/avg/max/mdev = 0.353/1.440/3.936/0.747 ms
"""
    parsed = parse_ping_summary(output)
    assert parsed["gateway_ping_ok"] is True
    assert parsed["gateway_ping_loss_percent"] == 0.0
    assert parsed["gateway_ping_ms_min"] == 0.353
    assert parsed["gateway_ping_ms_avg"] == 1.440
    assert parsed["gateway_ping_ms_max"] == 3.936


def test_collect_network_link_ok_with_fake_runner_and_sysfs(tmp_path: Path) -> None:
    write_sysfs(tmp_path)
    (tmp_path / "tun0").mkdir()
    runner = FakeRunner(base_responses())

    snapshot = collect_network_link(
        command_runner=runner,
        sysfs_root=tmp_path,
        timeout=3,
        collected_at="2026-05-24T23:17:44+00:00",
    )

    assert snapshot["state"] == "OK"
    assert snapshot["state_code"] == 0
    assert snapshot["interface"] == "enp6s0"
    assert snapshot["gateway_ip_present_value"] == BOOL_TRUE
    assert snapshot["gateway_ping_ok_value"] == BOOL_TRUE
    assert snapshot["gateway_ping_loss_percent"] == 0.0
    assert snapshot["dns_success_count"] == 2
    assert snapshot["vpn_interface_present_value"] == BOOL_TRUE
    assert snapshot["vpn_dns_present_value"] == BOOL_TRUE
    assert snapshot["wan_hint"] == "dns_reachable"
    assert snapshot["vpn_hint"] == "vpn_interface_present"
    assert all(timeout == 3 for _, timeout in runner.calls)


def test_collect_network_link_warn_on_small_loss(tmp_path: Path) -> None:
    write_sysfs(tmp_path)
    runner = FakeRunner(
        base_responses(
            """--- 10.1.1.1 ping statistics ---
100 packets transmitted, 96 received, 4% packet loss, time 99000ms
rtt min/avg/max/mdev = 1.000/8.000/390.000/1.000 ms
"""
        )
    )

    snapshot = collect_network_link(
        command_runner=runner,
        sysfs_root=tmp_path,
        collected_at="2026-05-24T23:17:44+00:00",
    )

    assert snapshot["state"] == "WARN"
    assert snapshot["severity"] == "warning"
    assert snapshot["gateway_ping_loss_percent"] == 4.0


def test_collect_network_link_unknown_without_route(tmp_path: Path) -> None:
    runner = FakeRunner({("ip", "route", "show", "default"): CommandResult(0, "")})

    snapshot = collect_network_link(
        command_runner=runner,
        sysfs_root=tmp_path,
        collected_at="2026-05-24T23:17:44+00:00",
    )

    assert snapshot["state"] == "UNKNOWN"
    assert snapshot["state_code"] == 3
    assert snapshot["interface"] is None


def test_collect_network_link_error_from_runner(tmp_path: Path) -> None:
    def broken_runner(args, timeout):
        raise RuntimeError("boom")

    snapshot = collect_network_link(
        command_runner=broken_runner,
        sysfs_root=tmp_path,
        collected_at="2026-05-24T23:17:44+00:00",
    )

    assert snapshot["state"] == "ERROR"
    assert snapshot["state_code"] == 5
    assert snapshot["operation_state"] == "failed"
    assert snapshot["operation_state_code"] == 5
    assert snapshot["wan_hint"] == "collector_error:RuntimeError"
