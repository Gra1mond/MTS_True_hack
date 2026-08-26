#!/usr/bin/env python3
"""Quick test runner for first 4 sample tasks."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import OllamaClient
from pipeline import LuaPipeline
from agents.validator import ValidatorAgent

TASKS = [
    ("01_last_email.json",  "Из полученного списка email получи последний"),
    ("02_counter.json",     "Увеличь значение переменной try_count_n на каждой итерации"),
    ("03_clear_fields.json","Для полученных данных из предыдущего REST запроса очисти значения переменных ID, ENTITY_ID, CALL"),
    ("04_iso8601.json",     "Преобразуй время из формата YYYYMMDD и HHMMSS в строку ISO 8601"),
]

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample")

def main():
    llm = OllamaClient()
    if not llm.is_available():
        print("❌ Ollama недоступен")
        sys.exit(1)

    pipeline = LuaPipeline(llm=llm)

    for i, (fname, task) in enumerate(TASKS, 1):
        path = os.path.join(SAMPLE_DIR, fname)
        with open(path, encoding="utf-8") as f:
            context = json.load(f)

        print(f"\n{'='*60}")
        print(f"Task {i}: {fname}")
        print(f"Задача: {task}")
        print("─"*60)

        result = pipeline.run_from_text(task, context=context, folder_name=f"test_{i:02d}")

        print(f"Validation: {'✅ PASS' if result.ok else '❌ FAIL'}")
        print(f"Retries: {result.retries}")
        print("\nКод:")
        for line in result.code.split("\n"):
            print(f"  {line}")

        output_key = result.plan.get("output_key", "result")
        lowcode = ValidatorAgent.format_for_lowcode(result.code, output_key)
        print(f"\nJSON:\n  {lowcode[:120]}{'...' if len(lowcode) > 120 else ''}")

    print(f"\n{'='*60}")
    print("Готово.")

if __name__ == "__main__":
    main()
