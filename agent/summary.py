"""Akşam özeti ve pazar boşluk kontrolü için mesaj metinleri. Model gerektirmez."""
from datetime import timedelta

from agent.calendar_sheet import empty_days, missing_days

DAY_ABBR = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")
MONTH_ABBR = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
HORIZON_DAYS = 14


def label(d):
    return f"{DAY_ABBR[d.weekday()]} {d.day} {MONTH_ABBR[d.month - 1]}"


def _note(d, days):
    if d not in days:
        return "⚠️ takvimde yok"
    return days[d] or "—"


def _lines(dates, days):
    return "\n".join(f"{label(d)}: {_note(d, days)}" for d in dates)


def evening_message(days, today):
    """Yarın, yarından cumaya kalan günler ve hafta sonu."""
    tomorrow = today + timedelta(days=1)
    monday = tomorrow - timedelta(days=tomorrow.weekday())
    rest_of_week = [tomorrow + timedelta(days=k) for k in range(1, 5 - tomorrow.weekday())]
    weekend = [d for d in (monday + timedelta(days=5), monday + timedelta(days=6)) if d > tomorrow]

    parts = [f"📅 Yarın: {label(tomorrow)}\n{_note(tomorrow, days)}"]
    if rest_of_week:
        parts.append(f"🗓 Hafta sonuna kadar\n{_lines(rest_of_week, days)}")
    if weekend:
        parts.append(f"🏖 Hafta sonu\n{_lines(weekend, days)}")
    return "\n\n".join(parts)


def gap_message(days, today):
    """Yarından itibaren 14 gün içinde notu boş veya takvimde hücresi olmayan günler."""
    start, end = today + timedelta(days=1), today + timedelta(days=HORIZON_DAYS)
    empty = empty_days(days, start, end)
    missing = missing_days(days, start, end)
    if not empty and not missing:
        return "✅ Önümüzdeki 2 hafta tamamen dolu."
    parts = ["🔔 Pazar kontrolü: önümüzdeki 2 haftada planı boş günler var."]
    if empty:
        parts.append("Boş: " + ", ".join(label(d) for d in empty))
    if missing:
        parts.append("Takvimde henüz hücresi olmayan: " + ", ".join(label(d) for d in missing))
    return "\n".join(parts)
