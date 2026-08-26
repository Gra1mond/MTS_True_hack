#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

chmod +x "$SCRIPT_DIR/scripts/docker-compose.sh"

# Открыть браузер как только фронт поднимется
(
  echo "⏳ Жду запуска фронтенда на localhost:5173..."
  until curl -sf http://localhost:5173 > /dev/null 2>&1; do
    sleep 2
  done
  echo "🌐 Открываю браузер..."
  if command -v open > /dev/null 2>&1; then
    open http://localhost:5173             # macOS
  elif command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:5173        # Linux
  elif command -v cmd.exe > /dev/null 2>&1; then
    cmd.exe /c start http://localhost:5173 2>/dev/null # Windows (Git Bash / WSL)
  fi
) &

"$SCRIPT_DIR/scripts/docker-compose.sh" "$@"
