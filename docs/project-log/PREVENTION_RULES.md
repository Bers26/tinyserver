# Prevention Rules

| Rule | Status | Applies to | Why |
|---|---|---|---|
| Final RESULT must depend on captured rc | active | all executor blocks | Prevent false OK |
| Use explicit GIT_SSH_COMMAND for repo deploy keys | active | GitHub repo operations | ssh -T and git may use different identities |
| Check whether HEAD exists before rev-parse/log | active | empty repos | Empty repo has no revision |
| Set local git identity before first commit | active | new repos | Avoid global config changes and commit failure |
| No long heredoc/prose dumps in executor blocks | active | SSH executor | Prevent shell continuation prompt and broken paste |
| Read ERRORS.md and PREVENTION_RULES.md before technical work | active | ServerGuard/Tiny Server | Avoid repeated mistakes |
| Avoid shell-wrapped Python content that contains raw single quotes | active | generated docs in executor blocks | Prevent unterminated string failures |
