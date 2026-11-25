"""Provider-agnostic chat clients over plain HTTPS (no vendor SDK needed).

Both providers below offer free API tiers. Model names change over time, so
they are configuration, not code: set GEMINI_MODEL or GROQ_MODEL to a model
your account can use.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Protocol

import requests

RETRYABLE = {429, 500, 502, 503, 504}


def _post_with_retry(url: str, attempts: int = 3, **kwargs) -> requests.Response:
    """POST with exponential backoff on rate limits and temporary overload (free tiers return 429 or 503)."""
    for i in range(attempts):
        r = requests.post(url, timeout=60, **kwargs)
        if r.status_code not in RETRYABLE or i == attempts - 1:
            return r
        time.sleep(2 ** (i + 1))
    return r


class ChatClient(Protocol):
    name: str

    def chat(self, system: str, messages: list[dict]) -> str: ...


@dataclass
class GeminiClient:
    api_key: str
    model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-flash-latest"))
    name: str = "Google Gemini"
    fallback_model: str | None = "gemini-3.5-flash-lite"

    def chat(self, system: str, messages: list[dict]) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                    for m in messages]
        body = {"system_instruction": {"parts": [{"text": system}]}, "contents": contents,
                "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}}
        r = _post_with_retry(url, params={"key": self.api_key}, json=body)
        if r.status_code in RETRYABLE and self.fallback_model and self.fallback_model != self.model:
            # The free tier sometimes reports the newest model as overloaded: answer with the lighter model instead.
            url = url.replace(f"/models/{self.model}:", f"/models/{self.fallback_model}:")
            r = _post_with_retry(url, params={"key": self.api_key}, json=body)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]


@dataclass
class GroqClient:
    api_key: str
    model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    name: str = "Groq"

    def chat(self, system: str, messages: list[dict]) -> str:
        r = _post_with_retry("https://api.groq.com/openai/v1/chat/completions",
                             headers={"Authorization": f"Bearer {self.api_key}"},
                             json={"model": self.model, "temperature": 0.0, "response_format": {"type": "json_object"},
                                   "messages": [{"role": "system", "content": system}, *messages]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def client_from_env(secrets: dict | None = None) -> ChatClient | None:
    """Pick a provider from Streamlit secrets or environment variables."""
    def get(key: str) -> str | None:
        return (secrets or {}).get(key) or os.getenv(key)

    if get("GEMINI_API_KEY"):
        return GeminiClient(get("GEMINI_API_KEY"), get("GEMINI_MODEL") or "gemini-flash-latest")
    if get("GROQ_API_KEY"):
        return GroqClient(get("GROQ_API_KEY"), get("GROQ_MODEL") or "llama-3.3-70b-versatile")
    return None
