#!/bin/bash
DIR="$(cd "$(dirname "$0")/nui-desktop" && pwd)"
exec "$DIR/run_nui_desktop.sh" "$@"
