from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from tinyserver_collectors.prometheus_projection import render_prometheus_from_registry


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_render_prometheus_projects_base_and_network_metrics(tmp_path: Path) -> None:
    latest = tmp_path / "network.link.ro" / "latest.json"
    write_json(
        tmp_path / "agent-ro-full.json",
        {
            "agents": [
                {
                    "agent_id": "network.link.ro",
                    "latest_path": str(latest),
                    "enabled": True,
                }
            ]
        },
    )
    write_json(
        latest,
        {
            "agent_id": "network.link.ro",
            "collected_at": "2026-05-25T11:13:07+00:00",
            "state": "OK",
            "severity": 0,
            "metrics": {
                "carrier_value": 1,
                "speed_mbps": 100,
                "gateway_ping_ok_value": 1,
                "gateway_ping_loss_percent": 0.0,
                "gateway_ping_ms_avg": 1.479,
                "dns_ok_value": 1,
                "dns_success_count": 3,
                "freshness_code": 0,
                "operation_state_code": 6,
                "provider": "ignored-string",
            },
        },
    )

    text = render_prometheus_from_registry(
        tmp_path / "agent-ro-full.json",
        now=datetime(2026, 5, 25, 11, 13, 17, tzinfo=timezone.utc),
    )

    assert 'agent_ro_state_code{contour="serverguard",stream="network.link"} 0' in text
    assert 'agent_ro_age_seconds{contour="serverguard",stream="network.link"} 10' in text
    assert 'agent_ro_network_carrier_value{contour="serverguard",stream="network.link"} 1' in text
    assert 'agent_ro_network_speed_mbps{contour="serverguard",stream="network.link"} 100' in text
    assert 'agent_ro_network_gateway_ping_ms_avg{contour="serverguard",stream="network.link"} 1.479' in text
    assert "ignored-string" not in text
    assert 'agent_ro_projection_error_value{contour="serverguard",stream="network.link"} 0' in text


def test_render_prometheus_projects_missing_latest_error(tmp_path: Path) -> None:
    write_json(
        tmp_path / "agent-ro-full.json",
        {
            "agents": [
                {
                    "agent_id": "network.link.ro",
                    "latest_path": str(tmp_path / "missing.json"),
                    "enabled": True,
                }
            ]
        },
    )

    text = render_prometheus_from_registry(tmp_path / "agent-ro-full.json")

    assert 'agent_ro_projection_error_value{contour="serverguard",stream="network.link"} 1' in text


def test_render_prometheus_skips_disabled_agents(tmp_path: Path) -> None:
    latest = tmp_path / "network.link.ro" / "latest.json"
    write_json(
        tmp_path / "agent-ro-full.json",
        {
            "agents": [
                {
                    "agent_id": "network.link.ro",
                    "latest_path": str(latest),
                    "enabled": False,
                }
            ]
        },
    )

    text = render_prometheus_from_registry(tmp_path / "agent-ro-full.json")

    assert text == "\n"
