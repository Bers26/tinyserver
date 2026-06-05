# CLAUDE.md

Status: CURRENT Claude Code instruction for tinyserver.
Updated: 2026-05-24.

## 1. Mandatory context before work

Claude Code must read these files before any technical task in this repo:

```text
docs/project-log/NEXT_DIALOG_INSTRUCTIONS.md
docs/project-log/ERRORS.md
docs/project-log/PREVENTION_RULES.md
docs/project-log/DECISIONS.md
docs/project-log/TASKS.md
```

Read TIMELINE.md when task history matters.

## 2. Executor role

Claude Code is used for local OS, config, runtime and repo operations.
Codex is used for code, API and tests inside repo.
Do not swap executors without a concrete reason.

## 3. Required Claude Code skill policy

Use these skills or their workflow principles when available in Claude Code.

```text
systematic-debugging
URL: https://github.com/obra/superpowers/tree/main/skills
Status: ACTIVE
Use for: recovery, repeated failures, unclear root cause, broken tests, runtime drift.
Rule: after the same error twice, stop, inspect cause, add prevention rule, continue recovery-aware.

writing-plans
URL: https://github.com/obra/superpowers/tree/main/skills
Status: ACTIVE
Use for: tasks touching more than one file, multi-step patches, collector design, Codex packages.
Rule: split work into short verifiable steps with exact paths and acceptance criteria.

vibesec
URL: https://github.com/BehiSecc/awesome-claude-skills
Status: ACTIVE for security-sensitive review
Use for: exporter, API, auth, secrets, Docker/runtime boundary, operator adapters, external exposure.
Rule: run before Prometheus exporter goes production and before any action-capable layer.

openai/yeet
URL: https://github.com/openai/skills
Status: ACTIVE WITH PROJECT CONSTRAINTS
Use for: standardizing add/commit/push/PR workflow only if it respects this repo protocol.
Rule: do not bypass rc-gated checks, explicit deploy key, diff check, recovery-aware result, or task separation.

openai/gh-fix-ci
URL: https://github.com/openai/skills
Status: ACTIVE AFTER GITHUB ACTIONS EXIST
Use for: reading failing GitHub Actions logs and proposing fixes.
Rule: no CI-fix automation until Actions are added and failure logs exist.
```

If a skill is unavailable locally, apply the workflow principle and record that the skill was not directly available.

## 4. Hard executor rules

Every shell block starts with:

```bash
clear
export GIT_PAGER=cat
export PAGER=cat
export LESS='-F -X'
```

Rules:

```text
one fenced bash block
only executable code
no long heredoc
no prose dumps in shell blocks
no interactive pagers
bounded network timeouts
git --no-pager
final RESULT must depend on captured rc
```

Use repo deploy key explicitly:

```text
KEY=$HOME/.ssh/tinyserver_ed25519
SSH_CMD="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
GIT_SSH_COMMAND="$SSH_CMD" git ...
```

## 5. Safety boundaries

Forbidden without explicit scope:

```text
secrets
.env
SSH keys
Docker runtime
VPN
DHCP
deploy
/srv/storage user data
history rewrite
```

## 6. Current repo state and next work

Current repo state:

```text
path: /home/bers/tinyserver
branch: main
HEAD: 8f7a9c4
upstream: origin/main
upstream HEAD: 8f7a9c4
Agent RO collector set: serverguard.server.ro, power.status.ro, network.link.ro, network.transport.ro, storage.status.ro, service.health.ro, interaction.channels.ro
recent targeted pytest: 43 passed in 0.09s
old project-log entries before SGTS-134 are historical, not next-task truth
```

Current next useful work:

```text
Keep handoff docs synchronized with current code state.
Design network.performance.ro / VPN performance only after source/reality hygiene.
interaction.channels.ro triage should happen in ServerGuard/live context.
BB-UX-001 deterministic simple-language fallback is ServerGuard-side, not tinyserver collector code unless a FactPack contract change is scoped.
Do not restart old storage.status.ro queued task.
```
