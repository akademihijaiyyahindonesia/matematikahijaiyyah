#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/run_nui_desktop.sh" "$@"
