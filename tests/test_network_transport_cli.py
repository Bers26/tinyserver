from __future__ import annotations

import subprocess

from tinyserver_collectors.network_transport_cli import default_command_runner


def test_default_command_runner_normalizes_timeout(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["curl"], timeout=5, output="partial", stderr="late")

    monkeypatch.setattr("tinyserver_collectors.network_transport_cli.subprocess.run", fake_run)

    result = default_command_runner(("curl",), 5)

    assert result.returncode == 124
    assert result.stdout == "partial"
    assert result.stderr == "late"


def test_default_command_runner_normalizes_os_error(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise OSError("missing command")

    monkeypatch.setattr("tinyserver_collectors.network_transport_cli.subprocess.run", fake_run)

    result = default_command_runner(("missing",), 5)

    assert result.returncode == 127
    assert result.stdout == ""
    assert result.stderr == "missing command"


def test_default_command_runner_success(monkeypatch) -> None:
    completed = subprocess.CompletedProcess(args=["cmd"], returncode=0, stdout="200 0.100000", stderr="")

    def fake_run(*args, **kwargs):
        return completed

    monkeypatch.setattr("tinyserver_collectors.network_transport_cli.subprocess.run", fake_run)

    result = default_command_runner(("cmd",), 5)

    assert result.returncode == 0
    assert result.stdout == "200 0.100000"
    assert result.stderr == ""
