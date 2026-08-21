from __future__ import annotations

from tinyserver_collectors.network_transport import (
    BOOL_FALSE,
    BOOL_TRUE,
    BOOL_UNKNOWN,
    CommandResult,
    REQUIRED_OUTPUT_FIELDS,
    build_snapshot,
    classify_state,
    collect_network_transport,
    RU_GOV_TARGETS,
    parse_curl_probe,
    parse_ru_gov_curl_probe,
)


class FakeRunner:
    def __init__(self, responses: dict[str, CommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], int | float]] = []

    def __call__(self, args, timeout):
        command = tuple(args)
        self.calls.append((command, timeout))
        key = self._key(command)
        return self.responses.get(key, CommandResult(28, "000 0.000000", f"missing fake response for {key}"))

    @staticmethod
    def _key(command: tuple[str, ...]) -> str:
        if not command:
            return "unknown:"
        if command[0] == "curl":
            url = command[-1]
            proxy = "--proxy" in command
            return f"{'socks' if proxy else 'direct'}:{url}"
        if command[:2] == ("getent", "hosts") and len(command) >= 3:
            return f"dns:{command[2]}"
        if command[0] == "python3" and len(command) >= 6:
            return f"tcp:{command[-3]}:{command[-2]}"
        if command[0] == "nc" and len(command) >= 3:
            return f"socks-target:{command[-2]}:{command[-1]}"
        if command[:3] == ("git", "ls-remote", "--heads"):
            return f"git:{command[-1]}"
        if command[:3] == ("ip", "route", "get"):
            return f"route:{command[-1]}"
        return "unknown:" + " ".join(command)


