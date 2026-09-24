"""Sohbet hafızası ve değişiklik günlüğü: Sheets'te AJAN_LOG sekmesi (A: zaman, B: rol, C: metin).

Roller: user (senin mesajın), bot (cevabı), change (yapılan hücre değişikliği: eski -> yeni).
Yanlış bir değişikliği bu sekmedeki eski değerlerden geri alabilirsin.
"""
LOG_TAB = "AJAN_LOG"
HISTORY_TURNS = 8


def load_history(sheets, limit=HISTORY_TURNS):
    sheets.ensure_tab(LOG_TAB)
    rows = sheets.get_values(LOG_TAB, "A1:C3000", render="FORMATTED_VALUE")
    turns = [(r[1], r[2]) for r in rows if len(r) >= 3 and r[1] in ("user", "bot")]
    return turns[-limit:]


def log(sheets, now, rows):
    """rows: [(rol, metin), ...]"""
    sheets.ensure_tab(LOG_TAB)
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    sheets.append_rows(LOG_TAB, [[stamp, role, text] for role, text in rows])
