# Skills Registry

| Skill/tool | Status | Why | Apply where | Risk | Rule |
|---|---|---|---|---|---|
| AGENTS.md | active | Machine-readable repo rules | all coding agents | can go stale | keep short and current |
| CLAUDE.md | active | Claude Code needs dedicated local/repo/runtime instruction | Claude Code tasks | can diverge from AGENTS.md | keep aligned with AGENTS.md |
| systematic-debugging | active | Repeated errors are already in project log | recovery/debug | can over-bureaucratize | use on failure, repeated failure, unclear cause |
| writing-plans | active | Prevent large vague patches and stuck Codex runs | multi-file tasks, collector design, Codex packages | can slow trivial edits | use when task has more than one file or step |
| vibesec | active for security-sensitive review | DRIFT-001, Docker socket, exposed services and future exporters need security review | exporter, API, auth, Docker boundary, operator adapters | may be web-app focused | run before production security-sensitive code |
| openai/yeet | active with project constraints | Standardizes repeated git add/commit/push/PR flow | repo shipping workflow | may bypass local protocol if used blindly | only if rc-gated checks and explicit key are preserved |
| openai/gh-fix-ci | active after GitHub Actions exist | Reads CI failures and helps repair | future CI failures | useless before Actions exist | enable after tests run in GitHub Actions |
