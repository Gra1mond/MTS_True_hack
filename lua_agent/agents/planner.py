"""
Agent 1: Planner
Analyzes the user's task and returns a structured JSON plan.
"""

import json
import re
import logging
from typing import Optional
from llm import OllamaClient
from prompts import PLANNER_SYSTEM

log = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self, llm: OllamaClient):
        self.llm = llm

    def plan(self, task_description: str, context: Optional[dict] = None) -> dict:
        """
        Analyze the task and return a structured plan as a dict.
        """
        prompt = f"Task: {task_description}"
        if context:
            prompt += f"\nContext (available data): {json.dumps(context, ensure_ascii=False)}"

        log.info("[Planner] → prompt: %s", prompt[:300])

        raw = self.llm.generate(
            prompt,
            system=PLANNER_SYSTEM,
            extra_options={"temperature": 0.1},
        )

        log.info("[Planner] ← response: %s", raw[:500])

        plan = self._parse_json(raw)

        # Fallback: build minimal plan if LLM failed
        if not plan:
            log.warning("[Planner] JSON parse failed, using fallback plan")
            plan = self._fallback_plan(task_description)
        else:
            log.info("[Planner] plan: task_id=%s title=%r steps=%d",
                     plan.get("task_id"), plan.get("title"), len(plan.get("steps", [])))

        # Enrich with original description
        plan["original_description"] = task_description
        if context:
            plan["context"] = context

        return plan

    # ------------------------------------------------------------------

    def _parse_json(self, raw: str) -> Optional[dict]:
        """Extract JSON from LLM response."""
        raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            # Try to repair common issues
            fixed = re.sub(r",\s*}", "}", raw[start:end])  # trailing comma
            fixed = re.sub(r",\s*]", "]", fixed)
            try:
                return json.loads(fixed)
            except Exception:
                return None

    def _fallback_plan(self, task: str) -> dict:
        """Minimal plan when LLM JSON parsing fails."""
        return {
            "task_id": "task",
            "title": task[:60],
            "lua_task": task,
            "inputs": [],
            "output_key": "result",
            "steps": ["Implement the task as described"],
            "needs_array_utils": False,
            "complexity": "simple",
        }

    def pretty_print(self, plan: dict) -> str:
        """Format plan for console display."""
        lines = [
            f"  task_id   : {plan.get('task_id', '?')}",
            f"  title     : {plan.get('title', '?')}",
            f"  inputs    : {', '.join(plan.get('inputs', [])) or '—'}",
            f"  output_key: {plan.get('output_key', 'result')}",
            f"  complexity: {plan.get('complexity', '?')}",
            f"  steps     :",
        ]
        for i, step in enumerate(plan.get("steps", []), 1):
            lines.append(f"    {i}. {step}")
        return "\n".join(lines)
