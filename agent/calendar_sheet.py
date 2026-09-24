"""TAKVIM sekmesinin ızgarasını (satır/sütun listesi) gün -> not sözlüğüne çevirir.

Sekme düzeni:
  - Ay başlığı gerçek bir tarih hücresidir (örn. B17 = 1 Eylül 2026).
  - Hemen altındaki satırda 7 sütun boyunca Pazartesi..Pazar yazar.
  - Sonra haftalar ikişer satırdır: üstte gün numarası, altında o günün notu.
  - Aylar yan yana (7 sütun) ve alta doğru bantlar hâlinde dizilir.

Izgara, Sheets API'nin values.get (UNFORMATTED_VALUE) çıktısı gibi, satır listelerinden
oluşan bir listedir; satır sonlarındaki boş hücreler eksik olabilir.
"""
from datetime import date, timedelta

EPOCH = date(1899, 12, 30)  # Sheets / Excel seri tarih başlangıcı
WEEKDAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
MAX_WEEKS = 6


def _cell(grid, r, c):
    row = grid[r] if 0 <= r < len(grid) else []
    v = row[c] if 0 <= c < len(row) else None
    if isinstance(v, str):
        v = v.strip()
    return None if v in ("", None) else v


def _as_date(v):
    # Seri tarih olarak 40000..60000 (2009..2064) arası; gün numaraları (1..31) ile karışmaz.
    if isinstance(v, (int, float)) and 40000 < v < 60000:
        return EPOCH + timedelta(days=int(v))
    return None


def find_month_blocks(grid):
    """Her ay bloğu için (satır, sütun, ayın_ilk_günü) döndürür (0 tabanlı konum)."""
    blocks = []
    for r in range(len(grid) - 1):
        for c in range(len(grid[r])):
            d = _as_date(_cell(grid, r, c))
            if d is None:
                continue
            if all(_cell(grid, r + 1, c + i) == WEEKDAYS[i] for i in range(7)):
                blocks.append((r, c, d.replace(day=1)))
    return blocks


def iter_days(grid):
    """Her gün için (tarih, not, not_satırı, not_sütunu) verir; konumlar 0 tabanlıdır."""
    for r, c, first in find_month_blocks(grid):
        for w in range(MAX_WEEKS):
            date_row = r + 2 + 2 * w
            for i in range(7):
                n = _cell(grid, date_row, c + i)
                if not isinstance(n, (int, float)) or not 1 <= n <= 31 or n != int(n):
                    continue
                try:
                    d = first.replace(day=int(n))
                except ValueError:
                    raise ValueError(
                        f"{first:%Y-%m} bloğunda geçersiz gün numarası {int(n)} "
                        f"(satır {date_row + 1}, sütun {c + i + 1})"
                    )
                note = _cell(grid, date_row + 1, c + i)
                yield d, (None if note is None else str(note)), date_row + 1, c + i


def read_days(grid):
    """Tüm ay bloklarından {tarih: not} döndürür. Not yoksa None."""
    return {d: note for d, note, _, _ in iter_days(grid)}


def col_letter(c):
    """0 tabanlı sütun numarasını A1 harfine çevirir (0 -> A, 26 -> AA)."""
    s, c = "", c + 1
    while c:
        c, rem = divmod(c - 1, 26)
        s = chr(65 + rem) + s
    return s


def _daterange(start, end):
    for k in range((end - start).days + 1):
        yield start + timedelta(days=k)


def empty_days(days, start, end):
    """[start, end] içinde takvimde bulunan ama notu boş olan günler."""
    return [d for d in _daterange(start, end) if d in days and not days[d]]


def missing_days(days, start, end):
    """[start, end] içinde takvimde hiç hücresi olmayan günler (ay henüz eklenmemiş)."""
    return [d for d in _daterange(start, end) if d not in days]
