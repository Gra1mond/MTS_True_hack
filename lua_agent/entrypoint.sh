#!/bin/sh
set -e

OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
MODEL="qwen2.5-coder:7b"

echo "⏳ Ожидаю Ollama на $OLLAMA_URL ..."
until curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; do
    sleep 2
done
echo "✅ Ollama доступен"

if ! curl -sf "$OLLAMA_URL/api/tags" | grep -q "$MODEL"; then
    echo "⬇️  Скачиваю $MODEL (первый запуск, ~2 GB)..."
    curl -s -X POST "$OLLAMA_URL/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$MODEL\"}" \
    | python3 -c "
import sys, json

last_pct = -1
done = False
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        data = json.loads(line)
    except Exception:
        continue

    status = data.get('status', '')
    total = data.get('total', 0)
    completed = data.get('completed', 0)

    if done:
        continue

    if total > 0:
        pct = int(completed / total * 100)
        if pct >= last_pct + 10 or pct == 100:
            last_pct = pct
            filled = pct // 2
            bar = '#' * filled + '-' * (50 - filled)
            mb_done = completed // 1024 // 1024
            mb_total = total // 1024 // 1024
            print(f'  [{bar}] {pct:3d}%  {mb_done} / {mb_total} MB', flush=True)
            if pct == 100:
                done = True
    elif status and status != 'success':
        print(f'  {status}', flush=True)
"
    echo "✅ Модель готова"
fi

exec uvicorn server:app --host 0.0.0.0 --port 8080
