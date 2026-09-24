"""Akşam özetini Telegram'a gönderir. Pazar günleri 2 haftalık boşluk kontrolünü de ekler.

GitHub Actions cron'u UTC çalıştığı için workflow hem 17:00 hem 18:00 UTC'de tetiklenir;
burada Zürih saatinin 19 olup olmadığına bakılır, değilse hiçbir şey yapılmaz.
FORCE=1 ile (elle çalıştırmada) bu kontrol atlanır.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

SEND_HOUR = 19


def main():
    now = datetime.now(ZoneInfo("Europe/Zurich"))
    if os.environ.get("FORCE") != "1" and now.hour != SEND_HOUR:
        print(f"Zürih saati {now:%H:%M}, gönderim saati değil; çıkılıyor.")
        return

    from agent.calendar_sheet import read_days
    from agent.sheets import get_values
    from agent.summary import evening_message, gap_message
    from agent.telegram import send_message

    days = read_days(get_values("TAKVIM"))
    text = evening_message(days, now.date())
    if now.weekday() == 6:  # Pazar
        text += "\n\n" + gap_message(days, now.date())
    send_message(text)
    print("Özet gönderildi.")


if __name__ == "__main__":
    main()
