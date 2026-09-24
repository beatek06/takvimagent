"""Modelin dosyadaki HER sekmede kullandığı genel araçlar: sekmeleri listele, aralık oku, hücre yaz.

Güvenlik: yazmadan önce eski değerler okunup değişiklik günlüğüne eklenir (geri alınabilsin),
tek seferde yazılabilecek hücre sayısı sınırlıdır ve AJAN_LOG sekmesi korumalıdır.
"""
import re

PROTECTED_TABS = {"AJAN_LOG"}
MAX_CELLS = 40
MAX_READ_ROWS = 150
CELL_RE = re.compile(r"^[A-Za-z]{1,3}[0-9]{1,5}$")

TOOL_DECLARATIONS = [
    {
        "name": "list_tabs",
        "description": "Dosyadaki tüm sekmelerin adını ve boyutunu listeler.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "read_range",
        "description": (
            "Bir sekmedeki hücre aralığını okur (örn. tab='KASA', cells='A1:H40'). "
            "mode='formulas' formülleri, mode='values' görünen değerleri döndürür."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tab": {"type": "STRING", "description": "Sekme adı, tam olarak"},
                "cells": {"type": "STRING", "description": "A1 aralığı, örn. A1:H40"},
                "mode": {"type": "STRING", "description": "'values' (varsayılan) veya 'formulas'"},
            },
            "required": ["tab", "cells"],
        },
    },
    {
        "name": "write_cells",
        "description": (
            "Bir sekmede tek tek hücrelere değer yazar. Yazmadan önce ilgili aralığı read_range ile oku; "
            "sadece istenen hücreleri değiştir. Sayılar sayı, '=' ile başlayanlar formül olarak yorumlanır."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tab": {"type": "STRING"},
                "updates": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "cell": {"type": "STRING", "description": "Tek hücre, örn. B5"},
                            "value": {"type": "STRING"},
                        },
                        "required": ["cell", "value"],
                    },
                },
            },
            "required": ["tab", "updates"],
        },
    },
]


class SheetTools:
    def __init__(self, api):
        """api: list_tabs, get_values, batch_get, update_cells fonksiyonlarını sağlayan modül/nesne."""
        self.api = api
        self.changes = []

    def _known_tab(self, tab):
        titles = [t["title"] for t in self.api.list_tabs()]
        if tab not in titles:
            return {"error": f"'{tab}' adlı sekme yok. Mevcut sekmeler: {', '.join(titles)}"}
        return None

    def list_tabs(self):
        return {"tabs": self.api.list_tabs()}

    def read_range(self, tab, cells, mode="values"):
        err = self._known_tab(tab)
        if err:
            return err
        render = "FORMULA" if mode == "formulas" else "FORMATTED_VALUE"
        rows = self.api.get_values(tab, cells, render=render)
        return {
            "tab": tab,
            "cells": cells,
            "rows": rows[:MAX_READ_ROWS],
            "truncated": len(rows) > MAX_READ_ROWS,
        }

    def write_cells(self, tab, updates):
        if tab in PROTECTED_TABS:
            return {"error": f"'{tab}' sekmesi korumalı, değiştirilemez."}
        if not updates:
            return {"error": "Yazılacak hücre verilmedi."}
        if len(updates) > MAX_CELLS:
            return {"error": f"Bir seferde en fazla {MAX_CELLS} hücre yazılabilir; işi parçalara böl."}
        cells = []
        for u in updates:
            cell = str(u.get("cell", "")).strip().upper()
            if not CELL_RE.match(cell):
                return {"error": f"Geçersiz hücre adresi: {u.get('cell')!r}. Tek hücre gerekli (örn. B5)."}
            cells.append((cell, str(u.get("value", ""))))
        err = self._known_tab(tab)
        if err:
            return err
        old = self.api.batch_get(tab, [c for c, _ in cells], render="FORMULA")
        self.api.update_cells(tab, cells, input_option="USER_ENTERED")
        result = []
        for (cell, new), before in zip(cells, old):
            self.changes.append(f"{tab}!{cell}: '{before}' -> '{new}'")
            result.append({"cell": cell, "old": before, "new": new})
        return {"changed": result}

    def call(self, name, args):
        try:
            if name == "list_tabs":
                return self.list_tabs()
            if name == "read_range":
                return self.read_range(args["tab"], args["cells"], args.get("mode", "values"))
            if name == "write_cells":
                return self.write_cells(args["tab"], args["updates"])
        except KeyError as e:
            return {"error": f"Eksik parametre: {e}"}
        return None  # başka araç setine ait
