"""Framework-compatible snapshot wrapper for network.transport.ro."""

from __future__ import annotations

import json
from typing import Any

from tinyserver_collectors.network_transport_cli import collect_with_default_runner

TTL_SEC = 300
RULESET_VERSION = "1.0"


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _contract_severity(value: Any, default: int = 4) -> int:
    severity = _int_value(value, default)
    if severity < 0:
        return 0
    if severity > 4:
        return 4
    return severity


def _metric_subset(raw: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "direct_github_api_ok_value",
        "socks_github_api_ok_value",
        "direct_gstatic_ok_value",
        "socks_gstatic_ok_value",
        "dns_telegram_ok_value",
        "tcp_telegram_443_ok_value",
        "direct_telegram_api_ok_value",
        "socks_telegram_api_ok_value",
        "socks_port_alive_value",
        "direct_github_http_code",
        "socks_github_http_code",
        "direct_gstatic_http_code",
        "socks_gstatic_http_code",
        "direct_github_time_ms",
        "socks_github_time_ms",
        "direct_gstatic_time_ms",
        "socks_gstatic_time_ms",
        "direct_telegram_http_code",
        "socks_telegram_http_code",
        "direct_telegram_time_ms",
        "socks_telegram_time_ms",
        "transport_success_count",
        "transport_checked_count",
        "ru_gov_checked_count",
        "ru_gov_reachable_count",
        "ru_gov_success_rate",
        "ru_gov_direct_route_count",
        "ru_gov_vpn_leak_count",
        "ru_gov_reachable_value",
        "ru_gov_direct_route_value",
        "freshness_code",
        "operation_state_code",
    ]
    return {key: raw.get(key) for key in keys if key in raw}


def _check(
    *,
    state: str,
    severity: int,
    confidence: str,
    summary: str,
    rule_id: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "state": state,
        "severity": _contract_severity(severity),
        "confidence": confidence,
        "summary": summary,
        "rule_id": rule_id,
        "ruleset_version": RULESET_VERSION,
        "evidence": evidence,
    }


def _evidence(raw: dict[str, Any], *, observed_value: str) -> dict[str, Any]:
    return {
        "source": "curl",
        "source_type": "command",
        "command_class": "read_only",
        "observed_value": observed_value,
        "collected_at": str(raw.get("collected_at") or ""),
    }


def _target_check(raw: dict[str, Any], *, check_id: str, direct_key: str, socks_key: str, direct_code: str, socks_code: str) -> dict[str, Any]:
    direct = _int_value(raw.get(f"{direct_key}_value"), -1)
    socks = _int_value(raw.get(f"{socks_key}_value"), -1)
    if direct == 1 or socks == 1:
        state, severity, confidence = "OK", 0, "high"
        summary = f"{check_id} reachable."
    elif direct == -1 and socks == -1:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = f"{check_id} was not checked."
    else:
        state, severity, confidence = "BAD", 4, "high"
        summary = f"{check_id} unreachable over direct and SOCKS paths."
    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id=f"network.transport.{check_id}",
        evidence=_evidence(
            raw,
            observed_value=(
                f"direct_ok={direct} socks_ok={socks} "
                f"direct_http_code={raw.get(direct_code)} socks_http_code={raw.get(socks_code)}"
            ),
        ),
    )


def _socks_proxy_check(raw: dict[str, Any]) -> dict[str, Any]:
    alive = _int_value(raw.get("socks_port_alive_value"), -1)
    if alive == 1:
        state, severity, confidence = "OK", 0, "medium"
        summary = "SOCKS proxy path produced HTTP probe output."
    elif alive == 0:
        state, severity, confidence = "WARN", 3, "medium"
        summary = "SOCKS proxy path did not produce HTTP probe output."
    else:
        state, severity, confidence = "UNKNOWN", 5, "low"
        summary = "SOCKS proxy path state unknown."
    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.transport.socks_proxy",
        evidence=_evidence(
            raw,
            observed_value=(
                f"socks_port_alive={alive} socks_github_code={raw.get('socks_github_http_code')} "
                f"socks_gstatic_code={raw.get('socks_gstatic_http_code')}"
            ),
        ),
    )


def _transport_path_check(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    severity = _contract_severity(raw.get("severity_code"), 4)
    success = _int_value(raw.get("transport_success_count"), 0)
    checked = _int_value(raw.get("transport_checked_count"), 0)
    return _check(
        state=state if state in {"OK", "WARN", "BAD", "UNKNOWN"} else "UNKNOWN",
        severity=severity,
        confidence="high" if checked > 0 else "medium",
        summary=f"Transport paths: {success}/{checked} probes succeeded.",
        rule_id="network.transport.path",
        evidence=_evidence(raw, observed_value=f"success={success} checked={checked} hint={raw.get('transport_hint')}"),
    )



def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _ru_gov_reachability_check(raw: dict[str, Any]) -> dict[str, Any]:
    checked = _int_value(raw.get("ru_gov_checked_count"), 0)
    reachable = _int_value(raw.get("ru_gov_reachable_count"), 0)
    reachable_value = _int_value(raw.get("ru_gov_reachable_value"), -1)
    failed_targets = _list_value(raw.get("ru_gov_failed_targets"))

    if checked <= 0 or reachable_value == -1:
        state, severity, confidence = "UNKNOWN", 5, "low"
        summary = "RU/gov direct reachability was not checked."
    elif reachable_value == 1:
        state, severity, confidence = "OK", 0, "high"
        summary = f"RU/gov direct reachability OK: {reachable}/{checked} targets reachable."
    else:
        state, severity, confidence = "WARN", 3, "high"
        summary = f"RU/gov direct reachability degraded: {reachable}/{checked} targets reachable."

    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.transport.ru_gov_reachability",
        evidence=_evidence(
            raw,
            observed_value=(
                f"reachable={reachable} checked={checked} failed_targets={failed_targets} "
                f"split={raw.get('reachability_split_hint')}"
            ),
        ),
    )


