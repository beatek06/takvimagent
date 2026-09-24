"""Bota yazılmış son mesajlardan chat ID'yi bulur. Token'ı ekrana yazmaz.

Token .env dosyasından okunur (TELEGRAM_BOT_TOKEN=...). .env gitignore'dadır.
Önce Telegram'dan bota bir mesaj yaz, sonra: python dev/get_chat_id.py
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

env = Path(__file__).parent.parent / ".env"
token = None
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")

if not token:
    sys.exit(".env içinde TELEGRAM_BOT_TOKEN=... satırı yok ya da boş.")

try:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20) as r:
        data = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Telegram hata döndürdü: HTTP {e.code} (401 ise token yanlış kopyalanmış)")

seen = {}
for u in data.get("result", []):
    chat = (u.get("message") or {}).get("chat")
    if chat and chat.get("type") == "private":
        seen[chat["id"]] = chat.get("first_name") or chat.get("username") or "?"

if not seen:
    sys.exit("Henüz mesaj yok. Telegram'dan @YunusTakvim_bot'a bir mesaj yaz ve tekrar çalıştır.")
for cid, name in seen.items():
    print(f"chat id: {cid}  (ad: {name})")
