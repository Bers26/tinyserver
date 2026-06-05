# Tasks

| Task | Tier | Scope | Executor | Status | DoD | Next |
|---|---:|---|---|---|---|---|
| TASK-TINY-KEY-001 | 1 | Generate deploy key for tinyserver | Claude Code | done | Key generated and added to GitHub | none |
| TASK-TINY-CLONE-001 | 1 | Verify repo SSH access and clone | Claude Code | closed-with-error | Failed without explicit key | superseded |
| TASK-TINY-CLONE-002 | 1 | Clone using explicit deploy key | Claude Code | done | Repo cloned | initial commit |
| TASK-TINY-INIT-001 | 1 | Create and push initial commit | Claude Code | done | Commit 6a5bc73 pushed to origin/main | none |
| TASK-PROJECT-LOG-001 | 1 | Add repo-native project log | Claude Code | done | docs/project-log committed and pushed in 1d02c9d | maintain before work |
| TASK-NEXT-DIALOG-001 | 1 | Add mono instruction for next dialogs | Claude Code | done | NEXT_DIALOG_INSTRUCTIONS.md committed and pushed in 93ea63b | none |
| TASK-AGENTS-001 | 1 | Add CLAUDE.md and Claude Code skills policy | Claude Code | done | CLAUDE.md/AGENTS.md pushed; systematic-debugging, writing-plans and vibesec installed active globally | numeric semantics |
| TASK-SKILLS-INSTALL-001 | 1 | Install required Claude Code skills | Claude Code | done | systematic-debugging, writing-plans and vibesec installed active globally | none |
| TASK-TINYSERVER-MVP-000A | 1 | Create Tinyserver MVP workpack | GitHub connector | done | docs/workpacks/TASK-TINYSERVER-MVP-000 merged in 7671f93 | numeric semantics adoption |
| TASK-SG-DESIGN-001A | 1 | Add canonical numeric semantics to tiny-agent-framework | GitHub connector | done | docs/runtime/telemetry-numeric-semantics-v0.1.md merged in 50e9654 | tinyserver adoption |
| TASK-SG-DESIGN-001B | 1 | Adopt canonical numeric semantics in tinyserver | GitHub connector | done | docs/runtime/telemetry-numeric-semantics.md merged in 98d14c3 | Prometheus projection |
| TASK-SG-DESIGN-002 | 1 | Add Prometheus projection spec in tinyserver | GitHub connector | done | docs/runtime/prometheus-projection.md merged in eaccd47 | network.link design |
| TASK-SG-DESIGN-003A | 1 | Add network.link.ro draft design skeleton | GitHub connector | done | docs/collectors/network-link.md merged in 2ee0cbd | factual inspect |
| TASK-SG-DESIGN-003B | 1 | Accept network.link.ro design from factual state | GitHub connector | done | docs/collectors/network-link.md merged in 13342cc | Codex collector package |
| TASK-SG-CODEX-001A | 2 | Implement network.link.ro pure snapshot logic and tests | GitHub connector fallback | done | pure logic and tests merged in af5e59f | live runner |
| TASK-SG-CODEX-001B | 2 | Implement network.link.ro live read-only runner | GitHub connector fallback | done | live helper layer merged in 7f7f468 | default runner |
| TASK-SG-CODEX-001C | 2 | Add network.link.ro bounded default runner CLI | GitHub connector fallback | done | CLI/default runner merged in 9dd49c0; server smoke PASS | framework wrapper |
| TASK-SG-CODEX-001D | 2 | Add network.link.ro framework snapshot wrapper | Claude Code + GitHub PR | done | PR #14 merged in 262c2d; framework wrapper tests PASS | runtime proof |
| TASK-SG-CODEX-001E | 2 | Soften transient gateway ping loss classification | GitHub connector + Claude Code validation | done | PR #15 merged in b492b2e; transient ICMP loss with DNS alive is WARN/degraded | checks dict |
| TASK-SG-CODEX-001F | 2 | Add network.link.ro checks dict | GitHub connector + Claude Code validation | done | PR #16 merged in 32c8a38; live latest and ServerGuard consumer show keyed checks dict | Prometheus exporter |
| TASK-SG-RUNTIME-001 | 2 | Wire network.link.ro into Agent RO runtime | Claude Code | done | latest/history/registry/consumer proof PASS; network.link.ro visible as fresh read-only agent | Prometheus exporter |
| TASK-SG-CONSUMER-001 | 2 | Prefer full Agent RO registry in ServerGuard consumer | GitHub connector + Claude Code validation | done | ServerGuard PR #4 merged and live; consumer reads registries/agent-ro-full.json primary | checks dict consumer |
| TASK-SG-CONSUMER-002 | 2 | Preserve Agent RO checks dict in ServerGuard consumer | GitHub connector + Claude Code validation | done | ServerGuard PR #5 merged and live; checks dict preserved through consumer | Prometheus exporter |
| TASK-SG-PROM-001 | 2 | Implement registry-driven Prometheus text projection MVP | GitHub connector + Claude Code validation | done | PR #17 merged in 78db512; tests pass; live CLI emits Agent RO metrics for serverguard.server, power.status, network.link | storage.status.ro |
| TASK-SG-CODEX-002 | 2 | Implement storage.status.ro collector | Codex/GitHub connector + Claude Code validation | historical-stale | Old queued entry; superseded by 2026-06-05 compact sync where storage.status.ro is marked done | see compact sync section |

