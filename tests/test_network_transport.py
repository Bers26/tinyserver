from __future__ import annotations

from tinyserver_collectors.network_transport import (
    BOOL_FALSE,
    BOOL_TRUE,
    CommandResult,
    REQUIRED_OUTPUT_FIELDS,
    build_snapshot,
    classify_state,
    collect_network_transport,
    parse_curl_probe,
)


class FakeRunner:
    def __init__(self, responses: dict[str, CommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], int | float]] = []

    def __call__(self, args, timeout):
        command = tuple(args)
        self.calls.append((command, timeout))
        url = command[-1]
        proxy = "--proxy" in command
        key = f"{'socks' if proxy else 'direct'}:{url}"
        return self.responses.get(key, CommandResult(28, "000 0.000000", "missing fake response"))


def responses(*, direct_github: CommandResult, socks_github: CommandResult, direct_gstatic: CommandResult, socks_gstatic: CommandResult) -> dict[str, CommandResult]:
    return {
        "direct:https://api.github.com/rate_limit": direct_github,
        "socks:https://api.github.com/rate_limit": socks_github,
        "direct:https://www.gstatic.com/generate_204": direct_gstatic,
        "socks:https://www.gstatic.com/generate_204": socks_gstatic,
    }


def test_required_output_fields_are_complete() -> None:
    snapshot = build_snapshot(
        {
            "direct_github_api_ok": True,
            "socks_github_api_ok": False,
            "direct_gstatic_ok": True,
            "socks_gstatic_ok": False,
            "socks_port_alive": True,
        },
        collected_at="2026-05-29T12:00:00+00:00",
    )

    assert tuple(snapshot.keys()) == REQUIRED_OUTPUT_FIELDS
    assert snapshot["agent_id"] == "network.transport.ro"
    assert snapshot["state"] == "OK"
    assert snapshot["direct_github_api_ok_value"] == BOOL_TRUE
    assert snapshot["socks_github_api_ok_value"] == BOOL_FALSE
    assert snapshot["transport_success_count"] == 2
    assert snapshot["transport_checked_count"] == 4


def test_parse_curl_probe_extracts_code_time_and_ok() -> None:
    assert parse_curl_probe("200 0.123456", 0) == (200, 123.456, True)
    assert parse_curl_probe("503 1.000000", 0) == (503, 1000.0, False)
    assert parse_curl_probe("", 28) == (None, None, False)


def test_classify_state_ok_when_socks_path_has_both_targets() -> None:
    state, state_code, severity, severity_code = classify_state(
        {
            "socks_github_api_ok": True,
            "socks_gstatic_ok": True,
            "direct_github_api_ok": False,
            "direct_gstatic_ok": False,
            "transport_checked_count": 4,
            "transport_success_count": 2,
        }
    )

    assert (state, state_code, severity, severity_code) == ("OK", 0, "normal", 0)


def test_classify_state_warn_when_only_one_target_family_works() -> None:
    state, state_code, severity, severity_code = classify_state(
        {
            "direct_github_api_ok": True,
            "socks_github_api_ok": False,
            "direct_gstatic_ok": False,
            "socks_gstatic_ok": False,
            "transport_checked_count": 4,
            "transport_success_count": 1,
        }
    )

    assert (state, state_code, severity, severity_code) == ("WARN", 1, "degraded", 3)


def test_classify_state_bad_when_checked_and_none_work() -> None:
    state, state_code, severity, severity_code = classify_state(
        {
            "direct_github_api_ok": False,
            "socks_github_api_ok": False,
            "direct_gstatic_ok": False,
            "socks_gstatic_ok": False,
            "transport_checked_count": 4,
            "transport_success_count": 0,
        }
    )

    assert (state, state_code, severity, severity_code) == ("BAD", 2, "critical", 4)


def test_classify_state_unknown_without_checks() -> None:
    assert classify_state({"transport_checked_count": 0})[0] == "UNKNOWN"


def test_collect_network_transport_ok_with_fake_runner() -> None:
    runner = FakeRunner(
        responses(
            direct_github=CommandResult(28, "000 0.000000"),
            socks_github=CommandResult(0, "200 0.111000"),
            direct_gstatic=CommandResult(28, "000 0.000000"),
            socks_gstatic=CommandResult(0, "204 0.222000"),
        )
    )

    snapshot = collect_network_transport(
        runner,
        timeout=3,
        collected_at="2026-05-29T12:00:00+00:00",
    )

    assert snapshot["state"] == "OK"
    assert snapshot["socks_github_api_ok_value"] == BOOL_TRUE
    assert snapshot["socks_gstatic_ok_value"] == BOOL_TRUE
    assert snapshot["direct_github_http_code"] == 0
    assert snapshot["socks_github_http_code"] == 200
    assert snapshot["socks_gstatic_http_code"] == 204
    assert snapshot["socks_github_time_ms"] == 111.0
    assert snapshot["socks_gstatic_time_ms"] == 222.0
    assert snapshot["transport_success_count"] == 2
    assert all(timeout == 3 for _, timeout in runner.calls)
    assert all(call[0][0] == "curl" for call in runner.calls)


def test_collect_network_transport_error_from_runner() -> None:
    def broken_runner(args, timeout):
        raise RuntimeError("boom")

    snapshot = collect_network_transport(
        broken_runner,
        collected_at="2026-05-29T12:00:00+00:00",
    )

    assert snapshot["state"] == "ERROR"
    assert snapshot["state_code"] == 5
    assert snapshot["operation_state"] == "failed"
    assert snapshot["operation_state_code"] == 5
    assert snapshot["transport_hint"] == "collector_error:RuntimeError"
