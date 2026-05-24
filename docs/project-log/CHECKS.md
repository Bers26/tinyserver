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
