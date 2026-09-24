"""Telegram webhook'unu Cloudflare Worker adresine yönlendirir. Kullanım: python -m agent.set_webhook <worker_url>"""
import os
import re
import sys
import urllib.error

from agent.telegram import set_webhook

if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        sys.exit("Worker adresi https:// ile başlamalı (örn. https://takvim-relay.xxx.workers.dev).")
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not secret:
        sys.exit("TELEGRAM_WEBHOOK_SECRET secret'ı boş ya da GitHub'da tanımlı değil.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", secret):
        sys.exit("TELEGRAM_WEBHOOK_SECRET sadece harf, rakam, _ ve - içerebilir (boşluk/nokta olmaz).")
    try:
        print(set_webhook(sys.argv[1], secret))
    except urllib.error.HTTPError as e:
        # Telegram'ın hata açıklaması token içermez.
        sys.exit(f"Telegram hata döndürdü: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
