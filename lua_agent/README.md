# Lua Code Agent — MWS Octapi LowCode

AI-агент для генерации Lua-кода для платформы MWS Octapi LowCode на базе локальной LLM (без внешних API).

Предоставляет **HTTP API** (`POST /generate`) и **CLI** для локальной отладки.

## Стек

- Python 3.12
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) — HTTP-сервер
- [Ollama](https://ollama.com/) — локальный LLM-сервер
- Модель: **qwen2.5-coder:3b** (~2 GB)
- `luac` + `luacheck` — проверка синтаксиса и статический анализ Lua

---

## Быстрый запуск через Docker

```bash
git clone <repo-url> && cd fak
docker compose up --build
```

API будет доступен на `http://localhost:8080`.  
При первом запуске Docker скачает модель (~2 GB) — это займёт несколько минут.

---

## HTTP API

### `POST /generate`

Генерирует Lua-код по описанию задачи на естественном языке.

**Запрос:**

```json
{
  "prompt": "Функция factorial(n) для n >= 0"
}
```

**Ответ (200 OK):**

```json
{
  "code": "function factorial(n)\n  if n <= 1 then return 1 end\n  return n * factorial(n - 1)\nend"
}
```

**Пример через curl:**

```bash
curl -X POST http://localhost:8080/generate \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Функция factorial(n) для n >= 0"}'
```

Интерактивная документация (Swagger UI): `http://localhost:8080/docs`

---

## Запуск через Docker (подробно)

### Требования

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- 4 GB RAM минимум, ~3 GB свободного места на диске

### Запустить

```bash
# Первый запуск (сборка образа + скачивание модели ~2 GB)
docker compose up --build

# Последующие запуски
docker compose up
```

Остановить:

```bash
docker compose down
```

Остановить и удалить кеш модели:

```bash
docker compose down -v
```

### GPU (опционально, для ускорения)

Если есть NVIDIA GPU, добавьте в `docker-compose.yml` в секцию `ollama`:

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

---

## Запуск без Docker (локально)

### 1. Установить Ollama и скачать модель

```bash
ollama pull qwen2.5-coder:3b
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Запустить HTTP-сервер

```bash
uvicorn server:app --host 0.0.0.0 --port 8080
```

### 4. CLI (опционально)

```bash
python main.py
```

---

## Как это работает

### Архитектура: 3 агента

```
HTTP POST /generate (prompt)
         │
         ▼
  Agent 1: Planner
  Анализирует задачу → возвращает JSON-план:
  task_id, output_key, inputs, steps, needs_array_utils
         │
         ▼
  Agent 2: Coder
  По плану генерирует Lua-код
         │
         ▼
  Agent 3: Validator  ┐
  Phase 1: luac       │ если ошибка → Coder.fix() → повтор
  Phase 2: luacheck   │ до 2 раз
  Phase 3: LLM-review ┘
         │
         ▼
  HTTP 200 {"code": "..."}
  Сохранение: tests/<папка>/main.lua + test.json
```

### Параметры LLM

| Параметр | Значение |
|---|---|
| `num_ctx` | 4096 |
| `num_predict` | 256 |
| `num_batch` | 1 |
| `num_parallel` | 1 |
| `temperature` | 0.15 |

`OLLAMA_NUM_PARALLEL=1` — обязательное техническое ограничение, выставляется на уровне сервера Ollama.

### Формат вывода

Lua-код также оборачивается в LowCode JSON-формат и сохраняется в `tests/`:

```json
{"output_key": "lua{<Lua код>}lua"}
```

---

## Структура проекта

```
lua_agent/
├── server.py         — FastAPI HTTP-сервер (POST /generate)
├── main.py           — CLI, диалоговый цикл (локальная отладка)
├── pipeline.py       — оркестратор трёх агентов
├── llm.py            — клиент Ollama REST API
├── prompts.py        — системные промпты для каждого агента
├── agents/
│   ├── planner.py    — Agent 1: анализ задачи → JSON-план
│   ├── coder.py      — Agent 2: генерация и исправление Lua-кода
│   └── validator.py  — Agent 3: luac + luacheck + LLM-review
├── sample/           — контексты для типовых задач (JSON)
├── tests/            — результаты генерации (main.lua + test.json)
├── .luacheckrc       — конфиг luacheck (globals: wf, _utils)
└── run_tests.py      — быстрый тест на первых 4 задачах
```

---

## Ограничения платформы MWS Octapi LowCode (Lua 5.5)

- Переменные только через `wf.vars.<имя>` — НЕ через JsonPath
- Init-переменные через `wf.initVariables.<имя>`
- Новый массив: `_utils.array.new()`
- Пометить существующий как массив: `_utils.array.markAsArray(arr)`
- Скрипт **обязательно** заканчивается на `return <значение>`
- Нет доступа к `os.*`, `io.*`, `require()`

---

## Файлы sample/

Каждый файл содержит контекст в формате платформы:

```json
{
  "wf": {
    "vars": { ... },
    "initVariables": { ... }
  }
}
```

| Файл | Задача |
|---|---|
| `01_last_email.json` | Последний элемент массива |
| `02_counter.json` | Счётчик попыток |
| `03_clear_fields.json` | Очистка полей объекта |
| `04_iso8601.json` | Конвертация даты в ISO 8601 |
| `05_ensure_array.json` | Приведение items к массиву |
| `06_filter_array.json` | Фильтрация элементов массива |
| `07_supplement.json` | Дополнение существующего кода |
| `08_unix_time.json` | Конвертация времени в Unix |

---

## Команды CLI (`main.py`)

| Команда | Описание |
|---|---|
| `/sample <файл>` | Загрузить контекст из JSON-файла в `sample/`, затем ввести задачу |
| `/new <папка>` | Задать имя папки для результата в `tests/`, затем ввести задачу |
| `/list` | Показать доступные sample-файлы |
| `/help` | Показать справку |
| `/exit` | Выход |
| `<текст>` | Ввести задачу напрямую |
