from __future__ import annotations

import json
import pytest

from tinyserver_collectors import power_status
from tinyserver_collectors.power_status import collect_power_status, parse_nut_text
from tinyserver_collectors.power_status_cli import main as power_cli_main
from tinyserver_collectors.power_status_framework import REQUIRED_CHECK_IDS, to_framework_snapshot

ONLINE = """ups.status: OL
battery.charge: 100
battery.runtime: 13920
device.model: Smart-UPS 2200
"""

def service(**updates):
    result = {
        "active_state": "active", "sub_state": "running", "main_pid": 123,
        "tasks_current": 5, "limit_nofile_soft": 1024,
        "fd_count_available": True, "fd_count": 20,
        "fd_count_error": "", "fd_usage_ratio": 20/1024,
    }
    result.update(updates)
    return result


def test_nut_online_and_numeric_units():
    assert parse_nut_text(ONLINE)["ups.status"] == "OL"
    raw = collect_power_status(ONLINE, service_status=service())
    assert raw["provider"] == "nut/upsc"
    assert raw["state"] == "OK"
    assert raw["metrics"]["battery_percent"] == 100
    assert raw["metrics"]["runtime_min"] == 232
    assert raw["metrics"]["freshness_code"] == 0
    assert "input_voltage" not in raw["metrics"]
    assert raw["diagnosis_layer"]["likely_layer"] == "ups_hardware"
    snap = to_framework_snapshot(raw)
    assert snap["agent_id"] == "power.status.ro"
    assert snap["capabilities"] == {"read_only": True, "actions": []}
    assert set(REQUIRED_CHECK_IDS).issubset(snap["checks"])
    assert "power.nut.input_voltage" not in snap["checks"]
    assert snap["checks"]["power.nut.command"]["state"] == "OK"
    assert snap["checks"]["power.nut.service"]["state"] == "OK"


@pytest.mark.parametrize("status,expected", [
    ("OL", "OK"), ("OB", "WARN"), ("OL LB", "BAD"),
    ("OB FSD", "BAD"), ("OFF", "BAD"), ("OL RB", "WARN"),
])
def test_ups_status_priority(status, expected):
    raw = collect_power_status("ups.status: " + status, service_status=service())
    assert raw["state"] == expected
    assert to_framework_snapshot(raw)["state"] == expected


def test_nut_unparseable_text_unknown():
    snap = to_framework_snapshot(collect_power_status("not NUT output"))
    assert snap["state"] == "UNKNOWN"
    assert snap["metrics"]["freshness_code"] == 4
    assert snap["metrics"]["operation_state_code"] == 7
    assert snap["checks"]["power.nut.status"]["state"] == "UNKNOWN"


@pytest.mark.parametrize("message,error_class,state,freshness,layer", [
    ("ERR DATA-STALE", "data_stale", "STALE", "stale", "driver"),
    ("ERR DRIVER-NOT-CONNECTED", "driver_disconnected", "UNKNOWN", "unknown", "driver"),
    ("Connection reset by peer", "connection_reset", "UNKNOWN", "unknown", "transport"),
])
def test_driver_failures_not_mislabelled_hardware(monkeypatch, message, error_class, state, freshness, layer):
    monkeypatch.setattr(power_status, "run_upsc", lambda: (1, "", message))
    raw = collect_power_status(service_status=service())
    assert raw["state"] == state
    assert raw["freshness"] == freshness
    assert raw["diagnosis_layer"]["likely_layer"] == layer
    assert raw["command_error_class"] == error_class
    assert to_framework_snapshot(raw)["state"] == state


def test_service_resources_retained_for_nut():
    raw = collect_power_status(ONLINE, service_status=service(fd_count=1023, fd_usage_ratio=1023/1024, tasks_current=919))
    checks = to_framework_snapshot(raw)["checks"]
    assert checks["power.nut.fd_usage"]["state"] == "WARN"
    assert checks["power.nut.tasks"]["state"] == "WARN"
    assert raw["diagnosis_layer"]["likely_layer"] == "service"


def test_fd_unreadable_is_unknown_not_zero():
    raw = collect_power_status(ONLINE, service_status=service(fd_count_available=False, fd_count=None, fd_usage_ratio=None))
    snap = to_framework_snapshot(raw)
    assert snap["checks"]["power.nut.fd_usage"]["state"] == "UNKNOWN"


def test_missing_voltages_and_temperature_are_not_errors():
    raw = collect_power_status(ONLINE, service_status=service())
    snap = to_framework_snapshot(raw)
    assert snap["state"] == "OK"
    assert "power.nut.output_voltage" not in snap["checks"]
    assert "power.nut.temperature" not in snap["checks"]


def test_bad_numeric_values_not_fabricated():
    raw = collect_power_status("ups.status: OL\nbattery.charge: bad\nbattery.runtime: -1", service_status=service())
    assert raw["state"] == "OK"
    assert "battery_percent" not in raw["metrics"]
    assert "runtime_min" not in raw["metrics"]


def test_upsc_command_is_read_only_and_local(monkeypatch):
    calls=[]
    def runner(args, timeout_sec=5):
        calls.append(args)
        if args == ["upsc", "-l", "localhost"]:
            return 0, "apc\n", ""
        return 0, ONLINE, ""
    monkeypatch.setattr(power_status, "run_command", runner)
    rc, data, err = power_status.run_upsc()
    assert rc == 0 and "ups.status" in data and not err
    assert calls == [["upsc", "-l", "localhost"], ["upsc", "apc@localhost"]]


def test_cli_contract_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "tinyserver_collectors.power_status_framework.collect_power_status",
        lambda: collect_power_status(ONLINE, service_status=service()),
    )
    assert power_cli_main() == 0
    snap = json.loads(capsys.readouterr().out)
    assert snap["agent_id"] == "power.status.ro"
    assert snap["checks"]["power.nut.status"]["state"] == "OK"
