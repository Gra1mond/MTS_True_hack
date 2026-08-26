"""
Ollama LLM client for the Lua Code Agent.
Model: qwen2.5-coder:3b
Parameters as specified in TZ: num_ctx=4096, num_predict=256, batch=1, parallel=1
Note: parallel=1 (num_parallel) is also enforced at the server level via OLLAMA_NUM_PARALLEL=1.
"""

import os
import requests
import json
from typing import List, Dict, Optional

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "qwen2.5-coder:7b"

# Parameters as required by the TZ specification
MODEL_OPTIONS = {
    "num_ctx": 4096,
    "num_predict": 256,
    "num_batch": 1,
    "num_parallel": 1,
    "temperature": 0.15,
    "top_p": 0.9,
    "repeat_penalty": 1.1,
}


class OllamaClient:
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = MODEL_NAME,
        options: Optional[Dict] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.options = options or MODEL_OPTIONS

    def is_available(self) -> bool:
        """Check if Ollama server is running and model is loaded."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False
            models = [m["name"] for m in resp.json().get("models", [])]
            return any(self.model in m for m in models)
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system: str = "",
        extra_options: Optional[Dict] = None,
    ) -> str:
        """Single-turn generation using /api/generate."""
        opts = {**self.options, **(extra_options or {})}
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": opts,
        }
        if system:
            payload["system"] = system

        resp = requests.post(
            f"{self.base_url}/api/generate", json=payload, timeout=600
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    def chat(
        self,
        messages: List[Dict],
        system: str = "",
        extra_options: Optional[Dict] = None,
    ) -> str:
        """Multi-turn chat using /api/chat."""
        opts = {**self.options, **(extra_options or {})}
        msgs: List[Dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)

        payload = {
            "model": self.model,
            "messages": msgs,
            "stream": False,
            "options": opts,
        }

        resp = requests.post(
            f"{self.base_url}/api/chat", json=payload, timeout=600
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    def quick_json(self, prompt: str, system: str = "") -> Optional[Dict]:
        """Generate a short JSON response (for analysis tasks)."""
        opts = {**self.options, "num_predict": 150, "temperature": 0.05}
        try:
            raw = self.generate(prompt, system=system, extra_options=opts)
            # Extract JSON from response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except Exception:
            pass
        return None
