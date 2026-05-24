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
| TASK-SG-DESIGN-003 | 1 | Design network.link.ro from real read-only network state | Claude Code | blocked-by-claude-limit | Needs live read-only network inspect before accepted design | wait for Claude Code or run manual read-only inspect |
