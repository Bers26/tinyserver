# Checks

| Date | Move | Check | Result | Evidence | Next |
|---|---|---|---|---|---|
| 2026-05-24 | SGTS-017 | ssh -T with explicit key | PASS | Authenticated as Bers26/tinyserver | Use same key for git |
| 2026-05-24 | SGTS-017 | git without explicit key | FAIL | Permission denied publickey | Set GIT_SSH_COMMAND/core.sshCommand |
| 2026-05-24 | SGTS-018 | git ls-remote with explicit key | PASS | LS_REMOTE_RC=0 | Clone |
| 2026-05-24 | SGTS-023 | dry-run push | PASS | DRY_PUSH_RC=0 | Real push |
| 2026-05-24 | SGTS-044 | systematic-debugging skill | PASS | installed active global under ~/.claude/skills/ | use for recovery/debug |
| 2026-05-24 | SGTS-044 | writing-plans skill | PASS | installed active global under ~/.claude/skills/ | use for multi-step planning |
| 2026-05-24 | SGTS-044 | vibesec skill | PASS | installed active global under ~/.claude/skills/ | use before security-sensitive production work |
| 2026-05-25 | SGTS-090 | network.link.ro CLI smoke | PASS | PYTHONPATH=src CLI returned state=OK, severity=normal, interface=enp6s0 | framework wrapper |
| 2026-05-25 | SGTS-101 | network.link.ro framework wrapper tests | PASS | pytest collected 22 items, all passed; branch pushed for PR #14 | merge/runtime proof |
| 2026-05-25 | SGTS-113 | ServerGuard full registry consumer proof | PASS | consumer saw network.link.ro, power.status.ro, serverguard.server.ro | checks dict consumer |
| 2026-05-25 | SGTS-121 | PR #15 transient ping classification validation | PASS | 24 tests passed; soft case WARN/degraded, hard case BAD/critical | merge PR #15 |
| 2026-05-25 | SGTS-124 | PR #15 live runtime smoke | PASS | run-network-link-ro.sh OK; consumer saw 3 agents, network.link.ro OK/fresh | checks dict |
| 2026-05-25 | SGTS-127 | ServerGuard PR #5 checks dict validation | PASS | 9 tests passed; targeted checks dict proof OK | merge PR #5 |
| 2026-05-25 | SGTS-129 | ServerGuard checks dict live sync | PASS | live consumer preserved checks as dict; app/api/maid.py untouched | network producer checks |
| 2026-05-25 | SGTS-132 | tinyserver PR #16 checks dict validation | PASS | 4 focused tests passed; CHECKS_KEYS_AND_SHAPE_OK | merge PR #16 |
| 2026-05-25 | SGTS-134 | network.link.ro checks dict live smoke | PASS | latest and ServerGuard consumer show link/gateway_ping/dns/vpn_hint/interface_counters checks | Prometheus exporter |
| 2026-05-25 | SGTS-139 | PR #17 Prometheus projection validation | PASS | 3 tests passed; compile OK; fixture and live registry CLI proof OK | merge PR #17 |
| 2026-05-25 | SGTS-141 | Prometheus projection live sync | PASS | main contains 78db512; CLI emits metrics for serverguard.server, power.status, network.link | storage.status.ro |
