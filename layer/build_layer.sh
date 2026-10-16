#!/bin/sh
# Build the gamohud Vulkan layer and (optionally) install it for the current user.
#
#   ./build_layer.sh            # build into layer/build
#   ./build_layer.sh --install  # build and install to ~/.local/share/vulkan/implicit_layer.d
#
# Requires a C compiler and Vulkan headers (vulkan/vulkan.h + vulkan/vk_layer.h).
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BUILD_DIR="$SCRIPT_DIR/build"
mkdir -p "$BUILD_DIR"

LIB="libgamohud_layer.so"
CC="${CC:-cc}"

# Vulkan include flags.
VK_CFLAGS="$(pkg-config --cflags vulkan 2>/dev/null || true)"
if [ -z "$VK_CFLAGS" ]; then
    for d in /usr/include /usr/local/include /usr/include/x86_64-linux-gnu; do
        if [ -f "$d/vulkan/vulkan.h" ]; then
            VK_CFLAGS="-I$d"
            break
        fi
    done
fi
if [ -z "$VK_CFLAGS" ]; then
    echo "error: Vulkan headers not found. Install vulkan-headers / vulkan-loader-devel." >&2
    exit 1
fi

echo "Compiling $LIB ..."
# shellcheck disable=SC2086
"$CC" -O2 -fPIC -Wall -Wextra -std=c99 $VK_CFLAGS -shared \
    -o "$BUILD_DIR/$LIB" src/gamohud_layer.c

cp gamohud_layer.json "$BUILD_DIR/"
echo "Built: $BUILD_DIR/$LIB"

if [ "$1" = "--install" ]; then
    IMPLDIR="${XDG_DATA_HOME:-$HOME/.local/share}/vulkan/implicit_layer.d"
    mkdir -p "$IMPLDIR"
    cp "$BUILD_DIR/$LIB" "$IMPLDIR/"
    cp gamohud_layer.json "$IMPLDIR/"
    echo "Installed layer to $IMPLDIR"
fi
