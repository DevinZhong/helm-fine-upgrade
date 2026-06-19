#!/usr/bin/env sh
set -eu

PLUGIN_DIR=${HELM_PLUGIN_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}

if [ "${HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL:-}" = "1" ]; then
  echo "Skipping fine-upgrade binary download because HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1"
  exit 0
fi

VERSION=${HELM_FINE_UPGRADE_BINARY_VERSION:-}
if [ -z "$VERSION" ]; then
  VERSION=$(awk -F"'" '/^version:/ { print $2; exit }' "$PLUGIN_DIR/plugin.yaml")
fi
TAG="v$VERSION"

OS=$(uname -s)
ARCH=$(uname -m)

case "$OS" in
  Linux) OS_NAME=linux ;;
  Darwin) OS_NAME=darwin ;;
  *)
    echo "Unsupported operating system for binary install: $OS" >&2
    echo "Set HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 to use source mode." >&2
    exit 1
    ;;
esac

case "$ARCH" in
  x86_64|amd64) ARCH_NAME=amd64 ;;
  arm64|aarch64) ARCH_NAME=arm64 ;;
  *)
    echo "Unsupported CPU architecture for binary install: $ARCH" >&2
    echo "Set HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 to use source mode." >&2
    exit 1
    ;;
esac

ASSET="${OS_NAME}-${ARCH_NAME}"
if [ "$ASSET" = "linux-arm64" ]; then
  echo "No linux-arm64 binary package is published yet." >&2
  echo "Set HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 to use source mode." >&2
  exit 1
fi

URL="https://github.com/DevinZhong/helm-fine-upgrade/releases/download/${TAG}/helm-fine-upgrade-${TAG}-${ASSET}.tar.gz"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

ARCHIVE="$TMP_DIR/package.tar.gz"
echo "Downloading fine-upgrade ${TAG} binary package for ${ASSET}"

if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" -o "$ARCHIVE"
elif command -v wget >/dev/null 2>&1; then
  wget -q "$URL" -O "$ARCHIVE"
else
  echo "curl or wget is required to download the binary package." >&2
  echo "Set HELM_FINE_UPGRADE_SKIP_BINARY_INSTALL=1 to use source mode." >&2
  exit 1
fi

tar -xzf "$ARCHIVE" -C "$TMP_DIR"
PACKAGE_DIR="$TMP_DIR/helm-fine-upgrade-${TAG}-${ASSET}"

if [ ! -x "$PACKAGE_DIR/bin/fine-upgrade" ]; then
  echo "Downloaded package does not contain bin/fine-upgrade." >&2
  exit 1
fi

mkdir -p "$PLUGIN_DIR/bin"
cp "$PACKAGE_DIR/bin/fine-upgrade" "$PLUGIN_DIR/bin/fine-upgrade"
chmod +x "$PLUGIN_DIR/bin/fine-upgrade"

echo "Installed fine-upgrade binary: $PLUGIN_DIR/bin/fine-upgrade"
