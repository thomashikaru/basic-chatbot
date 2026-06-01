#!/usr/bin/env python3
"""Minimal static file server + LLM API proxy (Hyperbolic & OpenRouter)."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent

HYPERBOLIC_CHAT_URL = "https://api.hyperbolic.xyz/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

HYPERBOLIC_DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
OPENROUTER_DEFAULT_MODEL = "openai/gpt-4o-mini"

HYPERBOLIC_MODELS = [
    {"id": "meta-llama/Llama-3.3-70B-Instruct", "label": "Llama 3.3 70B Instruct"},
    {"id": "deepseek-ai/DeepSeek-V3-0324", "label": "DeepSeek V3 0324"},
    {"id": "deepseek-ai/DeepSeek-R1", "label": "DeepSeek R1"},
    {"id": "deepseek-ai/DeepSeek-R1-0528", "label": "DeepSeek R1 0528"},
    {"id": "Qwen/Qwen3-Coder-480B-A35B-Instruct", "label": "Qwen3 Coder 480B"},
]
HYPERBOLIC_MODEL_IDS = {m["id"] for m in HYPERBOLIC_MODELS}

# Cloudflare blocks Python-urllib's default User-Agent (error 1010).
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

_openrouter_cache: dict = {"models": [], "ids": set(), "fetched_at": 0.0}
_OPENROUTER_CACHE_TTL = 300  # seconds


def hyperbolic_key() -> str:
    return os.environ.get("HYPERBOLIC_API_KEY", "").strip()


def openrouter_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def configured_providers() -> list[dict]:
    providers = []
    if hyperbolic_key():
        providers.append({"id": "hyperbolic", "label": "Hyperbolic"})
    if openrouter_key():
        providers.append({"id": "openrouter", "label": "OpenRouter"})
    return providers


def fetch_openrouter_models(key: str) -> list[dict]:
    now = time.time()
    if _openrouter_cache["models"] and now - _openrouter_cache["fetched_at"] < _OPENROUTER_CACHE_TTL:
        return _openrouter_cache["models"]

    req = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={**REQUEST_HEADERS, "Authorization": f"Bearer {key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())

    models = []
    for item in data.get("data", []):
        model_id = item.get("id")
        if not model_id:
            continue
        label = item.get("name") or model_id
        models.append({"id": model_id, "label": label})

    models.sort(key=lambda m: m["label"].lower())
    _openrouter_cache["models"] = models
    _openrouter_cache["ids"] = {m["id"] for m in models}
    _openrouter_cache["fetched_at"] = now
    return models


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/providers":
            providers = configured_providers()
            default = providers[0]["id"] if providers else None
            self._json(200, {"providers": providers, "default": default})
            return

        if parsed.path == "/api/models":
            params = urllib.parse.parse_qs(parsed.query)
            provider = (params.get("provider") or [""])[0]
            if provider == "hyperbolic":
                if not hyperbolic_key():
                    self._json(500, {"error": "Set HYPERBOLIC_API_KEY in your environment."})
                    return
                self._json(
                    200,
                    {"models": HYPERBOLIC_MODELS, "default": HYPERBOLIC_DEFAULT_MODEL},
                )
                return
            if provider == "openrouter":
                key = openrouter_key()
                if not key:
                    self._json(500, {"error": "Set OPENROUTER_API_KEY in your environment."})
                    return
                try:
                    models = fetch_openrouter_models(key)
                except urllib.error.HTTPError as e:
                    self._json(e.code, {"error": "OpenRouter API error", "detail": _read_error(e)})
                    return
                except urllib.error.URLError as e:
                    self._json(502, {"error": str(e.reason)})
                    return
                default = OPENROUTER_DEFAULT_MODEL
                if default not in _openrouter_cache["ids"] and models:
                    default = models[0]["id"]
                self._json(200, {"models": models, "default": default})
                return
            self._json(400, {"error": "Unknown or missing provider."})
            return

        super().do_GET()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._json(400, {"error": "Invalid JSON body."})
            return

        messages = body.get("messages")
        if not messages:
            self._json(400, {"error": "Missing 'messages' in request body."})
            return

        provider = body.get("provider", "hyperbolic")
        model = body.get("model")

        if provider == "hyperbolic":
            self._chat_hyperbolic(model, messages)
        elif provider == "openrouter":
            self._chat_openrouter(model, messages)
        else:
            self._json(400, {"error": f"Unknown provider: {provider}"})

    def _chat_hyperbolic(self, model: str | None, messages: list):
        key = hyperbolic_key()
        if not key:
            self._json(500, {"error": "Set HYPERBOLIC_API_KEY in your environment."})
            return

        model = model or HYPERBOLIC_DEFAULT_MODEL
        if model not in HYPERBOLIC_MODEL_IDS:
            self._json(400, {"error": f"Unknown model: {model}"})
            return

        payload = {"model": model, "messages": messages, "stream": True}
        req = urllib.request.Request(
            HYPERBOLIC_CHAT_URL,
            data=json.dumps(payload).encode(),
            headers={**REQUEST_HEADERS, "Authorization": f"Bearer {key}"},
            method="POST",
        )
        self._proxy_stream(req, "Hyperbolic")

    def _chat_openrouter(self, model: str | None, messages: list):
        key = openrouter_key()
        if not key:
            self._json(500, {"error": "Set OPENROUTER_API_KEY in your environment."})
            return

        try:
            fetch_openrouter_models(key)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            self._json(502, {"error": f"Could not load OpenRouter models: {e}"})
            return

        model = model or OPENROUTER_DEFAULT_MODEL
        if model not in _openrouter_cache["ids"]:
            self._json(400, {"error": f"Unknown model: {model}"})
            return

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        headers = {
            **REQUEST_HEADERS,
            "Authorization": f"Bearer {key}",
            "X-OpenRouter-Experimental-Metadata": "enabled",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "basic-chatbot",
        }
        req = urllib.request.Request(
            OPENROUTER_CHAT_URL,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        self._proxy_stream(req, "OpenRouter")

    def _proxy_stream(self, req: urllib.request.Request, label: str):
        try:
            resp = urllib.request.urlopen(req, timeout=300)
        except urllib.error.HTTPError as e:
            detail = _read_error(e)
            print(f"{label} API {e.code}: {detail}", flush=True)
            self._json(e.code, {"error": f"{label} API error", "detail": detail})
            return
        except urllib.error.URLError as e:
            self._json(502, {"error": str(e.reason)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            self._forward_sse_stream(resp)
        finally:
            resp.close()
            self._sse_done()

    def _forward_sse_stream(self, resp):
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if chunk.get("object") == "error":
                self._sse({"error": chunk.get("message", "Unknown error")})
                break
            if chunk.get("error"):
                err = chunk["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                self._sse({"error": msg})
                break
            choices = chunk.get("choices") or []
            if not choices:
                continue
            content = choices[0].get("delta", {}).get("content")
            if content:
                self._sse({"content": content})

    def _sse(self, obj: dict):
        payload = f"data: {json.dumps(obj)}\n\n".encode()
        self.wfile.write(payload)
        self.wfile.flush()

    def _sse_done(self):
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _json(self, status: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _read_error(e: urllib.error.HTTPError):
    raw = e.read().decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    providers = configured_providers()
    if not providers:
        print("Note: set HYPERBOLIC_API_KEY and/or OPENROUTER_API_KEY.")
    else:
        names = ", ".join(p["label"] for p in providers)
        print(f"Providers: {names}")
    print(f"Open http://localhost:{port}")
    HTTPServer(("", port), Handler).serve_forever()
