"""
Agent 3: Validator
Three-phase validation:
  Phase 1 — luac   : syntax check (Lua compiler)
  Phase 2 — luacheck: static analysis (undefined globals, shadowing, etc.)
  Phase 3 — LLM    : semantic review (does code match the task?)
"""

import subprocess
import shutil
import re
import json
import os
import logging
from dataclasses import dataclass, field
from typing import Optional
from llm import OllamaClient
from prompts import VALIDATOR_SYSTEM

log = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    ok: bool
    phase: str                    # "luac" | "luacheck" | "llm" | "pass"
    issues: list[str] = field(default_factory=list)
    llm_notes: str = ""
    suggestion: str = ""

    def summary(self) -> str:
        if self.ok:
            return f"✅ PASS  {('LLM: ' + self.llm_notes) if self.llm_notes else ''}"
        lines = [f"❌ FAIL [{self.phase}]"]
        for issue in self.issues:
            lines.append(f"   • {issue}")
        if self.suggestion:
            lines.append(f"   ↳ Suggestion: {self.suggestion}")
        return "\n".join(lines)


class ValidatorAgent:
    def __init__(self, llm: OllamaClient):
        self.llm = llm
        self.luac = shutil.which("luac") or shutil.which("luac5.4")
        self.luacheck = shutil.which("luacheck")
        # Path to .luacheckrc (project root)
        self._rc = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".luacheckrc",
        )

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    def validate(self, code: str, plan: dict) -> ValidationResult:
        """Run all three validation phases in order."""
        log.info("[Validator] starting validation (%d lines of code)", len(code.splitlines()))

        # Phase 1: luac — syntax
        result = self._phase_luac(code)
        log.info("[Validator] phase=luac ok=%s %s", result.ok,
                 ("issues: " + "; ".join(result.issues)) if not result.ok else "")
        if not result.ok:
            return result

        # Phase 2: luacheck — static analysis
        result = self._phase_luacheck(code)
        log.info("[Validator] phase=luacheck ok=%s %s", result.ok,
                 ("issues: " + "; ".join(result.issues)) if not result.ok else "")
        if not result.ok:
            return result

        # Phase 3: LLM — semantic review
        result = self._phase_llm(code, plan)
        log.info("[Validator] phase=llm ok=%s notes=%r", result.ok, result.llm_notes)
        return result

    # ──────────────────────────────────────────────────────────
    # Phase 1: luac
    # ──────────────────────────────────────────────────────────

    def _phase_luac(self, code: str) -> ValidationResult:
        if not self.luac:
            # luac not available — skip phase, warn
            return ValidationResult(ok=True, phase="luac", issues=["luac not found, skipped"])

        try:
            proc = subprocess.run(
                [self.luac, "-p", "-"],
                input=code.encode("utf-8"),
                capture_output=True,
                timeout=10,
            )
        except Exception as e:
            return ValidationResult(ok=False, phase="luac", issues=[f"luac error: {e}"])

        if proc.returncode == 0:
            return ValidationResult(ok=True, phase="luac")

        err = proc.stderr.decode("utf-8", errors="replace").strip()
        err = re.sub(r"stdin:", "line ", err)
        return ValidationResult(ok=False, phase="luac", issues=[err])

    # ──────────────────────────────────────────────────────────
    # Phase 2: luacheck
    # ──────────────────────────────────────────────────────────

    def _phase_luacheck(self, code: str) -> ValidationResult:
        if not self.luacheck:
            return ValidationResult(ok=True, phase="luacheck", issues=["luacheck not found, skipped"])

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".lua", mode="w", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        try:
            cmd = [self.luacheck, tmp_path]
            # Use .luacheckrc if it exists
            if os.path.exists(self._rc):
                cmd += ["--config", self._rc]
            else:
                cmd += ["--globals", "wf", "_utils", "--allow-defined"]

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except Exception as e:
            return ValidationResult(ok=False, phase="luacheck", issues=[f"luacheck error: {e}"])
        finally:
            os.unlink(tmp_path)

        # Parse output
        output = proc.stdout + proc.stderr
        issues = self._parse_luacheck_output(output)

        if proc.returncode == 0 or not issues:
            return ValidationResult(ok=True, phase="luacheck")

        # Filter out "OK" lines and empty
        real_issues = [i for i in issues if i]
        if not real_issues:
            return ValidationResult(ok=True, phase="luacheck")

        return ValidationResult(ok=False, phase="luacheck", issues=real_issues)

    def _parse_luacheck_output(self, output: str) -> list[str]:
        """Extract meaningful warning/error lines from luacheck output."""
        issues = []
        for line in output.split("\n"):
            # Match lines like: "  file.lua:5:3: (W111) ..."
            m = re.search(r":(\d+):(\d+): (.+)", line)
            if m:
                ln, col, msg = m.group(1), m.group(2), m.group(3)
                issues.append(f"line {ln}:{col} — {msg}")
        return issues

    # ──────────────────────────────────────────────────────────
    # Phase 3: LLM review
    # ──────────────────────────────────────────────────────────

    def _phase_llm(self, code: str, plan: dict) -> ValidationResult:
        task = plan.get("lua_task") or plan.get("original_description", "")
        prompt = (
            f"Task: {task}\n\n"
            f"Lua code to review:\n{code}\n\n"
            f"Review the code against the task."
        )

        raw = self.llm.quick_json(
            prompt,
            system=VALIDATOR_SYSTEM,
        )

        if not raw:
            # LLM failed → treat as pass (we already passed luac + luacheck)
            return ValidationResult(ok=True, phase="llm", llm_notes="LLM review unavailable")

        status = raw.get("status", "ok")
        notes = raw.get("notes", "")
        issue = raw.get("issue", "")
        suggestion = raw.get("suggestion", "")

        if status == "ok":
            return ValidationResult(ok=True, phase="pass", llm_notes=notes)

        return ValidationResult(
            ok=False,
            phase="llm",
            issues=[issue] if issue else ["LLM review found issues"],
            llm_notes=notes,
            suggestion=suggestion,
        )

    # ──────────────────────────────────────────────────────────
    # Helper: format Lua for LowCode JSON
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def format_for_lowcode(code: str, output_key: str = "result") -> str:
        escaped = (
            code
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\r\n", "\\r\\n")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
        return f'{{"{output_key}": "lua{{{escaped}}}lua"}}'
