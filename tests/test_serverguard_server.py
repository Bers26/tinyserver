from __future__ import annotations

import json
from collections import namedtuple

from tinyserver_collectors.serverguard_server import collect_serverguard_server
from tinyserver_collectors.serverguard_server_cli import main as server_cli_main
from tinyserver_collectors.serverguard_server_framework import to_framework_snapshot


DiskUsage = namedtuple("usage", "total used free")


def test_server_snapshot_has_non_empty_checks(monkeypatch, tmp_path) -> None:
    uptime = tmp_path / "uptime"
    loadavg = tmp_path / "loadavg"
    meminfo = tmp_path / "meminfo"
    uptime.write_text("3600.00 100.00\n", encoding="utf-8")
    loadavg.write_text("0.10 0.20 0.30 1/100 123\n", encoding="utf-8")
    meminfo.write_text("MemTotal:       1000000 kB\nMemAvailable:    750000 kB\n", encoding="utf-8")
    monkeypatch.setattr("tinyserver_collectors.serverguard_server.shutil.disk_usage", lambda path: DiskUsage(1000, 250, 750))
    monkeypatch.setattr("tinyserver_collectors.serverguard_server.os.cpu_count", lambda: 4)
    monkeypatch.setattr("tinyserver_collectors.serverguard_server.socket.gethostname", lambda: "tinyserver-test")

    snapshot = to_framework_snapshot(
        collect_serverguard_server(
            uptime_path=uptime,
            loadavg_path=loadavg,
            meminfo_path=meminfo,
        )
    )

    assert snapshot["agent_id"] == "serverguard.server.ro"
    assert snapshot["domain"] == "server"
    assert snapshot["state"] == "OK"
    assert snapshot["capabilities"] == {"read_only": True, "actions": []}
    assert set(snapshot["checks"]) == {
        "server.hostname",
        "server.uptime",
        "server.load",
        "server.memory",
        "server.root_disk",
        "server.platform",
    }
    assert snapshot["checks"]["server.hostname"]["summary"] == "Hostname: tinyserver-test."


def test_server_snapshot_has_required_numeric_metrics(monkeypatch, tmp_path) -> None:
    uptime = tmp_path / "uptime"
    loadavg = tmp_path / "loadavg"
    meminfo = tmp_path / "meminfo"
    uptime.write_text("7200.00 200.00\n", encoding="utf-8")
    loadavg.write_text("0.50 0.40 0.30 1/100 123\n", encoding="utf-8")
    meminfo.write_text("MemTotal:       2000000 kB\nMemAvailable:   1000000 kB\n", encoding="utf-8")
    monkeypatch.setattr("tinyserver_collectors.serverguard_server.shutil.disk_usage", lambda path: DiskUsage(4000, 1000, 3000))
    monkeypatch.setattr("tinyserver_collectors.serverguard_server.os.cpu_count", lambda: 8)

    snapshot = to_framework_snapshot(
        collect_serverguard_server(
            uptime_path=uptime,
            loadavg_path=loadavg,
            meminfo_path=meminfo,
        )
    )

    metrics = snapshot["metrics"]
    required = [
        "uptime_seconds",
        "load_1m",
        "load_5m",
        "load_15m",
        "cpu_count",
        "memory_total_bytes",
        "memory_available_bytes",
        "memory_used_percent",
        "root_used_percent",
        "freshness_code",
        "operation_state_code",
    ]
    assert all(isinstance(metrics[key], (int, float)) for key in required)
    assert metrics["uptime_seconds"] == 7200.0
    assert metrics["load_1m"] == 0.5
    assert metrics["cpu_count"] == 8
    assert metrics["memory_total_bytes"] == 2000000 * 1024
    assert metrics["memory_available_bytes"] == 1000000 * 1024
    assert metrics["memory_used_percent"] == 50.0
    assert metrics["root_used_percent"] == 25.0


def test_server_cli_generates_valid_json(capsys) -> None:
    assert server_cli_main() == 0
    snapshot = json.loads(capsys.readouterr().out)

    assert snapshot["agent_id"] == "serverguard.server.ro"
    assert snapshot["checks"]
    assert snapshot["metrics"]
