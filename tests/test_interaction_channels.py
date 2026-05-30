from __future__ import annotations

import json

from tinyserver_collectors.interaction_channels import ProbeResult, collect_interaction_channels
from tinyserver_collectors.interaction_channels_cli import main as interaction_cli_main
from tinyserver_collectors.interaction_channels_framework import to_framework_snapshot


REQUIRED_CHECKS = {
    "interaction.telegram.channel",
    "interaction.big_ui.channel",
    "interaction.llm.channel",
    "interaction.voice.channel",
}
ALLOWED_SOURCE_TYPES = {"api", "command", "derived", "file", "static"}


def test_raw_collector_default_is_read_only_safe_unknown_warn_without_secrets() -> None:
    raw = collect_interaction_channels(collected_at="2026-05-30T00:00:00+00:00")
    payload = json.dumps(raw, sort_keys=True).lower()

    assert raw["agent_id"] == "interaction.channels.ro"
    assert raw["state"] == "WARN"
    assert raw["channels"]["telegram"]["state"] == "UNKNOWN"
    assert raw["channels"]["telegram"]["source"] == "not_configured"
    assert "token" not in payload
    assert "secret" not in payload


def test_framework_snapshot_has_required_contract_fields_and_checks() -> None:
    snapshot = to_framework_snapshot(
        collect_interaction_channels(collected_at="2026-05-30T00:00:00+00:00")
    )

    assert snapshot["agent_id"] == "interaction.channels.ro"
    assert snapshot["product"] == "Tiny Agent Framework"
    assert snapshot["state"] == "WARN"
    assert isinstance(snapshot["severity"], int)
    assert snapshot["collected_at"] == "2026-05-30T00:00:00+00:00"
    assert snapshot["summary"]
    assert set(snapshot["checks"]) == REQUIRED_CHECKS
    assert isinstance(snapshot["checks"], dict)
    assert isinstance(snapshot["metrics"], dict)
    assert snapshot["capabilities"] == {"read_only": True, "actions": []}
    assert all(isinstance(value, (int, float)) for value in snapshot["metrics"].values())

    for check in snapshot["checks"].values():
        assert {"state", "severity", "confidence", "summary", "rule_id", "ruleset_version", "evidence"} <= set(check)
        assert check["evidence"]["command_class"] in {"read_only", "local_file_read", "local_fact"}
        assert check["evidence"]["source_type"] in ALLOWED_SOURCE_TYPES


def test_required_metrics_are_present() -> None:
    snapshot = to_framework_snapshot(collect_interaction_channels())
    metrics = snapshot["metrics"]

    for key in (
        "channels_total",
        "channels_ok",
        "channels_warn",
        "channels_bad",
        "channels_unknown",
        "channels_deferred",
        "operation_state_code",
    ):
        assert isinstance(metrics[key], int)


def test_big_ui_ok_fixture_makes_big_ui_check_ok() -> None:
    raw = collect_interaction_channels(
        big_ui_probe=lambda url, timeout: ProbeResult(ok=True, status_code=200),
        collected_at="2026-05-30T00:00:00+00:00",
    )
    snapshot = to_framework_snapshot(raw)

    assert raw["channels"]["big_ui"]["state"] == "OK"
    assert snapshot["checks"]["interaction.big_ui.channel"]["state"] == "OK"
    assert snapshot["checks"]["interaction.big_ui.channel"]["evidence"]["source_type"] == "api"

def test_framework_check_evidence_source_types_are_schema_valid() -> None:
    raw = collect_interaction_channels(
        big_ui_probe=lambda url, timeout: ProbeResult(ok=True, status_code=200),
        telegram_status={"source_type": "none"},
        llm_status={"source_type": "injected_fact", "configured": True, "ok": True},
    )
    snapshot = to_framework_snapshot(raw)

    source_types = {check["evidence"]["source_type"] for check in snapshot["checks"].values()}
    assert source_types <= ALLOWED_SOURCE_TYPES
    assert snapshot["checks"]["interaction.telegram.channel"]["evidence"]["source_type"] == "static"
    assert snapshot["checks"]["interaction.big_ui.channel"]["evidence"]["source_type"] == "api"
    assert snapshot["checks"]["interaction.llm.channel"]["evidence"]["source_type"] == "static"
    assert snapshot["checks"]["interaction.voice.channel"]["evidence"]["source_type"] == "static"



def test_missing_unconfigured_telegram_does_not_fail_collector() -> None:
    raw = collect_interaction_channels(
        big_ui_probe=lambda url, timeout: ProbeResult(ok=True, status_code=200),
        llm_status={"configured": True, "ok": True, "source_type": "injected_fact"},
    )

    assert raw["channels"]["telegram"]["state"] == "UNKNOWN"
    assert raw["state"] == "WARN"
    assert raw["state"] != "BAD"


def test_configured_critical_channel_unavailable_is_bad() -> None:
    raw = collect_interaction_channels(llm_status={"configured": True, "ok": False})

    assert raw["channels"]["llm"]["state"] == "BAD"
    assert raw["state"] == "BAD"


def test_voice_default_is_unknown_and_deferred() -> None:
    raw = collect_interaction_channels()

    assert raw["channels"]["voice"]["state"] == "UNKNOWN"
    assert raw["channels"]["voice"]["deferred"] is True
    assert raw["channels_deferred"] == 1


def test_cli_prints_valid_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "tinyserver_collectors.interaction_channels_cli.default_http_probe",
        lambda url, timeout: ProbeResult(ok=True, status_code=200),
    )

    assert interaction_cli_main() == 0
    snapshot = json.loads(capsys.readouterr().out)

    assert snapshot["agent_id"] == "interaction.channels.ro"
    assert set(snapshot["checks"]) == REQUIRED_CHECKS
    assert snapshot["capabilities"] == {"read_only": True, "actions": []}
