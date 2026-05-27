from __future__ import annotations

import json

from tinyserver_collectors.power_status import collect_power_status, parse_apcupsd_text
from tinyserver_collectors.power_status_cli import main as power_cli_main
from tinyserver_collectors.power_status_framework import REQUIRED_CHECK_IDS, to_framework_snapshot


ONLINE_SAMPLE = """\
APC      : 001,036,0876
DATE     : 2026-05-27 10:10:00 +0300
HOSTNAME : tinyserver
VERSION  : 3.14.14
UPSNAME  : tinyserver-ups
CABLE    : USB Cable
DRIVER   : USB UPS Driver
UPSMODE  : Stand Alone
STARTTIME: 2026-05-27 09:00:00 +0300
STATUS   : ONLINE
LINEV    : 229.0 Volts
LOADPCT  : 12.0 Percent
BCHARGE  : 100.0 Percent
TIMELEFT : 48.0 Minutes
MBATTCHG : 5 Percent
MINTIMEL : 3 Minutes
MAXTIME  : 0 Seconds
OUTPUTV  : 230.0 Volts
ITEMP    : 29.2 C
SELFTEST : NO
BATTDATE : 2025-11-01
END APC  : 2026-05-27 10:10:01 +0300
"""


def test_power_parser_handles_online_healthy_ups_sample() -> None:
    parsed = parse_apcupsd_text(ONLINE_SAMPLE)

    assert parsed["STATUS"] == "ONLINE"
    assert parsed["BCHARGE"] == "100.0 Percent"
    assert parsed["TIMELEFT"] == "48.0 Minutes"

    raw = collect_power_status(ONLINE_SAMPLE)

    assert raw["state"] == "OK"
    assert raw["severity_code"] == 0
    assert raw["metrics"]["battery_percent"] == 100.0
    assert raw["metrics"]["runtime_min"] == 48.0
    assert raw["metrics"]["input_voltage"] == 229.0
    assert raw["metrics"]["output_voltage"] == 230.0
    assert raw["metrics"]["temperature_c"] == 29.2
    assert raw["metrics"]["load_percent"] == 12.0


def test_power_success_snapshot_has_non_empty_checks() -> None:
    snapshot = to_framework_snapshot(collect_power_status(ONLINE_SAMPLE))

    assert snapshot["agent_id"] == "power.status.ro"
    assert snapshot["domain"] == "power"
    assert snapshot["state"] == "OK"
    assert snapshot["capabilities"] == {"read_only": True, "actions": []}
    assert set(REQUIRED_CHECK_IDS).issubset(snapshot["checks"])
    assert snapshot["checks"]["power.apcupsd.status"]["state"] == "OK"
    assert snapshot["checks"]["power.apcupsd.status"]["evidence"]["command_class"] == "read_only"
    assert snapshot["checks"]["power.apcupsd.selftest"]["state"] == "OK"
    assert snapshot["checks"]["power.apcupsd.battery_date"]["state"] == "OK"


def test_power_missing_unparseable_source_returns_unknown_contract_snapshot() -> None:
    snapshot = to_framework_snapshot(collect_power_status("not apcupsd output"))

    assert snapshot["schema_version"] == "1.0"
    assert snapshot["agent_id"] == "power.status.ro"
    assert snapshot["state"] == "UNKNOWN"
    assert snapshot["severity"] == 5
    assert set(REQUIRED_CHECK_IDS).issubset(snapshot["checks"])
    assert snapshot["metrics"]["freshness_code"] == 4
    assert snapshot["metrics"]["operation_state_code"] == 7
    assert snapshot["checks"]["power.apcupsd.status"]["evidence"]["observed_value"] == "missing"


def test_power_cli_generates_valid_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "tinyserver_collectors.power_status_framework.collect_power_status",
        lambda: collect_power_status(ONLINE_SAMPLE),
    )

    assert power_cli_main() == 0
    snapshot = json.loads(capsys.readouterr().out)

    assert snapshot["agent_id"] == "power.status.ro"
    assert snapshot["checks"]
