#!/usr/bin/env python3
"""Minimal static file server + Hyperbolic API proxy."""

import json
import os
import urllib.error
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent
HYPERBOLIC_URL = "https://api.hyperbolic.xyz/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
MODELS = [
    {"id": "meta-llama/Llama-3.3-70B-Instruct", "label": "Llama 3.3 70B Instruct"},
    {"id": "deepseek-ai/DeepSeek-V3-0324", "label": "DeepSeek V3 0324"},
    {"id": "deepseek-ai/DeepSeek-R1", "label": "DeepSeek R1"},
    {"id": "deepseek-ai/DeepSeek-R1-0528", "label": "DeepSeek R1 0528"},
    {"id": "Qwen/Qwen3-Coder-480B-A35B-Instruct", "label": "Qwen3 Coder 480B"},
]
ALLOWED_MODEL_IDS = {m["id"] for m in MODELS}
# Cloudflare blocks Python-urllib's default User-Agent (error 1010).
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def api_key() -> str:
    return os.environ.get("HYPERBOLIC_API_KEY", "").strip()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/api/models":
            self._json(200, {"models": MODELS, "default": DEFAULT_MODEL})
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        key = api_key()
        if not key:
            self._json(500, {"error": "Set HYPERBOLIC_API_KEY in your environment."})
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

        model = body.get("model", DEFAULT_MODEL)
        if model not in ALLOWED_MODEL_IDS:
            self._json(400, {"error": f"Unknown model: {model}"})
            return

        payload = {"model": model, "messages": messages}

        req = urllib.request.Request(
            HYPERBOLIC_URL,
            data=json.dumps(payload).encode(),
            headers={
                **REQUEST_HEADERS,
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                detail = json.loads(raw)
            except json.JSONDecodeError:
                detail = raw
            print(f"Hyperbolic API {e.code}: {detail}", flush=True)
            self._json(e.code, {"error": "Hyperbolic API error", "detail": detail})
            return
        except urllib.error.URLError as e:
            self._json(502, {"error": str(e.reason)})
            return

        reply = data["choices"][0]["message"]["content"]
        self._json(200, {"reply": reply})

    def _json(self, status: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    if not api_key():
        print("Note: HYPERBOLIC_API_KEY is not set yet.")
    print(f"Open http://localhost:{port}")
    HTTPServer(("", port), Handler).serve_forever()
