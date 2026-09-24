"""Gemini API (generateContent) istemcisi, araç çağırma destekli."""
import os

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash-lite")
FALLBACK_STATUSES = (404, 429, 500, 503)


def generate(system, contents, tool_declarations):
    """Sıradaki modeli dener; model yok/kota dolu/aşırı yüklü ise bir sonrakine geçer."""
    key = os.environ["GEMINI_API_KEY"]
    models = list(dict.fromkeys(m for m in (os.environ.get("GEMINI_MODEL"), *DEFAULT_MODELS) if m))
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "tools": [{"functionDeclarations": tool_declarations}],
        "generationConfig": {"temperature": 0.2},
    }
    last = "model denenemedi"
    for model in models:
        r = requests.post(
            URL.format(model=model), headers={"x-goog-api-key": key}, json=body, timeout=90
        )
        if r.ok:
            return r.json()
        last = f"{model}: HTTP {r.status_code} {r.text[:300]}"
        print("Gemini hatası:", last)
        if r.status_code not in FALLBACK_STATUSES:
            break
    raise RuntimeError(f"Gemini çağrısı başarısız. Son hata: {last}")
