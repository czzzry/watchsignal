#!/usr/bin/env sh
set -eu

VERSION="v2.0.0"
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$ARCH" in
  x86_64)
    ARCH="amd64"
    ;;
  arm64|aarch64)
    ARCH="arm64"
    ;;
  *)
    echo "Unsupported architecture: $ARCH" >&2
    exit 1
    ;;
esac

case "$OS" in
  darwin|linux)
    ;;
  *)
    echo "Unsupported operating system: $OS" >&2
    exit 1
    ;;
esac

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DOWNLOAD_DIR="$ROOT_DIR/.tools/downloads"
BIN_DIR="$ROOT_DIR/.tools/bin"
ASSET="treehouse-${VERSION}-${OS}-${ARCH}.tar.gz"
BASE_URL="https://github.com/kunchenguid/treehouse/releases/download/${VERSION}"

mkdir -p "$DOWNLOAD_DIR" "$BIN_DIR"

curl -L -o "$DOWNLOAD_DIR/$ASSET" "$BASE_URL/$ASSET"
curl -L -o "$DOWNLOAD_DIR/treehouse-checksums.txt" "$BASE_URL/checksums.txt"

EXPECTED="$(grep "  $ASSET" "$DOWNLOAD_DIR/treehouse-checksums.txt" | awk '{print $1}')"
ACTUAL="$(shasum -a 256 "$DOWNLOAD_DIR/$ASSET" | awk '{print $1}')"

if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "Checksum mismatch for $ASSET" >&2
  exit 1
fi

tar -xzf "$DOWNLOAD_DIR/$ASSET" -C "$BIN_DIR"
chmod +x "$BIN_DIR/treehouse"

"$BIN_DIR/treehouse" --version
