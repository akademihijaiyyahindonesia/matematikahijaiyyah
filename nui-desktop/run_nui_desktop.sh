#!/bin/bash
# Peluncur Resmi CosmicTera NUI Desktop (macOS Native App v1.5.0 + Automatic Local Ollama LLM Engine + NUI Local Service v1.5.0)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DIR/.." && pwd)"
APP_PATH="$DIR/macos/build/CosmicTera NUI.app"
SWIFT_SRC="$DIR/macos/Sources/CosmicTeraNUIApp.swift"
APP_BIN="$APP_PATH/Contents/MacOS/CosmicTeraNUI"
PYTHON_BIN="$REPO_ROOT/.venv-mac/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="/usr/local/bin/python3"
fi

export PYTHONPATH="$REPO_ROOT/src:$DIR:${PYTHONPATH:-}"

# 1. Pastikan Ollama Local Language Engine berjalan di 127.0.0.1:11434 (tanpa duplikasi)
if command -v ollama >/dev/null 2>&1; then
  if ! lsof -i :11434 >/dev/null 2>&1; then
    nohup ollama serve >/tmp/cosmictera_ollama.log 2>&1 &
    sleep 1.0
  fi
fi

# 2. Kompilasi ulang CosmicTera NUI.app jika source Swift lebih baru dari biner
if [ -f "$SWIFT_SRC" ] && [ "$SWIFT_SRC" -nt "$APP_BIN" ]; then
  echo "[CosmicTera NUI] Mengompilasi ulang CosmicTera NUI.app v1.5.0..."
  "$PYTHON_BIN" "$DIR/macos/build_app.py"
fi

# 3. Hentikan proses aplikasi CosmicTeraNUI lama di memori macOS agar biner terbaru yang dimuat
killall CosmicTeraNUI 2>/dev/null || true

# 4. Hentikan NUI Local Service lama (termasuk PID lama di port 8848 / active_service.json) dan jalankan v1.5.0 di luar sandbox
if [ -f "$DIR/data/active_service.json" ]; then
  OLD_PID=$("$PYTHON_BIN" -c 'import json; d=json.load(open("'"$DIR/data/active_service.json"'")); print(d.get("pid", 0))' 2>/dev/null || echo 0)
  if [ "$OLD_PID" -gt 0 ] 2>/dev/null; then
    kill -TERM "$OLD_PID" 2>/dev/null || true
    sleep 0.3
  fi
fi
EXISTING_PIDS=$(lsof -ti :8848 2>/dev/null || true)
if [ -n "$EXISTING_PIDS" ]; then
  kill -TERM $EXISTING_PIDS 2>/dev/null || true
  sleep 0.4
fi

nohup env PYTHONPATH="$REPO_ROOT/src:$DIR" "$PYTHON_BIN" "$DIR/backend/server.py" --host 127.0.0.1 --port 8848 >/tmp/cosmictera_nui_service.log 2>&1 &
sleep 0.8

# 5. Segarkan LaunchServices dan buka CosmicTera NUI.app terbaru
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP_PATH" >/dev/null 2>&1 || true

open -n "$APP_PATH" || "$APP_BIN" &
echo "[CosmicTera NUI v1.5.0] Layanan lokal (127.0.0.1:8848), Browser Engine WKWebView & Local Ollama LLM aktif."
