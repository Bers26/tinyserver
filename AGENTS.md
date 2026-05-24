# AGENTS.md

Project: tinyserver.

Rules:
- Work from real repo state before changes.
- Do not touch secrets, .env, SSH keys, deploy/runtime paths unless scope explicitly allows it.
- Prefer small, verifiable changes.
- Do not use long heredoc/prose dumps in executor blocks.
- Before commit run git diff --check.
- Keep telemetry read-only by default.