## 2026-06-05 compact sync / completed after SGTS-134

Completed after the old SGTS-134 handoff context:

| Task | Tier | Scope | Executor | Status | DoD | Next |
|---|---:|---|---|---|---|---|
| TASK-SG-CODEX-002 | 2 | storage.status.ro collector | Codex/GitHub connector + Claude Code validation | done | Read-only storage latest/checks/metrics implemented after old queued entry | maintain docs |
| TASK-SG-CODEX-003 | 2 | service.health.ro collector | Codex/GitHub connector + Claude Code validation | done | Service health read-only collector implemented | maintain docs |
| TASK-SG-CODEX-004 | 2 | power.status.ro UPS diagnostic evidence | Codex/GitHub connector + Claude Code validation | done | UPS diagnostic evidence added to Power RO | maintain docs |
| TASK-SG-CODEX-005 | 2 | interaction.channels.ro collector and framework exposure | Codex/GitHub connector + Claude Code validation | done | Interaction channels implemented, normalized, and exposed through framework pattern | ServerGuard/live triage if needed |
| TASK-SG-CODEX-006 | 2 | network.transport.ro collector | Codex/GitHub connector + Claude Code validation | done | Network transport collector implemented | maintain docs |
| TASK-SG-CODEX-007 | 2 | network.transport.ro RU/gov route evidence | Codex/GitHub connector + Claude Code validation | done | RU/gov direct route evidence added | maintain docs |
| TASK-SG-CODEX-008 | 2 | network.transport.ro framework exposure | Codex/GitHub connector + Claude Code validation | done | Framework snapshot exposes network transport evidence | maintain docs |
| TASK-SG-RUNTIME-002 | 2 | network.transport.ro live registry visibility | Claude Code validation | done | Live Agent RO full registry includes network.transport.ro | ServerGuard reality docs |
| TASK-SG-CODEX-009 | 2 | network.link.ro gateway_icmp_loss wording fix | Codex/GitHub connector + Claude Code validation | done | Summary wording uses gateway_icmp_loss instead of ambiguous bare loss | maintain docs |

Current next candidates, queued/deferred rather than active commands:

| Task | Tier | Scope | Executor | Status | DoD | Next |
|---|---:|---|---|---|---|---|
| TASK-TINY-DOCS-001 | 1 | Keep handoff docs/current task state synchronized | Codex or Claude Code | queued | Handoff docs match current HEAD/upstream and completed collector state | verify before edit |
| TASK-TINY-NETPERF-001 | 1 | Design network.performance.ro read-only collector | Codex/GitHub connector | deferred | Design matches existing collector/framework/CLI/test pattern | source hygiene first |
| TASK-TINY-VPNPERF-001 | 1 | Design VPN node ping/top-3/speed measurement read-only collector | Codex/GitHub connector | deferred | Read-only VPN node performance design without runtime changes | source hygiene first |
| TASK-TINY-DIAG-001 | 1 | Diagnostic enrichment pattern across thin agents | Codex/GitHub connector | deferred | Reusable diagnostic enrichment pattern documented before broad collector edits | source hygiene first |
