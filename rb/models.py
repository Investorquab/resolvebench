"""One client for any OpenAI-compatible chat endpoint (OpenRouter, xAI, Google's
OpenAI-compatible endpoint, Groq, ...). Keys are read from environment variables named
in config.yaml; they are never written to disk or logged."""
import logging
import os
import random
import threading
import time

log = logging.getLogger("rb")


class ModelClient:
    def __init__(self, cfg, http):
        self.name = cfg["name"]
        self.model = cfg["model"]
        self.base_url = cfg["base_url"].rstrip("/")
        self.key_env = cfg["api_key_env"]
        self.key = os.environ.get(self.key_env, "")
        self.price_in = float(cfg.get("price_in", 0))    # USD per 1M input tokens
        self.price_out = float(cfg.get("price_out", 0))  # USD per 1M output tokens
        self.max_tokens = int(cfg.get("max_tokens", 1500))
        self.temperature = cfg.get("temperature")        # None = provider default
        self.extra = cfg.get("extra") or {}
        self.http = http
        # optional requests-per-minute ceiling, for free tiers
        self.min_gap = 60.0 / float(cfg["rpm"]) if cfg.get("rpm") else 0.0
        self._lock, self._next = threading.Lock(), 0.0

    def _wait_turn(self):
        if not self.min_gap:
            return
        with self._lock:
            now = time.time()
            start = max(now, self._next)
            self._next = start + self.min_gap
        time.sleep(max(0.0, start - now))

    @property
    def ready(self):
        return bool(self.key) and "<" not in self.model

    def chat(self, messages, tries=3):
        body = {"model": self.model, "messages": messages, "max_tokens": self.max_tokens}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if "openrouter.ai" in self.base_url:
            body["usage"] = {"include": True}
        body.update(self.extra)
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
                   "X-Title": "ResolveBench"}
        t0, err = time.time(), None
        for i in range(tries):
            self._wait_turn()
            try:
                status, data = self.http.post_json(self.base_url + "/chat/completions", body, headers)
                if isinstance(data, list):  # Gemini returns errors as a JSON list [{"error": ...}]
                    data = data[0] if data and isinstance(data[0], dict) else {"error": data}
                if not isinstance(data, dict):
                    data = {"error": data}
                if status == 200 and data.get("choices"):
                    msg = data["choices"][0].get("message") or {}
                    text = msg.get("content") or ""
                    if isinstance(text, list):  # some providers return content parts
                        text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
                    u = data.get("usage") or {}
                    tin, tout = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
                    cost = u.get("cost")
                    if cost is None:
                        cost = tin * self.price_in / 1e6 + tout * self.price_out / 1e6
                    return {"text": text, "tok_in": tin, "tok_out": tout, "cost": float(cost),
                            "latency": time.time() - t0, "error": None if text else "empty_content"}
                err = f"HTTP {status}: {str(data.get('error') or data)[:300]}"
                if status in (400, 401, 402, 403, 404):
                    break  # will not get better by retrying
                if status == 429:  # rate limited: wait longer before the next try
                    time.sleep(min(60, 15 * 2 ** i))
            except Exception as e:
                err = repr(e)[:300]
            time.sleep(min(30, 2 * 2 ** i) + random.random())
        return {"text": "", "tok_in": 0, "tok_out": 0, "cost": 0.0, "latency": time.time() - t0, "error": err}

    def list_models(self):
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        return self.http.get_json(self.base_url + "/models", tries=2, headers=headers)
