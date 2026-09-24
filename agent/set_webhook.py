"""Telegram webhook'unu Cloudflare Worker adresine yönlendirir. Kullanım: python -m agent.set_webhook <worker_url>"""
import os
import sys

from agent.telegram import set_webhook

if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        sys.exit("Kullanım: python -m agent.set_webhook https://...workers.dev")
    print(set_webhook(sys.argv[1], os.environ["TELEGRAM_WEBHOOK_SECRET"]))
