"""CLI for Agent RO Prometheus text projection."""

from __future__ import annotations

import argparse
from pathlib import Path

from tinyserver_collectors.prometheus_projection import render_prometheus_from_registry

DEFAULT_REGISTRY = Path("/opt/serverguard-local/agent-ro/registries/agent-ro-full.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Agent RO latest snapshots as Prometheus text metrics.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Path to Agent RO registry JSON.")
    parser.add_argument("--contour", default="serverguard", help="Stable contour label value.")
    args = parser.parse_args()

    print(render_prometheus_from_registry(args.registry, contour=args.contour), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
