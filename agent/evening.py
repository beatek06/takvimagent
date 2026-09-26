"""Akşam özetini Telegram'a gönderir. Pazar günleri 2 haftalık boşluk kontrolünü de ekler.

Tetikleyiciler: Cloudflare Worker cron'u (asıl, dakikası dakikasına) ve GitHub cron'u (yedek,
GitHub bunu saatlerce geciktirebiliyor). İkisi de UTC'de çalıştığı için yaz/kış saatine bakmadan
her gün birkaç kez tetiklenir; burada şu kurallar uygulanır:
  - Zürih saati 19:00-23:59 arasında değilse hiçbir şey yapılmaz.
  - O gün için özet zaten gönderildiyse (AJAN_LOG'daki işaret) tekrar gönderilmez.
FORCE=1 ile (elle çalıştırmada) bu kontroller atlanır ve işaret bırakılmaz.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

SEND_FROM_HOUR = 19
SEND_UNTIL_HOUR = 23


def in_send_window(now):
    return SEND_FROM_HOUR <= now.hour <= SEND_UNTIL_HOUR


def main():
    now = datetime.now(ZoneInfo("Europe/Zurich"))
    force = os.environ.get("FORCE") == "1"
    if not force and not in_send_window(now):
        print(f"Zürih saati {now:%H:%M}, gönderim penceresi dışında; çıkılıyor.")
        return

    from agent import memory
    from agent.calendar_sheet import read_days
    from agent import sheets
    from agent.summary import evening_message, gap_message
    from agent.telegram import send_message

    key = f"evening:{now.date().isoformat()}"
    if not force and memory.already_sent(sheets, key):
        print("Bugünkü özet zaten gönderilmiş; çıkılıyor.")
        return

    days = read_days(sheets.get_values("TAKVIM"))
    text = evening_message(days, now.date())
    if now.weekday() == 6:  # Pazar
        text += "\n\n" + gap_message(days, now.date())
    send_message(text)
    if not force:
        memory.mark_sent(sheets, now, key)
    print("Özet gönderildi.")


if __name__ == "__main__":
    main()