def _ru_gov_route_policy_check(raw: dict[str, Any]) -> dict[str, Any]:
    checked = _int_value(raw.get("ru_gov_checked_count"), 0)
    direct = _int_value(raw.get("ru_gov_direct_route_count"), 0)
    leaks = _int_value(raw.get("ru_gov_vpn_leak_count"), 0)
    route_value = _int_value(raw.get("ru_gov_direct_route_value"), -1)
    leak_targets = _list_value(raw.get("ru_gov_route_leak_targets"))

    if checked <= 0 or route_value == -1:
        state, severity, confidence = "UNKNOWN", 5, "medium"
        summary = "RU/gov direct route policy evidence is unknown."
    elif leaks > 0:
        state, severity, confidence = "BAD", 4, "high"
        summary = f"RU/gov route leak detected: {leaks}/{checked} targets appear routed via VPN-like interfaces."
    elif route_value == 1:
        state, severity, confidence = "OK", 0, "high"
        summary = f"RU/gov direct route policy OK: {direct}/{checked} targets use direct-like routes."
    else:
        state, severity, confidence = "WARN", 3, "medium"
        summary = f"RU/gov direct route policy incomplete: {direct}/{checked} targets use direct-like routes."

    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.transport.ru_gov_route_policy",
        evidence=_evidence(
            raw,
            observed_value=(
                f"direct={direct} checked={checked} vpn_leaks={leaks} "
                f"leak_targets={leak_targets} route_policy={raw.get('route_policy_hint')}"
            ),
        ),
    )


def _reachability_split_check(raw: dict[str, Any]) -> dict[str, Any]:
    hint = str(raw.get("reachability_split_hint") or "unknown")
    if hint == "external_and_ru_gov_ok":
        state, severity, confidence = "OK", 0, "high"
        summary = "External and RU/gov reachability are both OK."
    elif hint in {"no_evidence", "unknown"}:
        state, severity, confidence = "UNKNOWN", 5, "low"
        summary = f"Reachability split evidence is {hint}."
    else:
        state, severity, confidence = "WARN", 3, "medium"
        summary = f"Reachability split hint: {hint}."

    return _check(
        state=state,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rule_id="network.transport.reachability_split",
        evidence=_evidence(raw, observed_value=f"reachability_split_hint={hint}"),
    )


def _checks(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "github_api": _target_check(
            raw,
            check_id="github_api",
            direct_key="direct_github_api_ok",
            socks_key="socks_github_api_ok",
            direct_code="direct_github_http_code",
            socks_code="socks_github_http_code",
        ),
        "gstatic": _target_check(
            raw,
            check_id="gstatic",
            direct_key="direct_gstatic_ok",
            socks_key="socks_gstatic_ok",
            direct_code="direct_gstatic_http_code",
            socks_code="socks_gstatic_http_code",
        ),
        "telegram_api": _target_check(
            raw,
            check_id="telegram_api",
            direct_key="direct_telegram_api_ok",
            socks_key="socks_telegram_api_ok",
            direct_code="direct_telegram_http_code",
            socks_code="socks_telegram_http_code",
        ),
        "socks_proxy": _socks_proxy_check(raw),
        "transport_path": _transport_path_check(raw),
        "ru_gov_reachability": _ru_gov_reachability_check(raw),
        "ru_gov_route_policy": _ru_gov_route_policy_check(raw),
        "reachability_split": _reachability_split_check(raw),
    }


def _summary(raw: dict[str, Any]) -> str:
    state = str(raw.get("state") or "UNKNOWN").upper()
    success = raw.get("transport_success_count")
    checked = raw.get("transport_checked_count")
    return f"Network transport {state}: {success}/{checked} probes succeeded."


def to_framework_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    state = str(raw.get("state") or "UNKNOWN").upper()
    if state not in {"OK", "WARN", "BAD", "UNKNOWN"}:
        state = "UNKNOWN"
    severity = _contract_severity(raw.get("severity_code"), 4)
    return {
        "schema_version": "1.0",
        "agent_id": "network.transport.ro",
        "product": "Tiny Agent Framework",
        "domain": "network",
        "display_name": "Network Transport RO",
        "version": "0.1",
        "collected_at": str(raw.get("collected_at") or ""),
        "ttl_sec": TTL_SEC,
        "state": state,
        "severity": severity,
        "summary": _summary(raw),
        "checks": _checks(raw),
        "metrics": _metric_subset(raw),
        "links": [],
        "capabilities": {"read_only": True, "actions": []},
    }


def collect(output_root: object | None = None) -> dict[str, Any]:
    raw = collect_with_default_runner()
    return to_framework_snapshot(raw)


def main() -> int:
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
