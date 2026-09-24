"""Telegram Bot API ile mesaj gönderme. Token ve chat ID ortam değişkenlerinden okunur."""
import json
import os
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"


def send_message(text, chat_id=None, token=None):
    token = token or os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]
    req = urllib.request.Request(
        API.format(token=token, method="sendMessage"),
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)
