"""Telegram bağlantısını sınamak için tek seferlik test mesajı gönderir."""
from agent.telegram import send_message

if __name__ == "__main__":
    send_message("Takvim ajanı GitHub Actions'tan bağlandı. Bu bir test mesajıdır.")
    print("Mesaj gönderildi.")
