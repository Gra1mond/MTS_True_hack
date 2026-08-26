"""
Agent 1.5: Clarifier
Checks if the task prompt is clear enough to generate Lua code.
If ambiguous, returns a single clarifying question in Russian.
Runs between Planner and Coder.
"""
from typing import Optional, Tuple
from llm import OllamaClient
from prompts import CLARIFIER_SYSTEM

# Tasks longer than this threshold are assumed clear
_WORD_THRESHOLD = 15


class ClarifierAgent:
    def __init__(self, llm: OllamaClient):
        self.llm = llm

    def check(self, task: str, context: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
        """
        Analyze the task and decide if clarification is needed.

        Returns:
            (True, None)       — task is clear, proceed with generation
            (False, question)  — task is ambiguous, question to ask the user
        """
        # Tasks with context or sufficient detail are assumed clear
        if context or len(task.split()) > _WORD_THRESHOLD:
            return True, None

        raw = self.llm.generate(
            f"Task: {task}",
            system=CLARIFIER_SYSTEM,
            extra_options={"num_predict": 80, "temperature": 0.1},
        ).strip()

        if not raw:
            return True, None

        # Take only the first non-empty line
        first_line = next((line.strip() for line in raw.split("\n") if line.strip()), "")

        # Strip arrows the model might echo (e.g. "task → question")
        if "→" in first_line:
            first_line = first_line.split("→", 1)[-1].strip()

        # If model returned CLEAR (anywhere in a short reply) — treat as clear
        if not first_line or "CLEAR" in first_line.upper():
            return True, None

        # Ensure question ends with "?"
        if not first_line.endswith("?"):
            first_line += "?"

        return False, first_line
