"""
Main pipeline: orchestrates Planner → Coder → Validator.
Supports verbose and quiet output modes.
"""

import os
import json
import logging
import datetime
from dataclasses import dataclass
from typing import Callable, Optional

from llm import OllamaClient
from agents import PlannerAgent, CoderAgent, ValidatorAgent, ClarifierAgent
from agents.validator import ValidationResult

log = logging.getLogger(__name__)

MAX_RETRIES = 3


@dataclass
class PipelineResult:
    plan: dict
    code: str
    validation: ValidationResult
    output_dir: Optional[str] = None
    retries: int = 0

    @property
    def ok(self) -> bool:
        return self.validation.ok


class LuaPipeline:
    def __init__(self, llm: Optional[OllamaClient] = None):
        self.llm = llm or OllamaClient()
        self.clarifier = ClarifierAgent(self.llm)
        self.planner = PlannerAgent(self.llm)
        self.coder = CoderAgent(self.llm)
        self.validator = ValidatorAgent(self.llm)

        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.tests_dir = os.path.join(self.project_root, "tests")
        os.makedirs(self.tests_dir, exist_ok=True)

    # ──────────────────────────────────────────────────────────
    # Public entry points
    # ──────────────────────────────────────────────────────────

    def run_from_text(
        self,
        task: str,
        context: Optional[dict] = None,
        folder_name: Optional[str] = None,
        clarify_hook: Optional[Callable[[str], Optional[str]]] = None,
    ) -> PipelineResult:
        """
        clarify_hook — callable(question: str) -> answer: str | None.
        If provided, ClarifierAgent may call it once to ask the user for clarification.
        If None, clarification is skipped (useful for HTTP POST or batch mode).
        """
        if clarify_hook is not None:
            clear, question = self.clarifier.check(task, context)
            if not clear and question:
                answer = clarify_hook(question)
                if answer and answer.strip():
                    task = f"{task}\n\nДополнение: {answer.strip()}"

        plan = self.planner.plan(task, context)
        return self._run(plan, folder_name=folder_name)

    def run_from_file(
        self,
        json_path: str,
        folder_name: Optional[str] = None,
    ) -> PipelineResult:
        with open(json_path, encoding="utf-8") as f:
            sample = json.load(f)

        task = sample.get("description") or sample.get("title", "")
        context = sample.get("context")
        plan = self.planner.plan(task, context)

        if "id" in sample:
            plan["task_id"] = sample["id"]
        if "output_key" in sample:
            plan["output_key"] = sample["output_key"]

        return self._run(plan, folder_name=folder_name)

    # ──────────────────────────────────────────────────────────
    # Core pipeline (silent — only returns result)
    # ──────────────────────────────────────────────────────────

    def _run(self, plan: dict, folder_name: Optional[str] = None) -> PipelineResult:
        retries = 0

        log.info("[Pipeline] starting: task_id=%s", plan.get("task_id"))
        code = self.coder.code(plan)

        while True:
            result = self.validator.validate(code, plan)
            if result.ok:
                log.info("[Pipeline] validation PASS after %d retries", retries)
                break
            if retries >= MAX_RETRIES:
                log.warning("[Pipeline] max retries (%d) reached, stopping", MAX_RETRIES)
                break
            retries += 1
            log.info("[Pipeline] validation FAIL, retry %d/%d", retries, MAX_RETRIES)
            code = self.coder.fix(code, result.issues, plan)

        output_dir = self._save(plan, code, result, folder_name)

        return PipelineResult(
            plan=plan,
            code=code,
            validation=result,
            output_dir=output_dir,
            retries=retries,
        )

    # ──────────────────────────────────────────────────────────
    # Save output
    # ──────────────────────────────────────────────────────────

    def _save(
        self,
        plan: dict,
        code: str,
        validation: ValidationResult,
        folder_name: Optional[str] = None,
    ) -> str:
        if folder_name:
            dir_name = folder_name
        else:
            task_id = plan.get("task_id", "task")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dir_name = f"{task_id}_{timestamp}"

        out_dir = os.path.join(self.tests_dir, dir_name)
        os.makedirs(out_dir, exist_ok=True)

        # main.lua
        with open(os.path.join(out_dir, "main.lua"), "w", encoding="utf-8", errors="replace") as f:
            f.write(f"-- Task: {plan.get('original_description', plan.get('title', ''))}\n")
            f.write(f"-- Validation: {'PASS' if validation.ok else 'FAIL'}\n\n")
            f.write(code)
            f.write("\n")

        # test.json — только LowCode формат: {"key": "lua{...}lua"}
        output_key = plan.get("output_key", "result")
        lowcode = json.loads(ValidatorAgent.format_for_lowcode(code, output_key))
        with open(os.path.join(out_dir, "test.json"), "w", encoding="utf-8") as f:
            json.dump(lowcode, f, ensure_ascii=False)

        return out_dir
