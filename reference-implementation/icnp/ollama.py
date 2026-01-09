\
from __future__ import annotations

import requests
from typing import Any, Dict, List


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout_s: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def chat(self, model: str, messages: List[Dict[str, str]]) -> str:
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        r = requests.post(url, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")
