# Repeats

| Pattern | Last seen | Known symptom | Workaround |
|---|---|---|---|
| False success output | SGTS-017 | RESULT OK after failed command | rc-gated result only |
| GitHub SSH identity mismatch | SGTS-017 | ssh auth passes, git fails | explicit GIT_SSH_COMMAND |
| Google Sheet friction | SGTS-024 | 429/rate limits and batch errors | repo-native Markdown log |
| Heredoc/paste fragility | prior ServerGuard work | shell enters > continuation | no long heredoc |
