"""Executable read-only CLI wrapper for interaction.channels.ro."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tinyserver_collectors.interaction_channels import (
    DEFAULT_BIG_UI_URL,
    ProbeResult,
    collect_interaction_channels,
)
from tinyserver_collectors.interaction_channels_framework import to_framework_snapshot


def default_http_probe(url: str, timeout: int | float) -> ProbeResult:
    """Run a bounded local HTTP GET and normalize the result."""
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = int(response.status)
            return ProbeResult(ok=200 <= status_code < 400, status_code=status_code)
    except HTTPError as exc:
        return ProbeResult(ok=False, status_code=int(exc.code), detail="http_error")
    except (OSError, URLError) as exc:
        return ProbeResult(ok=False, status_code=None, detail=type(exc).__name__)


def collect_with_default_probe(timeout: int | float = 3) -> dict:
    """Collect interaction.channels.ro using only bounded local probing."""
    return collect_interaction_channels(
        big_ui_probe=default_http_probe,
        big_ui_url=DEFAULT_BIG_UI_URL,
        timeout=timeout,
    )


def main() -> int:
    snapshot = to_framework_snapshot(collect_with_default_probe())
    print(json.dumps(snapshot, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
