from __future__ import annotations

from tinyserver_collectors.service_health import (
    UnitFile,
    classify_unit,
    collect_service_health,
    discover_units,
    parse_systemctl_show,
    parse_unit_files,
    safe_metric_label,
)
from tinyserver_collectors.service_health_framework import to_framework_snapshot


def test_parse_unit_files_and_discovery() -> None:
    unit_files = parse_unit_files(
        "\n".join(
            [
                "UNIT FILE STATE PRESET",
                "agent-ro-network-link-ro.timer enabled enabled",
                "agent-ro-power-status-ro.timer disabled enabled",
                "serverguard-agent-ro-prom.timer enabled enabled",
                "ssh.service enabled enabled",
                "docker.service enabled enabled",
            ]
        )
    )

    units = discover_units(unit_files)

    assert "agent-ro-network-link-ro.timer" in units
    assert "serverguard-agent-ro-prom.timer" in units
    assert "agent-ro-storage-status-ro.timer" in units
    assert "agent-ro-registry.timer" in units
    assert "agent-ro-power-status-ro.timer" not in units
    assert "ssh.service" not in units
    assert "docker.service" not in units


def test_safe_metric_label() -> None:
    assert safe_metric_label("agent-ro-network-link-ro.timer") == "agent_ro_network_link_ro_timer"
    assert safe_metric_label("serverguard-agent-ro-prom.service") == "serverguard_agent_ro_prom_service"


def test_classify_unit_timer_service_and_failed() -> None:
    timer_show = parse_systemctl_show("LoadState=loaded\nActiveState=active\nSubState=waiting\nResult=success\nUnitFileState=enabled\n")
    assert classify_unit("agent-ro-storage-status-ro.timer", timer_show)[0] == "OK"

    inactive_timer_show = parse_systemctl_show("LoadState=loaded\nActiveState=inactive\nSubState=dead\nResult=success\nUnitFileState=enabled\n")
    assert classify_unit("agent-ro-storage-status-ro.timer", inactive_timer_show)[0] == "WARN"

    oneshot_show = parse_systemctl_show("LoadState=loaded\nActiveState=inactive\nSubState=dead\nResult=success\nUnitFileState=static\n")
    assert classify_unit("agent-ro-storage-status-ro.service", oneshot_show)[0] == "OK"

    failed_show = parse_systemctl_show("LoadState=loaded\nActiveState=failed\nSubState=failed\nResult=exit-code\nUnitFileState=enabled\n")
    assert classify_unit("agent-ro-storage-status-ro.service", failed_show)[0] == "BAD"


def test_framework_snapshot_has_checks_and_numeric_metrics() -> None:
    snapshot = to_framework_snapshot(
        {
            "agent_id": "service.health.ro",
            "collected_at": "2026-05-25T20:15:00+00:00",
            "state": "OK",
            "state_code": 0,
            "severity": "normal",
            "severity_code": 0,
            "freshness_code": 0,
            "operation_state_code": 6,
            "unit_count": 2,
            "units": [
                {
                    "unit": "agent-ro-storage-status-ro.timer",
                    "unit_type": "timer",
                    "unit_type_code": 2,
                    "command_rc": 0,
                    "load_state": "loaded",
                    "active_state": "active",
                    "sub_state": "waiting",
                    "result": "success",
                    "unit_file_state": "enabled",
                    "active_value": 1,
                    "enabled_value": 1,
                    "state": "OK",
                    "state_code": 0,
                    "severity": "normal",
                    "severity_code": 0,
                    "summary": "ok",
                },
                {
                    "unit": "agent-ro-network-link-ro.service",
                    "unit_type": "service",
                    "unit_type_code": 1,
                    "command_rc": 0,
                    "load_state": "loaded",
                    "active_state": "inactive",
                    "sub_state": "dead",
                    "result": "success",
                    "unit_file_state": "static",
                    "active_value": 0,
                    "enabled_value": 0,
                    "state": "OK",
                    "state_code": 0,
                    "severity": "normal",
                    "severity_code": 0,
                    "summary": "ok",
                },
            ],
        }
    )

    assert snapshot["agent_id"] == "service.health.ro"
    assert snapshot["domain"] == "service"
    assert snapshot["state"] == "OK"
    assert snapshot["severity"] == 0
    assert snapshot["capabilities"] == {"read_only": True, "actions": []}
    assert "service_agent_ro_storage_status_ro_timer_health" in snapshot["checks"]
    assert snapshot["checks"]["service_agent_ro_storage_status_ro_timer_health"]["state"] == "OK"
    assert snapshot["metrics"]["unit_count"] == 2
    assert snapshot["metrics"]["unit_agent_ro_storage_status_ro_timer_active_value"] == 1
    assert snapshot["metrics"]["unit_agent_ro_network_link_ro_service_active_value"] == 0


def test_collect_service_health_with_explicit_missing_unit_is_bad() -> None:
    snapshot = collect_service_health(["definitely-missing-serverguard-test-unit.timer"])

    assert snapshot["agent_id"] == "service.health.ro"
    assert snapshot["unit_count"] == 1
    assert snapshot["state"] == "BAD"
    assert snapshot["units"][0]["unit"] == "definitely-missing-serverguard-test-unit.timer"
    assert snapshot["units"][0]["state"] == "BAD"
