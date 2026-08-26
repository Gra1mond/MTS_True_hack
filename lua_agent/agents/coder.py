"""
Agent 2: Coder
Generates Lua code based on the plan from PlannerAgent.
Can also fix code given validation errors.
"""

import re
import logging
from typing import Optional
from llm import OllamaClient
from prompts import CODER_SYSTEM, CODER_FIX_SYSTEM

log = logging.getLogger(__name__)


class CoderAgent:
    def __init__(self, llm: OllamaClient):
        self.llm = llm

    def code(self, plan: dict) -> str:
        """
        Generate Lua code based on a plan dict.
        """
        prompt = self._build_code_prompt(plan)
        log.info("[Coder] → generating code for task: %r", plan.get("title", "")[:120])
        log.debug("[Coder] → prompt: %s", prompt[:500])
        raw = self.llm.generate(prompt, system=CODER_SYSTEM)
        result = self._extract_lua(raw)
        log.info("[Coder] ← generated %d lines of Lua", len(result.splitlines()))
        log.debug("[Coder] ← code:\n%s", result[:800])
        return result

    def fix(self, broken_code: str, issues: list[str], plan: dict) -> str:
        """
        Fix broken Lua code given a list of issues.
        """
        issues_text = "\n".join(f"- {i}" for i in issues)
        log.info("[Coder] → fixing code, issues: %s", issues)
        prompt = (
            f"Task: {plan.get('lua_task', plan.get('original_description', ''))}\n\n"
            f"Current (broken) Lua code:\n{broken_code}\n\n"
            f"Problems found:\n{issues_text}\n\n"
            f"Fix all problems. Return ONLY corrected Lua code."
        )
        raw = self.llm.generate(prompt, system=CODER_FIX_SYSTEM)
        result = self._extract_lua(raw)
        log.info("[Coder] ← fixed code: %d lines", len(result.splitlines()))
        log.debug("[Coder] ← fixed:\n%s", result[:800])
        return result

    # ------------------------------------------------------------------

    def _build_code_prompt(self, plan: dict) -> str:
        """Build the generation prompt from the plan."""
        task = plan.get("lua_task") or plan.get("original_description", "")
        inputs = plan.get("inputs", [])
        steps = plan.get("steps", [])
        output_key = plan.get("output_key", "result")

        parts = [f"Task: {task}"]

        if inputs:
            parts.append(f"Input variables: {', '.join(inputs)}")

        if steps:
            parts.append("Implementation steps:")
            for i, step in enumerate(steps, 1):
                parts.append(f"  {i}. {step}")

        parts.append(f"Return variable name: {output_key}")

        # Add context if available
        ctx = plan.get("context")
        if ctx:
            import json
            parts.append(f"Data context: {json.dumps(ctx, ensure_ascii=False)[:300]}")

        return "\n".join(parts)

    @staticmethod
    def _extract_lua(raw: str) -> str:
        """
        Strip markdown fences and leading explanations from LLM output.
        """
        if not raw:
            return ""

        # Remove markdown code fences
        raw = re.sub(r"```lua\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)

        lines = raw.strip().split("\n")

        # Find first line that looks like Lua code
        lua_starters = [
            r"^\s*(local|return|if|for|while|repeat|function|--)",
            r"^\s*\w+\s*=\s*",
            r"^\s*\w+(\.\w+)+",
        ]
        for i, line in enumerate(lines):
            if any(re.match(p, line) for p in lua_starters):
                return "\n".join(lines[i:]).strip()

        return raw.strip()
