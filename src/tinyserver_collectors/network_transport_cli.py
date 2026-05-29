"""Executable read-only CLI wrapper for network.transport.ro."""

from __future__ import annotations

import json
import subprocess
from typing import Sequence

from tinyserver_collectors.network_transport import CommandResult, collect_network_transport


def default_command_runner(args: Sequence[str], timeout: int | float) -> CommandResult:
    """Run one bounded read-only command and normalize the result."""
    try:
        completed = subprocess.run(
            list(args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, exc.stdout or "", exc.stderr or "timeout")
    except OSError as exc:
        return CommandResult(127, "", str(exc))
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def collect_with_default_runner(timeout: int | float = 7) -> dict:
    """Collect network.transport.ro using the bounded default command runner."""
    return collect_network_transport(command_runner=default_command_runner, timeout=timeout)


def main() -> int:
    snapshot = collect_with_default_runner()
    print(json.dumps(snapshot, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
