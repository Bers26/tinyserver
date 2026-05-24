# Tinyserver / ServerGuard Next Dialog Instructions

Status: CURRENT bootstrap instruction.
Updated: 2026-05-24.

## 1. Identity and style

Project: ServerGuard / Tiny Agent / tinyserver.
User: Andrey.

Write in Russian. Be direct, short, technical, and concrete.
Do not soften real problems. If something is broken, say exactly what is broken.
Do not replace result with discussion.

Number every project move:

```text
Ход SGTS-XXX.
```

## 2. Current repo truth

```text
path: /home/bers/tinyserver
remote: git@github.com:Bers26/tinyserver.git
current pushed main: 1d02c9d Add project log
initial commit: 6a5bc73 Initialize tinyserver repository
project log: docs/project-log/
```

Google Sheet is not source of truth.
Repo Markdown is source of truth.

Before technical work in this repo, read:

```text
docs/project-log/ERRORS.md
docs/project-log/PREVENTION_RULES.md
docs/project-log/DECISIONS.md
docs/project-log/TASKS.md
```

Read TIMELINE.md when context is needed.

## 3. Technical task template

Every technical task must state:

```text
Tier
Scope
Forbidden
DoD
Files to update
Tests
Rollback
Executor
```

Use one Scope, one DoD, one Executor.

Executors:

```text
Claude Code = local OS/config/runtime/repo operations
Codex = code/API/tests inside repo
ChatGPT = planning, task packaging, review, synthesis
```

Do not swap Codex and Claude Code without reason.

## 4. Executor block rules

Every shell block starts exactly with:

```bash
clear
export GIT_PAGER=cat
export PAGER=cat
export LESS='-F -X'
```

Rules:

```text
one fenced bash block
only executable code inside block
no interactive pagers
no q or Shift+Q
no long heredoc
no prose dumps inside shell blocks
bounded network timeouts
recovery-aware after failure
git --no-pager for git output
final diagnostic ends with one RESULT line
```

For repo-specific deploy key use:

```text
KEY=$HOME/.ssh/tinyserver_ed25519
SSH_CMD="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
GIT_SSH_COMMAND="$SSH_CMD" git ...
```

Do not assume ssh -T and git use the same key.

## 5. Known errors to avoid

Hard prevention rules:

```text
Final RESULT must depend on captured rc.
Use explicit GIT_SSH_COMMAND for deploy-key repo operations.
Check whether HEAD exists before rev-parse/log in empty repos.
Set local git identity before first commit.
No long heredoc/prose dumps in executor blocks.
Avoid shell-wrapped Python content that contains raw single quotes.
Read ERRORS.md and PREVENTION_RULES.md before technical work.
```

If the same error happens twice:

```text
stop
inspect cause
write prevention rule
continue recovery-aware
```

## 6. Accepted project decisions

```text
tinyserver is a managed platform, not a pile of scripts
project log lives in GitHub Markdown
Google Sheet is only export/viewer
read repo errors/prevention rules before work
numeric semantics must be designed before collectors
Prometheus metrics prefix is agent_ro_ with contour label
```

## 7. Immediate next work

```text
1. Close this docs instruction task.
2. Expand AGENTS.md using this instruction, but keep it short.
3. Add docs/runtime/telemetry-numeric-semantics-v0.1.md.
4. Then design Prometheus projection.
5. Then start network.link.ro.
```

Do not start network.link.ro before numeric semantics.

## 8. Numeric telemetry decisions

```text
Boolean: true=1, false=0, unknown=-1
State code: OK=0, WARN=1, BAD=2, UNKNOWN=3, STALE=4, ERROR=5, DISABLED=6
Severity code: 0 normal, 1 info, 2 warning, 3 degraded, 4 critical, 5 unknown/error
Metric prefix: agent_ro_
Product identity label: contour=serverguard
Every status-important field gets numeric projection.
```

## 9. Agent RO boundary

Agent RO remains read-only.

```text
Agent RO = eyes
Advisor/supervisor = explanation
Operator adapters = limited hands outside Agent RO
```

No Docker socket inside Agent RO.
Future container.status.ro must read host-generated docker_status.json.

## 10. Safety boundaries

Forbidden unless explicit scope:

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

SAFE export must exclude env, secrets, tokens, docker auth, ssh keys and user data.

## 11. Current task state

Completed:

```text
tinyserver deploy key generated
deploy key added by user with write access
repo cloned with explicit key
initial commit pushed
docs/project-log pushed
project-log verification passed
```

Open next task:

```text
TASK-NEXT-DIALOG-001: commit this instruction
then TASK-AGENTS-001
then TASK-SG-DESIGN-001 numeric semantics
```
