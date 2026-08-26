#!/usr/bin/env python3
"""
FastAPI HTTP server for the Lua Code Agent.

Endpoints:
  GET  /projects                  — список сохранённых проектов
  GET  /projects/{name}/main.lua  — получить Lua-файл проекта
  POST /generate                  — генерация Lua-кода (HTTP, без уточнений)
  WS   /ws/generate               — генерация с циклом уточнений
  WS   /ws/update_settings        — управление настройками LLM
"""

import sys
import os
import json
import logging
import asyncio
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from llm import OllamaClient, MODEL_OPTIONS
from pipeline import LuaPipeline
from agents import ValidatorAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title="LocalScript API",
    version="1.0.0",
    description="Generates Lua code for MWS Octapi LowCode from a natural language prompt.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── LLM settings state ────────────────────────────────────────────────────────

_ALLOWED_SETTINGS: frozenset[str] = frozenset({
    "num_ctx",
    "num_predict",
    "num_batch",
    "num_parallel",
    "temperature",
    "top_p",
    "repeat_penalty",
})

# Текущие активные настройки (None = дефолты из MODEL_OPTIONS)
_active_settings: dict | None = None

# Singleton pipeline с дефолтными настройками
_default_pipeline: LuaPipeline | None = None


def _build_pipeline(overrides: dict | None) -> LuaPipeline:
    options = {**MODEL_OPTIONS, **(overrides or {})}
    return LuaPipeline(llm=OllamaClient(options=options))


def get_pipeline() -> LuaPipeline:
    """Возвращает pipeline с учётом активных настроек (_active_settings)."""
    global _default_pipeline
    if _active_settings:
        return _build_pipeline(_active_settings)
    if _default_pipeline is None:
        _default_pipeline = _build_pipeline(None)
    return _default_pipeline


# ── Clarification logic ───────────────────────────────────────────────────────

_CLARIFY_SYSTEM = (
    "You help check if a Lua code generation task is clear enough to implement. "
    "If the task is clear, reply with exactly: CLEAR\n"
    "If one specific detail is missing, reply with exactly one short question in Russian (no explanation). "
    "Reply CLEAR or a single question only."
)

# Максимальное количество раундов уточнений за одну сессию генерации
_MAX_CLARIFICATIONS = 3


def _ask_clarification(pipeline: LuaPipeline, task: str) -> str | None:
    """
    Спрашивает LLM: задача понятна или нужно уточнение?
    Возвращает строку с вопросом, если уточнение нужно, или None если всё ясно.
    Threshold применяется только к исходному промпту, а не накопленному контексту.
    """
    # Используем тот же ClarifierAgent, что и в CLI, чтобы поведение совпадало.
    clear, question = pipeline.clarifier.check(task, None)
    if clear or not question:
        return None

    first_line = question.strip()
    if not first_line:
        first_line = "Уточните, пожалуйста, что именно нужно сделать?"

    # Даже если модель не поставила '?', для фронта это всё равно вопрос clarifier.
    if not first_line.endswith("?"):
        first_line = f"{first_line}?"

    return first_line


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# ── Projects ──────────────────────────────────────────────────────────────────

_TESTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")


