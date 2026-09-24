"""Telegram Bot API ile mesaj gönderme. Token ve chat ID ortam değişkenlerinden okunur."""
import json
import os
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"


def _call(method, payload, token=None):
    token = token or os.environ["TELEGRAM_BOT_TOKEN"]
    req = urllib.request.Request(
        API.format(token=token, method=method),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def send_message(text, chat_id=None, token=None):
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]
    return _call("sendMessage", {"chat_id": chat_id, "text": text[:4000]}, token)


def send_chat_action(action="typing", chat_id=None, token=None):
    """Sohbette 'yazıyor…' göstergesi (yaklaşık 5 saniye görünür)."""
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]
    return _call("sendChatAction", {"chat_id": chat_id, "action": action}, token)


def set_webhook(url, secret_token, token=None):
    return _call(
        "setWebhook",
        {
            "url": url,
            "secret_token": secret_token,
            "allowed_updates": ["message"],
            "drop_pending_updates": True,
        },
        token,
    )
