#!/usr/bin/env python3
"""
Lua Code Agent — CLI

Триггеры:
  /sample <путь>        — загрузить задачу из JSON-файла и решить её
  /new <папка>          — следующее сообщение будет задачей,
                          результат сохранится в tests/<папка>/
  /list                 — список sample-файлов
  /help                 — справка
  /exit                 — выход
  <текст>               — запустить pipeline для текстовой задачи
"""

import sys
import os
import glob
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import OllamaClient, MODEL_NAME
from pipeline import LuaPipeline
from agents.validator import ValidatorAgent
from agents.clarifier import ClarifierAgent

BANNER = """
╔══════════════════════════════════════════════════════════╗
║     Lua Code Agent  │  Planner → Coder → Validator       ║
║     Model: qwen2.5-coder:7b  (Ollama, local)             ║
╠══════════════════════════════════════════════════════════╣
║  Команды:                                                ║
║   /sample <файл>   загрузить задачу из JSON              ║
║                    пример: /sample 01_last_email.json    ║
║   /new <папка>     имя папки для следующего результата   ║
║                    пример: /new my_script                ║
║   /list            список доступных sample-файлов        ║
║   /help            показать эти команды снова            ║
║   /exit            выход                                 ║
║                                                          ║
║  Или просто введите задачу на русском / английском.      ║
╚══════════════════════════════════════════════════════════╝
"""

HELP = """
  /sample <путь>   загрузить задачу из JSON
                     пример: /sample sample/01_last_email.json
  /new <папка>     задать имя папки для следующего результата
                     пример: /new my_script
                     затем введите задачу текстом
  /list            список sample-файлов
  /help            эта справка
  /exit            выход

  Или просто введите задачу на русском/английском.
"""


def print_result(result, _project_root: str):
    """Вывод: код + LowCode JSON."""
    output_key = result.plan.get("output_key", "result")
    lowcode = ValidatorAgent.format_for_lowcode(result.code, output_key)

    print()
    print("┌─ Lua ──────────────────────────────────────────────────")
    for line in result.code.split("\n"):
        print(f"│  {line}")
    print("└────────────────────────────────────────────────────────")
    print(lowcode)
    print()


def check_ollama(llm: OllamaClient) -> bool:
    print(f"⏳ Ollama ({MODEL_NAME})...", end=" ", flush=True)
    if not llm.is_available():
        print(f"\n❌ Недоступен. Запустите: ollama serve && ollama pull {MODEL_NAME}")
        return False
    print("✅")
    return True


def find_sample(name: str, project_root: str) -> str | None:
    """Найти sample-файл по частичному имени."""
    sample_dir = os.path.join(project_root, "sample")
    # Exact path
    if os.path.exists(name):
        return name
    # Inside sample/
    direct = os.path.join(sample_dir, name)
    if os.path.exists(direct):
        return direct
    # Fuzzy match
    candidates = glob.glob(os.path.join(sample_dir, f"*{name}*"))
    return candidates[0] if candidates else None


def list_samples(project_root: str):
    files = sorted(glob.glob(os.path.join(project_root, "sample", "*.json")))
    if not files:
        print("  (нет файлов в sample/)")
        return
    for f in files:
        print(f"  • {os.path.basename(f)}")



def main():
    print(BANNER)

    llm = OllamaClient()
    if not check_ollama(llm):
        sys.exit(1)

    pipeline = LuaPipeline(llm=llm)
    root = pipeline.project_root

    def cli_clarify_hook(question: str) -> str:
        print(f"  ❓ {question}")
        try:
            return input("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            return ""

    pending_folder: str | None = None   # имя папки из /new
    pending_context: dict | None = None  # контекст из /sample

    print()
    while True:
        try:
            parts_prompt = []
            if pending_folder:
                parts_prompt.append(f"folder→{pending_folder}")
            if pending_context:
                parts_prompt.append("ctx✓")
            prefix = f"({', '.join(parts_prompt)}) " if parts_prompt else ""
            line = input(f"{prefix}> ").encode("utf-8", errors="replace").decode("utf-8").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nДо свидания!")
            break

        if not line:
            continue

        # ── /exit ───────────────────────────────────────────
        if line.lower() in ("/exit", "/quit", "exit", "выход"):
            print("До свидания!")
            break

        # ── /help ───────────────────────────────────────────
        if line.lower() in ("/help", "/?"):
            print(HELP)
            continue

        # ── /list ───────────────────────────────────────────
        if line.lower() == "/list":
            list_samples(root)
            continue

        # ── /sample <путь> ──────────────────────────────────
        if line.lower().startswith("/sample"):
            parts = line.split(None, 1)
            if len(parts) < 2:
                print("  Использование: /sample <файл>")
                continue
            path = find_sample(parts[1].strip(), root)
            if not path:
                print(f"  ❌ Файл не найден: {parts[1]}")
                print("  Используйте /list для просмотра доступных файлов.")
                continue
            with open(path, encoding="utf-8") as f:
                pending_context = json.load(f)
            print(f"  Контекст загружен из {os.path.basename(path)}:")
            print(f"  {json.dumps(pending_context, ensure_ascii=False)}")
            print(f"  Введите задачу:")
            continue

        # ── /new <папка> ────────────────────────────────────
        if line.lower().startswith("/new"):
            parts = line.split(None, 1)
            if len(parts) < 2 or not parts[1].strip():
                print("  Использование: /new <имя_папки>")
                continue
            pending_folder = parts[1].strip()
            print(f"  Результат → tests/{pending_folder}/")
            print(f"  Введите задачу:")
            continue

        # ── Текстовая задача ─────────────────────────────────
        task = line
        ctx = pending_context
        folder = pending_folder
        pending_folder = None
        pending_context = None

        while True:
            print("  ⏳ Обрабатываю...")
            result = pipeline.run_from_text(
                task, context=ctx, folder_name=folder, clarify_hook=cli_clarify_hook
            )
            print_result(result, root)
            try:
                feedback = input("  Уточнить? (Enter — продолжить, иначе — правка): ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not feedback:
                break
            task = f"{task}\n\nПравка: {feedback}"
            ctx = None  # context already encoded in plan on first run


if __name__ == "__main__":
    main()
