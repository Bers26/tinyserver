"""Executable read-only CLI wrapper for interaction.channels.ro."""

from __future__ import annotations

import json

from tinyserver_collectors.interaction_channels import (
    DEFAULT_BIG_UI_URL,
    collect_interaction_channels,
    default_http_probe,
)
from tinyserver_collectors.interaction_channels_framework import to_framework_snapshot


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
