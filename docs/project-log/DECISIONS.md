# Decisions

| Decision | Status | Why | Consequence |
|---|---|---|---|
| Tiny server is managed platform, not pile of scripts | accepted | Prevent repeat failures while keeping home-server scale | Use light guardrails, repo log, AGENTS.md, numeric semantics |
| Primary project log lives in GitHub Markdown | accepted | Google Sheets has rate limits and weak diff/review | docs/project-log is source of truth |
| Google Sheet is export/viewer only | accepted | External table must not replace repo truth | Update only when useful |
| Read errors and prevention rules from repo before work | accepted | Prevent repeating known mistakes | ERRORS.md and PREVENTION_RULES.md become required context |
| Numeric semantics before collectors | accepted | Avoid ad-hoc state codes | Add telemetry numeric spec before network.link.ro |
| Prometheus prefix agent_ro_ plus contour label | accepted | Dashboards should work across contours | Use contour label serverguard |
| Next-dialog instruction is stored as mono-md in repo | accepted | Future dialogs need one compact bootstrap source | Read NEXT_DIALOG_INSTRUCTIONS.md at start |
| Claude Code uses CLAUDE.md | accepted | Claude Code is a mandatory executor for local/repo/runtime work | Root CLAUDE.md becomes required context |
| Claude Code skills policy is active | accepted | systematic-debugging, writing-plans, vibesec, constrained yeet and gh-fix-ci improve reliability | Skills are recorded in CLAUDE.md and SKILLS_REGISTRY.md |
| openai/yeet is constrained by project protocol | accepted | Automated shipping must not bypass rc-gated checks or explicit SSH key | Use only if it preserves executor discipline |
| systematic-debugging is active globally in Claude Code | accepted | Recovery/debug must stop repeated blind retries | Use for failures and repeated errors |
| writing-plans is active globally in Claude Code | accepted | Multi-file tasks need short verifiable steps | Use for collector design and Codex packages |
| vibesec is active globally in Claude Code | accepted | Exporter/API/runtime boundaries need security review | Use before security-sensitive production work |
