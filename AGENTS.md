# AGENTS.md

Project: tinyserver.

Read before work:

```text
docs/project-log/NEXT_DIALOG_INSTRUCTIONS.md
docs/project-log/ERRORS.md
docs/project-log/PREVENTION_RULES.md
docs/project-log/DECISIONS.md
docs/project-log/TASKS.md
```

Executor split:

```text
Claude Code = local OS/config/runtime/repo operations
Codex = code/API/tests inside repo
ChatGPT = planning, task packaging, review, synthesis
```

Claude Code specific rules are in CLAUDE.md.

Active workflow skills for Claude Code:

```text
systematic-debugging
writing-plans
vibesec
openai/yeet with project constraints
openai/gh-fix-ci after GitHub Actions exist
```

Project rules:

```text
Work from real repo state before changes.
Do not touch secrets, .env, SSH keys, deploy/runtime paths unless scope explicitly allows it.
Prefer small, verifiable changes.
Do not use long heredoc/prose dumps in executor blocks.
Before commit run git diff --check.
Keep telemetry read-only by default.
Final RESULT must depend on captured rc.
Use explicit GIT_SSH_COMMAND for repo deploy keys.
```
