"""Sohbet hafızası, değişiklik günlüğü ve 'gönderildi' işaretleri: Sheets'te AJAN_LOG sekmesi.

Sütunlar: A zaman, B rol, C metin. Roller:
  user    senin mesajın            bot     ajanın cevabı
  change  hücre değişikliği (eski -> yeni); yanlış bir düzenlemeyi buradan geri alabilirsin
  sent    zamanlanmış mesajın o gün gönderildiği işareti (tekrar gönderimi önler)
"""
LOG_TAB = "AJAN_LOG"
HISTORY_TURNS = 8


def _rows(sheets):
    sheets.ensure_tab(LOG_TAB)
    # Tüm sütun okunur ki günlük uzadıkça en yeni satırlar dışarıda kalmasın.
    return sheets.get_values(LOG_TAB, "A:C", render="FORMATTED_VALUE")


def load_history(sheets, limit=HISTORY_TURNS):
    turns = [(r[1], r[2]) for r in _rows(sheets) if len(r) >= 3 and r[1] in ("user", "bot")]
    return turns[-limit:]


def log(sheets, now, rows):
    """rows: [(rol, metin), ...]"""
    sheets.ensure_tab(LOG_TAB)
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    sheets.append_rows(LOG_TAB, [[stamp, role, text] for role, text in rows])


def already_sent(sheets, key):
    return any(len(r) >= 3 and r[1] == "sent" and r[2] == key for r in _rows(sheets))


def mark_sent(sheets, now, key):
    log(sheets, now, [("sent", key)])
