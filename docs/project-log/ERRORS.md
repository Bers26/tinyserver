# Errors

| ID | Move | Mistake | Cause | Impact | Fix | Prevention |
|---|---|---|---|---|---|---|
| E-SGTS-017 | SGTS-017 | Printed OK after failed ls-remote/clone | Final RESULT ignored command failures | Misleading operator state | Recovery block with explicit key | Final RESULT must depend on captured rc |
| E-SGTS-017B | SGTS-017 | git commands did not use deploy key | ssh -T used -i but git did not | Repo clone failed | Use GIT_SSH_COMMAND/core.sshCommand | Repo deploy keys require explicit SSH command or ssh config |
| E-SGTS-018 | SGTS-018 | Ran HEAD command in empty repo | Empty repo has no commit | fatal Needed a single revision | Treat empty repo as valid pre-init state | Check HEAD exists before rev-parse/log |
| E-SGTS-019 | SGTS-019 | Commit failed due missing git identity | New repo lacked local user.name/email | Initial commit blocked | Set local repo identity | Configure local identity before first commit |
| E-SGTS-021 | SGTS-021 | Google Sheet not updated after result | Logging treated as optional | Project trace lagged | Move primary log to repo | Operational log must be updated in repo |
| E-SGTS-022 | SGTS-022 | Google Sheet batch failed on invalid sheet index | Tried reindex before sheets existed | Logging update failed | Stop relying on Sheets | Create structure in repo markdown |
| E-HEREDOC | prior | Long heredoc/prose blocks caused shell continuation prompts | Fragile paste workflow | Interrupted sessions | Avoid long heredoc | Use small files, repo patches, or bounded scripts |
