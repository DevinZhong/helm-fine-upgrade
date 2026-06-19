#!/usr/bin/env sh
set -eu

PLUGIN_DIR=${HELM_PLUGIN_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
BIN="$PLUGIN_DIR/bin/fine-upgrade"

if [ -x "$BIN" ]; then
  exec "$BIN" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$PLUGIN_DIR/src/main.py" "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$PLUGIN_DIR/src/main.py" "$@"
fi

echo "fine-upgrade binary was not found and Python is not available." >&2
echo "Run the install hook again or reinstall the plugin from GitHub Releases." >&2
exit 1