def responses(
    *,
    direct_github: CommandResult,
    socks_github: CommandResult,
    direct_gstatic: CommandResult,
    socks_gstatic: CommandResult,
    direct_telegram: CommandResult = CommandResult(0, "302 0.105000"),
    socks_telegram: CommandResult = CommandResult(0, "302 0.106000"),
) -> dict[str, CommandResult]:
    ok = CommandResult(0, "ok\n")
    return {
        "dns:github.com": ok,
        "dns:ssh.github.com": ok,
        "dns:api.telegram.org": ok,
        "tcp:github.com:443": ok,
        "tcp:ssh.github.com:443": ok,
        "tcp:api.telegram.org:443": ok,
        "tcp:127.0.0.1:10808": ok,
        "socks-target:ssh.github.com:443": ok,
        "direct:https://api.github.com/rate_limit": direct_github,
        "socks:https://api.github.com/rate_limit": socks_github,
        "direct:https://www.gstatic.com/generate_204": direct_gstatic,
        "socks:https://www.gstatic.com/generate_204": socks_gstatic,
        "direct:https://api.telegram.org/": direct_telegram,
        "socks:https://api.telegram.org/": socks_telegram,
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
    assert snapshot["state"] == "WARN"
    assert snapshot["direct_github_api_ok_value"] == BOOL_TRUE
    assert snapshot["socks_github_api_ok_value"] == BOOL_FALSE
    assert snapshot["transport_success_count"] == 3
    assert snapshot["transport_checked_count"] == 5


def test_parse_curl_probe_extracts_code_time_and_ok() -> None:
    assert parse_curl_probe("200 0.123456", 0) == (200, 123.456, True)
    assert parse_curl_probe("503 1.000000", 0) == (503, 1000.0, False)
    assert parse_curl_probe("", 28) == (None, None, False)


def test_classify_state_warn_when_only_socks_path_has_both_targets() -> None:
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

    assert (state, state_code, severity, severity_code) == ("WARN", 1, "degraded", 3)


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

    assert snapshot["state"] == "WARN"
    assert snapshot["socks_github_api_ok_value"] == BOOL_TRUE
    assert snapshot["socks_gstatic_ok_value"] == BOOL_TRUE
    assert snapshot["direct_github_http_code"] == 0
    assert snapshot["socks_github_http_code"] == 200
    assert snapshot["socks_gstatic_http_code"] == 204
    assert snapshot["socks_github_time_ms"] == 111.0
    assert snapshot["socks_gstatic_time_ms"] == 222.0
    assert snapshot["direct_telegram_api_ok_value"] == BOOL_TRUE
    assert snapshot["socks_telegram_api_ok_value"] == BOOL_TRUE
    assert snapshot["direct_telegram_http_code"] == 302
    assert snapshot["socks_telegram_http_code"] == 302
    assert snapshot["transport_success_count"] == 12
    assert snapshot["transport_checked_count"] == 14
    assert all(timeout == 3 for _, timeout in runner.calls)
    assert any(call[0][0] == "curl" for call in runner.calls)
    assert any(call[0][0] == "getent" for call in runner.calls)
    assert any(call[0][0] == "python3" for call in runner.calls)
    assert any(call[0][0] == "nc" for call in runner.calls)


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


def test_v02_dns_failure_identifies_dns_layer() -> None:
    snapshot = build_snapshot(
        {
            "dns_github_ok": False,
            "dns_ssh_github_ok": True,
        },
        collected_at="2026-06-03T12:00:00+00:00",
    )

    assert snapshot["state"] == "WARN"
    assert snapshot["likely_failure_layer"] == "dns"
    assert snapshot["dns_github_ok_value"] == BOOL_FALSE


def test_v02_tcp_ok_but_git_transport_failure_is_git_layer() -> None:
    snapshot = build_snapshot(
        {
            "dns_github_ok": True,
            "dns_ssh_github_ok": True,
            "tcp_github_443_ok": True,
            "tcp_ssh_github_443_ok": True,
            "git_transport_ok": False,
            "git_transport_state": "failed",
        },
        collected_at="2026-06-03T12:00:00+00:00",
    )

    assert snapshot["state"] == "WARN"
    assert snapshot["likely_failure_layer"] == "git_transport"
    assert snapshot["git_transport_ok_value"] == BOOL_FALSE


def test_v02_socks_alive_but_socks_target_failure_is_socks_layer() -> None:
    snapshot = build_snapshot(
        {
            "dns_github_ok": True,
            "dns_ssh_github_ok": True,
            "tcp_github_443_ok": True,
            "tcp_ssh_github_443_ok": True,
            "socks_port_alive": True,
            "socks_ssh_github_443_ok": False,
        },
        collected_at="2026-06-03T12:00:00+00:00",
    )

    assert snapshot["state"] == "WARN"
    assert snapshot["likely_failure_layer"] == "socks_proxy"


def test_v02_mixed_burst_identifies_flapping() -> None:
    snapshot = build_snapshot(
        {
            "dns_github_ok": False,
            "dns_ssh_github_ok": True,
            "burst": {
                "dns_github": {
                    "success_count": 1,
                    "failure_count": 1,
                    "success_rate": 0.5,
                    "consecutive_failures": 1,
                    "last_ok_at": "2026-06-03T12:00:00+00:00",
                    "last_fail_at": "2026-06-03T12:00:00+00:00",
                }
            },
        },
        collected_at="2026-06-03T12:00:00+00:00",
    )

    assert snapshot["state"] == "WARN"
    assert snapshot["likely_failure_layer"] == "mixed_flapping"
    assert "dns_github" in snapshot["failed_targets"]


def test_v02_all_ok_without_git_probe_is_ok_and_git_disabled() -> None:
    runner = FakeRunner(
        responses(
            direct_github=CommandResult(0, "200 0.101000"),
            socks_github=CommandResult(0, "200 0.102000"),
            direct_gstatic=CommandResult(0, "204 0.103000"),
            socks_gstatic=CommandResult(0, "204 0.104000"),
        )
    )

    snapshot = collect_network_transport(
        runner,
        timeout=3,
        collected_at="2026-06-03T12:00:00+00:00",
    )

    assert snapshot["state"] == "OK"
    assert snapshot["git_transport_state"] == "disabled"
    assert snapshot["git_transport_ok_value"] == BOOL_UNKNOWN
    assert snapshot["transport_success_count"] == 14
    assert snapshot["transport_checked_count"] == 14
    assert snapshot["failed_targets"] == []


def test_telegram_failures_participate_in_failure_classification() -> None:
    runner = FakeRunner(
        responses(
            direct_github=CommandResult(0, "200 0.101000"),
            socks_github=CommandResult(0, "200 0.102000"),
            direct_gstatic=CommandResult(0, "204 0.103000"),
            socks_gstatic=CommandResult(0, "204 0.104000"),
            direct_telegram=CommandResult(28, "000 0.000000"),
            socks_telegram=CommandResult(28, "000 0.000000"),
        )
    )

    snapshot = collect_network_transport(runner, timeout=3, collected_at="2026-06-03T12:00:00+00:00")

    assert snapshot["state"] == "WARN"
    assert snapshot["likely_failure_layer"] == "https"
    assert "direct_telegram_api" in snapshot["failed_targets"]
    assert "socks_telegram_api" in snapshot["failed_targets"]
    assert snapshot["transport_success_count"] == 12
    assert snapshot["transport_checked_count"] == 14


def ru_gov_responses(*, https: CommandResult, route_dev: str) -> dict[str, CommandResult]:
    mapping = responses(
        direct_github=CommandResult(0, "200 0.101000"),
        socks_github=CommandResult(0, "200 0.102000"),
        direct_gstatic=CommandResult(0, "204 0.103000"),
        socks_gstatic=CommandResult(0, "204 0.104000"),
    )
    for index, host in enumerate(RU_GOV_TARGETS, start=10):
        ip_address = f"203.0.113.{index}"
        mapping[f"dns:{host}"] = CommandResult(0, f"{ip_address} {host}\n")
        mapping[f"tcp:{host}:443"] = CommandResult(0, "ok\n")
        mapping[f"direct:https://{host}/"] = https
        mapping[f"route:{ip_address}"] = CommandResult(
            0,
            f"{ip_address} via 192.0.2.1 dev {route_dev} src 192.0.2.10 uid 1000\n",
        )
    return mapping


def test_ru_gov_https_403_counts_as_transport_reachable() -> None:
    assert parse_ru_gov_curl_probe("403 0.123000", 0) == (403, 123.0, True, False)


def test_ru_gov_targets_are_never_probed_with_socks_proxy() -> None:
    runner = FakeRunner(ru_gov_responses(https=CommandResult(0, "403 0.123000"), route_dev="enp3s0"))

    collect_network_transport(runner, timeout=3, collected_at="2026-06-04T12:00:00+00:00")

    ru_gov_calls = [command for command, _timeout in runner.calls if any(host in command for host in RU_GOV_TARGETS)]
    assert ru_gov_calls
    assert all("--proxy" not in command for command in ru_gov_calls)
    assert all(command[0] != "nc" for command in ru_gov_calls)


def test_ru_gov_route_via_direct_devices_counts_direct() -> None:
    for route_dev in ("enp3s0", "eth0", "wlan0"):
        runner = FakeRunner(ru_gov_responses(https=CommandResult(0, "403 0.123000"), route_dev=route_dev))

        snapshot = collect_network_transport(runner, timeout=3, collected_at="2026-06-04T12:00:00+00:00")

        assert snapshot["ru_gov_direct_route_count"] == len(RU_GOV_TARGETS)
        assert snapshot["ru_gov_vpn_leak_count"] == 0
        assert snapshot["ru_gov_direct_route_value"] == BOOL_TRUE
        assert snapshot["route_policy_hint"] == "ru_gov_direct_ok"


def test_ru_gov_route_via_vpn_devices_counts_route_leak() -> None:
    for route_dev in ("tun0", "wg0", "sing0"):
        runner = FakeRunner(ru_gov_responses(https=CommandResult(0, "403 0.123000"), route_dev=route_dev))

        snapshot = collect_network_transport(runner, timeout=3, collected_at="2026-06-04T12:00:00+00:00")

        assert snapshot["ru_gov_vpn_leak_count"] == len(RU_GOV_TARGETS)
        assert snapshot["ru_gov_direct_route_value"] == BOOL_FALSE
        assert snapshot["ru_gov_route_leak_targets"] == list(RU_GOV_TARGETS)
        assert snapshot["route_policy_hint"] == "ru_gov_route_leak"


def test_ru_gov_external_degraded_ru_gov_reachable_direct_hint() -> None:
    mapping = ru_gov_responses(https=CommandResult(0, "403 0.123000"), route_dev="enp3s0")
    mapping["direct:https://api.github.com/rate_limit"] = CommandResult(28, "000 0.000000")
    runner = FakeRunner(mapping)

    snapshot = collect_network_transport(runner, timeout=3, collected_at="2026-06-04T12:00:00+00:00")

    assert snapshot["ru_gov_reachable_count"] == len(RU_GOV_TARGETS)
    assert snapshot["ru_gov_reachable_value"] == BOOL_TRUE
    assert snapshot["reachability_split_hint"] == "external_degraded_ru_gov_reachable"
    assert snapshot["route_policy_hint"] == "ru_gov_direct_ok"


def test_ru_gov_external_ok_ru_gov_degraded_hint() -> None:
    runner = FakeRunner(ru_gov_responses(https=CommandResult(0, "503 0.123000"), route_dev="enp3s0"))

    snapshot = collect_network_transport(runner, timeout=3, collected_at="2026-06-04T12:00:00+00:00")

    assert snapshot["ru_gov_reachable_count"] == len(RU_GOV_TARGETS)
    assert snapshot["ru_gov_reachable_value"] == BOOL_TRUE
    assert snapshot["reachability_split_hint"] == "external_ok_ru_gov_degraded"


def test_ru_gov_external_and_ru_gov_both_degraded_hint() -> None:
    mapping = ru_gov_responses(https=CommandResult(28, "000 0.000000"), route_dev="enp3s0")
    mapping["direct:https://api.github.com/rate_limit"] = CommandResult(28, "000 0.000000")
    runner = FakeRunner(mapping)

    snapshot = collect_network_transport(runner, timeout=3, collected_at="2026-06-04T12:00:00+00:00")

    assert snapshot["ru_gov_reachable_count"] == 0
    assert snapshot["ru_gov_reachable_value"] == BOOL_FALSE
    assert snapshot["reachability_split_hint"] == "global_connectivity_degraded"
