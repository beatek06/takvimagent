"""Modelin kullandığı takvim araçları.

Yazma yalnızca gün-not hücrelerine yapılır: model istese de başlıklara, tarih satırlarına
veya diğer bölümlere dokunamaz, çünkü adresler ızgaradan bu sınıf tarafından hesaplanır.
"""
import re
from datetime import date

from agent.calendar_sheet import col_letter, iter_days

MAX_WRITES = 60

TOOL_DECLARATIONS = [
    {
        "name": "get_days",
        "description": "Belirli bir tarih aralığındaki günlerin notlarını okur.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "start_date": {"type": "STRING", "description": "YYYY-MM-DD"},
                "end_date": {"type": "STRING", "description": "YYYY-MM-DD (dahil)"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "set_note",
        "description": "Bir günün notunu tamamen değiştirir. Boş metin notu siler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date": {"type": "STRING", "description": "YYYY-MM-DD"},
                "note": {"type": "STRING", "description": "Yeni not, çok kısa"},
            },
            "required": ["date", "note"],
        },
    },
    {
        "name": "add_to_note",
        "description": "Bir günün mevcut notunu koruyup sonuna ' - ' ile yeni metin ekler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date": {"type": "STRING", "description": "YYYY-MM-DD"},
                "text": {"type": "STRING", "description": "Eklenecek kısa metin"},
            },
            "required": ["date", "text"],
        },
    },
    {
        "name": "replace_text",
        "description": (
            "Günlerin notlarında bir metni bulup başkasıyla değiştirir (büyük/küçük harf fark etmez). "
            "İsim düzeltmeleri gibi toplu işler için. Tarih aralığı verilmezse tüm takvimde çalışır."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "find": {"type": "STRING"},
                "replace": {"type": "STRING"},
                "start_date": {"type": "STRING", "description": "YYYY-MM-DD, isteğe bağlı"},
                "end_date": {"type": "STRING", "description": "YYYY-MM-DD, isteğe bağlı"},
            },
            "required": ["find", "replace"],
        },
    },
]


class CalendarTools:
    def __init__(self, grid, write, tab="TAKVIM"):
        """write: [(a1_hücre, değer), ...] alıp sekmeye yazan fonksiyon."""
        self.tab = tab
        self._write = write
        self.days, self.where = {}, {}
        for d, note, r, c in iter_days(grid):
            self.days[d], self.where[d] = note, (r, c)
        self.changes = []

    # -- yardımcılar ---------------------------------------------------------
    @staticmethod
    def _parse(s):
        try:
            return date.fromisoformat(str(s))
        except ValueError:
            return None

    def _apply(self, updates):
        """updates: {tarih: yeni_not}. Hepsini tek istekte yazar ve değişiklik günlüğüne ekler."""
        if len(updates) > MAX_WRITES:
            return {"error": f"Bir seferde en fazla {MAX_WRITES} gün değiştirilebilir; aralığı daralt."}
        cells = []
        for d, new in updates.items():
            r, c = self.where[d]
            cells.append((f"{col_letter(c)}{r + 1}", new))
        self._write(cells)
        result = []
        for d, new in updates.items():
            old = self.days[d]
            self.days[d] = new or None
            self.changes.append(f"{d.isoformat()}: '{old or ''}' -> '{new}'")
            result.append({"date": d.isoformat(), "old": old or "", "new": new})
        return {"changed": result}

    def _day_or_error(self, s):
        d = self._parse(s)
        if d is None:
            return None, {"error": f"Geçersiz tarih: {s!r}. YYYY-MM-DD biçimi gerekli."}
        if d not in self.days:
            return None, {"error": f"{d.isoformat()} takvimde yok (ilgili ay henüz eklenmemiş)."}
        return d, None

    # -- araçlar -------------------------------------------------------------
    def get_days(self, start_date, end_date):
        a, b = self._parse(start_date), self._parse(end_date)
        if a is None or b is None:
            return {"error": "Geçersiz tarih; YYYY-MM-DD biçimi gerekli."}
        return {
            "days": [
                {"date": d.isoformat(), "weekday": d.strftime("%A"), "note": self.days[d] or ""}
                for d in sorted(self.days)
                if a <= d <= b
            ]
        }

    def set_note(self, day, note):
        d, err = self._day_or_error(day)
        return err or self._apply({d: str(note).strip()})

    def add_to_note(self, day, text):
        d, err = self._day_or_error(day)
        if err:
            return err
        old = self.days[d]
        text = str(text).strip()
        return self._apply({d: f"{old} - {text}" if old else text})

    def replace_text(self, find, replace, start_date=None, end_date=None):
        if not find:
            return {"error": "Aranacak metin boş olamaz."}
        a = self._parse(start_date) if start_date else None
        b = self._parse(end_date) if end_date else None
        pattern = re.compile(re.escape(find), re.IGNORECASE)
        updates = {}
        for d in sorted(self.days):
            note = self.days[d]
            if not note or (a and d < a) or (b and d > b):
                continue
            new = pattern.sub(lambda _: replace, note)
            if new != note:
                updates[d] = new
        if not updates:
            return {"changed": [], "message": "Eşleşen not bulunamadı."}
        return self._apply(updates)

    def call(self, name, args):
        try:
            if name == "get_days":
                return self.get_days(args["start_date"], args["end_date"])
            if name == "set_note":
                return self.set_note(args["date"], args["note"])
            if name == "add_to_note":
                return self.add_to_note(args["date"], args["text"])
            if name == "replace_text":
                return self.replace_text(
                    args["find"], args["replace"], args.get("start_date"), args.get("end_date")
                )
        except KeyError as e:
            return {"error": f"Eksik parametre: {e}"}
        return None  # başka araç setine ait
