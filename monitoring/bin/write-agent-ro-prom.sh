#!/usr/bin/env bash
set -u

ROOT="/opt/serverguard-monitoring"
REGISTRY="/opt/serverguard-local/agent-ro/registries/agent-ro-full.json"
TINY="/home/bers/tinyserver"
OUT_DIR="$ROOT/textfile"
TMP="$OUT_DIR/agent_ro.prom.tmp"
OUT="$OUT_DIR/agent_ro.prom"

mkdir -p "$OUT_DIR"
cd "$TINY" || exit 2
PYTHONPATH=src python3 -m tinyserver_collectors.prometheus_cli --registry "$REGISTRY" > "$TMP" || exit 3
mv "$TMP" "$OUT" || exit 4
