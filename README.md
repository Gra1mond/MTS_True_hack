# LocalScript — AI-агент генерации Lua-кода

Локальный AI-агент для генерации Lua-скриптов под платформу **MWS Octapi LowCode**.
Работает полностью офлайн на базе [Ollama](https://ollama.com/) — никаких внешних API.

## Стек

| Компонент | Технология |
|---|---|
| LLM | `qwen2.5-coder:3b` via Ollama |
| Бэкенд | Python 3.12, FastAPI, Uvicorn |
| Фронтенд | Vue 3, TypeScript, Vite, Tailwind CSS |
| Валидация | `luac` (синтаксис) + `luacheck` (статика) + LLM (семантика) |
| Инфраструктура | Docker, Docker Compose |

---

## Быстрый запуск

**Требования:** Docker + Docker Compose, 6 GB RAM, ~3 GB места на диске.

```bash
git clone https://git.truetecharena.ru/tta/true-tech-hack2026-localscript/30-30-feat/task-repo.git
cd task-repo
./start.sh # При первичном запуске может понадобиться повторное введение команды
```

`start.sh` автоматически определяет наличие NVIDIA GPU и подключает нужный compose-файл.

При **первом запуске** автоматически скачается модель `qwen2.5-coder:3b` (~1.8 GB) — займёт несколько минут. Последующие запуски — мгновенные.

| Сервис | URL |
|---|---|
| Фронтенд | http://localhost:5173 |
| Бэкенд API | http://localhost:8080 |
| Swagger UI | http://localhost:8080/docs |
| Ollama | http://localhost:11434 |

Остановить:
```bash
docker compose down
```

Остановить и удалить кэш модели:
```bash
docker compose down -v
```

---

## Архитектура

```
Пользователь (prompt)
        │
        ▼
┌─────────────────┐
│  Agent: Clarifier│  Задача слишком расплывчатая?
│  (уточнение)    │  → задаёт один уточняющий вопрос
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent: Planner │  prompt → структурированный JSON-план
│                 │  (task_id, inputs, steps, output_key)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent: Coder   │  план → nil-безопасный Lua-код
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Agent: Validator                │
│  Phase 1: luac    (синтаксис)    │  ошибка → Coder.fix() → повтор
│  Phase 2: luacheck (статика)     │  до 3 раз
│  Phase 3: LLM     (семантика)    │
└────────┬─────────────────────────┘
         │
         ▼
   Lua-код + LowCode JSON
   сохраняется в tests/<папка>/
```

---

## API

### `POST /generate`

```bash
curl -X POST http://localhost:8080/generate \
     -H "Content-Type: application/json" \
     -d '{"prompt": "найти максимальный элемент в массиве чисел"}'
```

```json
{ "code": "local arr = wf.vars.arr or {}\n..." }
```

### `GET /projects`

Список сохранённых результатов генерации.

```bash
curl http://localhost:8080/projects
```

### `GET /projects/{name}/main.lua`

Lua-файл конкретного проекта.

```bash
curl http://localhost:8080/projects/binary_search_20260414_134937/main.lua
```

### `WS /ws/generate`

WebSocket с поддержкой цикла уточнений.

**Клиент → Сервер:**
```json
{ "event": "generate", "prompt": "бинарный поиск", "request_id": "abc123" }
```

**Сервер → Клиент (если задача неясна):**
```json
{ "event": "clarification_request", "question": "Что искать в массиве?" }
```

**Клиент → Сервер (ответ на уточнение):**
```json
{ "event": "clarification_response", "answer": "индекс числа по значению" }
```

**Сервер → Клиент (результат):**
```json
{
  "event": "generation_complete",
  "raw_lua": "...",
  "lowcode": { "result": "lua{...}lua" },
  "retries": 0,
  "timestamp": "2026-04-15T10:00:00.000Z"
}
```

---

## Структура проекта

```
fak3/
├── start.sh                    — точка запуска (авто-GPU)
├── docker-compose.yml          — базовая конфигурация
├── docker-compose.gpu.yml      — оверрайд для NVIDIA GPU
├── scripts/
│   └── docker-compose.sh       — скрипт авто-определения GPU
│
├── lua_agent/                  — бэкенд (Python)
│   ├── server.py               — FastAPI HTTP + WebSocket сервер
│   ├── main.py                 — CLI-интерфейс
│   ├── pipeline.py             — оркестратор агентов
│   ├── llm.py                  — клиент Ollama REST API
│   ├── prompts.py              — системные промпты агентов
│   ├── entrypoint.sh           — Docker entrypoint (ожидание Ollama + pull модели)
│   ├── agents/
│   │   ├── clarifier.py        — уточнение расплывчатых задач
│   │   ├── planner.py          — задача → JSON-план
│   │   ├── coder.py            — план → Lua-код
│   │   └── validator.py        — luac + luacheck + LLM-ревью
│   ├── sample/                 — примеры контекстов (JSON)
│   └── tests/                  — результаты генерации (создаётся в runtime)
│
└── lua_agent_ui/               — фронтенд (Vue 3 + TypeScript)
    ├── src/
    │   ├── composables/
    │   │   └── useWebSocket.ts — WebSocket с авто-реконнектом
    │   ├── stores/
    │   │   └── chat.ts         — Pinia store (история чатов, localStorage)
    │   └── components/         — Vue-компоненты UI
    └── Dockerfile
```

---

## Ограничения платформы MWS Octapi LowCode

- Переменные только через `wf.vars.<имя>` — не через JsonPath (`$.`)
- Init-переменные: `wf.initVariables.<имя>`
- Новый массив: `_utils.array.new()`
- Пометить существующий как массив: `_utils.array.markAsArray(arr)`
- Скрипт обязан заканчиваться на `return <значение>`
- Нет доступа к `os.*`, `io.*`, `require()`
- Все переменные из `wf.vars` могут быть `nil` — обязателен fallback: `local x = wf.vars.x or 0`

---

## Параметры модели

| Параметр | Значение |
|---|---|
| Модель | `qwen2.5-coder:3b` |
| `num_ctx` | 4096 |
| `num_predict` | 256 |
| `temperature` | 0.15 |
| `top_p` | 0.9 |
| `repeat_penalty` | 1.1 |

Параметры можно менять через WebSocket `/ws/update_settings` без перезапуска сервера.