@app.get("/projects", summary="Список сохранённых проектов")
async def list_projects():
    if not os.path.isdir(_TESTS_DIR):
        return []
    result = []
    for name in sorted(os.listdir(_TESTS_DIR), reverse=True):
        project_dir = os.path.join(_TESTS_DIR, name)
        if not os.path.isdir(project_dir):
            continue
        lua_path = os.path.join(project_dir, "main.lua")
        if not os.path.exists(lua_path):
            continue
        created_at = datetime.datetime.fromtimestamp(
            os.path.getmtime(lua_path), tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        result.append({"name": name, "path": project_dir, "created_at": created_at})
    return result


@app.get(
    "/projects/{name}/main.lua",
    response_class=PlainTextResponse,
    summary="Получить Lua-файл проекта",
)
async def get_project_lua(name: str):
    lua_path = os.path.join(_TESTS_DIR, name, "main.lua")
    if not os.path.exists(lua_path):
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")
    with open(lua_path, encoding="utf-8") as f:
        return f.read()


# ── Request / Response schemas ──────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    code: str


# ── HTTP POST /generate ───────────────────────────────────────────────────────

@app.post("/generate", response_model=GenerateResponse, summary="Сгенерировать Lua-код по описанию")
async def generate(body: GenerateRequest) -> GenerateResponse:
    """
    Принимает описание задачи, прогоняет через pipeline и возвращает Lua-код.
    Уточнений нет — для интерактивной работы используйте WS /ws/generate.
    """
    if not body.prompt.strip():
        raise HTTPException(status_code=422, detail="prompt не может быть пустым")

    log.info("generate: prompt=%r", body.prompt[:120])
    try:
        result = get_pipeline().run_from_text(body.prompt)
    except Exception as exc:
        log.exception("Pipeline error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    log.info("generate: ok=%s retries=%d", result.ok, result.retries)
    return GenerateResponse(code=result.code)


# ── WebSocket helpers ─────────────────────────────────────────────────────────

def _ts() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    )


async def _recv_json(websocket: WebSocket) -> dict | None:
    """Читает следующее сообщение и парсит JSON. None при ошибке парсинга."""
    raw = await websocket.receive_text()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json({"event": "error", "detail": "Invalid JSON"})
        return None


async def _wait_for_clarification_response(
    websocket: WebSocket,
    request_id: str | None,
) -> str | None:
    """
    Блокирует соединение в ожидании события clarification_response от фронтенда.
    Другие события логируются и пропускаются.
    Возвращает строку ответа (может быть пустой) или None при ошибке/дисконнекте.
    """
    while True:
        data = await _recv_json(websocket)
        if data is None:
            continue  # ошибка парсинга — ждём ещё

        incoming_event = data.get("event")

        if incoming_event == "clarification_response":
            # Проверяем request_id для корректности
            if request_id and data.get("request_id") not in (request_id, None):
                log.warning("ws_generate: clarification_response request_id mismatch, ignoring")
                continue
            return (data.get("answer") or "").strip()

        if incoming_event == "cancel" or data.get("prompt"):
            # Пользователь прислал новый запрос или отменил — прерываем текущую сессию
            log.info("ws_generate: session interrupted by new event=%r", incoming_event)
            return None

        log.warning("ws_generate: unexpected event=%r while waiting for clarification", incoming_event)


# ── WebSocket: generation + clarification loop ────────────────────────────────

@app.websocket("/ws/generate")
async def ws_generate(websocket: WebSocket):
    """
    WebSocket endpoint для генерации Lua-кода с поддержкой цикла уточнений.

    ─── Протокол ───────────────────────────────────────────────────────────────

    Клиент → Сервер:
      Начало генерации:
        { "event": "generate", "prompt": str, "request_id"?: str }
        (для обратной совместимости поле event можно не указывать)

      Ответ на уточнение:
        { "event": "clarification_response", "answer": str, "request_id"?: str }

      Отмена текущей сессии:
        { "event": "cancel", "request_id"?: str }

    Сервер → Клиент:
      Запрос уточнения:
        { "event": "clarification_request", "question": str,
          "iteration": int, "request_id"?: str }

      Генерация началась (уточнения завершены):
        { "event": "generation_started", "request_id"?: str }

      Результат:
        { "event": "generation_complete", "prompt": str, "raw_lua": str,
          "lowcode": dict, "retries": int, "timestamp": str, "request_id"?: str }

      Ошибка:
        { "event": "error", "detail": str, "request_id"?: str }

    ─── Логика уточнений ───────────────────────────────────────────────────────

    1. Если исходный промпт короче _CLARIFY_WORD_THRESHOLD слов — LLM проверяет,
       достаточно ли данных.
    2. Если нет — сервер присылает clarification_request с вопросом.
    3. Фронтенд отвечает clarification_response.
    4. Ответ пристыковывается к накопленному контексту.
    5. Шаги 1–4 повторяются до _MAX_CLARIFICATIONS раз или до ответа CLEAR.
    6. Далее запускается pipeline и возвращается generation_complete.
    """
    await websocket.accept()
    log.info("ws_generate: client connected")
    try:
        while True:
            # ── Ожидание нового запроса генерации ────────────────────────────
            data = await _recv_json(websocket)
            if data is None:
                continue

            # Поддержка старого формата (без event) и нового (event: "generate")
            event_type = data.get("event", "generate")

            if event_type not in ("generate",) and "prompt" not in data:
                await websocket.send_json({
                    "event": "error",
                    "detail": f'Неизвестное событие: "{event_type}"',
                })
                continue

            prompt = (data.get("prompt") or "").strip()
            request_id: str | None = data.get("request_id")

            if not prompt:
                await websocket.send_json({
                    "event": "error",
                    "detail": "prompt не может быть пустым",
                    **({"request_id": request_id} if request_id else {}),
                })
                continue

            log.info("ws_generate: NEW SESSION request_id=%s prompt=%r", request_id, prompt[:120])

            pipeline = get_pipeline()
            # ── Цикл уточнений ────────────────────────────────────────────────
            accumulated = prompt

            for iteration in range(_MAX_CLARIFICATIONS):
                question = await asyncio.to_thread(_ask_clarification, pipeline, accumulated)

                if question is None:
                    log.info("ws_generate: clarification CLEAR on iteration %d", iteration)
                    break

                log.info("ws_generate: clarification_request iteration=%d question=%r",
                         iteration + 1, question)

                await websocket.send_json({
                    "event": "clarification_request",
                    "question": question,
                    "iteration": iteration + 1,
                    **({"request_id": request_id} if request_id else {}),
                })

                answer = await _wait_for_clarification_response(websocket, request_id)

                if answer is None:
                    # Сессия прервана (cancel или новый запрос от пользователя)
                    log.info("ws_generate: session cancelled during clarification")
                    break

                if answer:
                    accumulated += f"\nДополнение: {answer}"
                    log.info("ws_generate: answer appended, accumulated length=%d chars",
                             len(accumulated))
                    # Если ответ содержательный — не мучаем пользователя+дальше
                    if len(answer.split()) >= 5:
                        log.info("ws_generate: answer is detailed enough, stopping clarification")
                        break
                else:
                    # Пустой ответ — прекращаем уточнения
                    log.info("ws_generate: empty answer, stopping clarification loop")
                    break

            # ── Запуск генерации ──────────────────────────────────────────────
            log.info("ws_generate: starting pipeline, accumulated=%r", accumulated[:200])

            await websocket.send_json({
                "event": "generation_started",
                **({"request_id": request_id} if request_id else {}),
            })

            try:
                result = await asyncio.to_thread(pipeline.run_from_text, accumulated)
            except Exception as exc:
                log.exception("ws_generate: pipeline error")
                await websocket.send_json({
                    "event": "error",
                    "detail": str(exc),
                    **({"request_id": request_id} if request_id else {}),
                })
                continue

            output_key = result.plan.get("output_key", "result")
            lowcode = json.loads(ValidatorAgent.format_for_lowcode(result.code, output_key))

            response: dict = {
                "event": "generation_complete",
                "prompt": prompt,
                "raw_lua": result.code,
                "lowcode": lowcode,
                "retries": result.retries,
                "timestamp": _ts(),
            }
            if request_id is not None:
                response["request_id"] = request_id

            log.info("ws_generate: DONE ok=%s retries=%d", result.ok, result.retries)
            await websocket.send_json(response)

    except WebSocketDisconnect:
        log.info("ws_generate: client disconnected")


# ── WebSocket: settings management ───────────────────────────────────────────

@app.websocket("/ws/update_settings")
async def ws_update_settings(websocket: WebSocket):
    """
    WebSocket для управления настройками LLM.

    Клиент → Сервер:
      { "settings": { "temperature"?: float, "num_predict"?: int, ... } }
      { "settings": null }  — сброс к дефолтам

    Сервер → Клиент:
      { "event": "settings_updated", "settings": { ...effective... } }
      { "event": "settings_reset",   "settings": { ...defaults...  } }
      { "event": "error",            "detail": "..." }
    """
    global _active_settings

    await websocket.accept()
    log.info("ws_update_settings: client connected")
    try:
        while True:
            data = await _recv_json(websocket)
            if data is None:
                continue

            if "settings" not in data:
                await websocket.send_json({
                    "event": "error",
                    "detail": 'Поле "settings" обязательно',
                })
                continue

            incoming = data["settings"]

            # Сброс: settings: null или settings: {}
            if not incoming:
                _active_settings = None
                log.info("ws_update_settings: reset to defaults")
                await websocket.send_json({
                    "event": "settings_reset",
                    "settings": MODEL_OPTIONS,
                })
                continue

            if not isinstance(incoming, dict):
                await websocket.send_json({
                    "event": "error",
                    "detail": '"settings" должен быть объектом',
                })
                continue

            filtered = {k: v for k, v in incoming.items() if k in _ALLOWED_SETTINGS}
            unknown = set(incoming) - _ALLOWED_SETTINGS
            if unknown:
                log.warning("ws_update_settings: ignoring unknown keys: %s", unknown)

            _active_settings = filtered if filtered else None
            effective = {**MODEL_OPTIONS, **(_active_settings or {})}

            log.info("ws_update_settings: applied %s → effective %s", filtered, effective)
            await websocket.send_json({
                "event": "settings_updated",
                "settings": effective,
            })

    except WebSocketDisconnect:
        log.info("ws_update_settings: client disconnected")
