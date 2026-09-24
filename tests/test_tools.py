import json
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from agent import calendar_tools, sheet_tools
from agent.calendar_sheet import col_letter
from agent.calendar_tools import CalendarTools
from agent.chat import Toolbox, build_system, run_agent
from agent.sheet_tools import SheetTools

FIXTURE = Path(__file__).parent.parent / "dev" / "fixtures" / "takvim.json"


class FakeApi:
    def __init__(self):
        self.tabs = [
            {"title": "KASA", "rows": 50, "columns": 10},
            {"title": "AJAN_LOG", "rows": 100, "columns": 3},
        ]
        self.cells = {"B5": "100", "C5": "=B5*2"}
        self.updates = []

    def list_tabs(self):
        return self.tabs

    def get_values(self, tab, cells, render="UNFORMATTED_VALUE"):
        return [["x", "y"]] * 200

    def batch_get(self, tab, cells, render="FORMULA"):
        return [self.cells.get(c, "") for c in cells]

    def update_cells(self, tab, updates, input_option="RAW"):
        self.updates.append((tab, updates, input_option))


class ColLetterTests(unittest.TestCase):
    def test_letters(self):
        self.assertEqual([col_letter(i) for i in (0, 7, 25, 26, 27)], ["A", "H", "Z", "AA", "AB"])


@unittest.skipUnless(FIXTURE.exists(), "dev/fixtures/takvim.json yok")
class CalendarToolsTests(unittest.TestCase):
    def setUp(self):
        self.grid = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.writes = []
        self.cal = CalendarTools(self.grid, self.writes.extend)

    def test_replace_text_renames_yuliia(self):
        out = self.cal.call("replace_text", {"find": "yuliia", "replace": "yulia"})
        self.assertEqual(self.writes, [("H26", "yulia")])
        self.assertEqual(out["changed"][0], {"date": "2026-09-27", "old": "yuliia", "new": "yulia"})
        self.assertEqual(self.cal.days[date(2026, 9, 27)], "yulia")
        self.assertEqual(self.cal.changes, ["2026-09-27: 'yuliia' -> 'yulia'"])

    def test_replace_text_no_match(self):
        out = self.cal.call("replace_text", {"find": "zzz", "replace": "y"})
        self.assertEqual(out["changed"], [])
        self.assertEqual(self.writes, [])

    def test_add_to_existing_and_empty(self):
        self.cal.call("add_to_note", {"date": "2026-09-28", "text": "digital"})
        self.cal.call("add_to_note", {"date": "2026-10-09", "text": "gym"})
        self.assertEqual(self.writes, [("B28", "forti - digital"), ("M22", "gym")])

    def test_set_note_clear(self):
        self.cal.call("set_note", {"date": "2026-09-27", "note": ""})
        self.assertEqual(self.writes, [("H26", "")])
        self.assertIsNone(self.cal.days[date(2026, 9, 27)])

    def test_errors_do_not_write(self):
        self.assertIn("takvimde yok", self.cal.call("set_note", {"date": "2026-11-01", "note": "x"})["error"])
        self.assertIn("Geçersiz tarih", self.cal.call("set_note", {"date": "cuma", "note": "x"})["error"])
        self.assertIn("Eksik parametre", self.cal.call("set_note", {"date": "2026-09-28"})["error"])
        self.assertEqual(self.writes, [])

    def test_write_cap(self):
        with mock.patch.object(calendar_tools, "MAX_WRITES", 1):
            out = self.cal.call("replace_text", {"find": "forti", "replace": "fortinet"})
        self.assertIn("en fazla", out["error"])
        self.assertEqual(self.writes, [])

    def test_get_days(self):
        out = self.cal.call("get_days", {"start_date": "2026-09-25", "end_date": "2026-09-26"})
        self.assertEqual([d["note"] for d in out["days"]], ["forti - kocluk", "cemaat"])

    def test_unknown_tool_returns_none(self):
        self.assertIsNone(self.cal.call("nope", {}))


class SheetToolsTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        self.t = SheetTools(self.api)

    def test_write_logs_old_values_and_uses_user_entered(self):
        out = self.t.call("write_cells", {"tab": "KASA", "updates": [{"cell": "b5", "value": "150"}, {"cell": "C5", "value": "=B5*3"}]})
        self.assertEqual(self.api.updates, [("KASA", [("B5", "150"), ("C5", "=B5*3")], "USER_ENTERED")])
        self.assertEqual([c["old"] for c in out["changed"]], ["100", "=B5*2"])  # formül de saklanır
        self.assertEqual(self.t.changes[1], "KASA!C5: '=B5*2' -> '=B5*3'")

    def test_protected_unknown_and_bad_cells(self):
        self.assertIn("korumalı", self.t.call("write_cells", {"tab": "AJAN_LOG", "updates": [{"cell": "A1", "value": "x"}]})["error"])
        self.assertIn("yok", self.t.call("write_cells", {"tab": "KASSA", "updates": [{"cell": "A1", "value": "x"}]})["error"])
        self.assertIn("Geçersiz hücre", self.t.call("write_cells", {"tab": "KASA", "updates": [{"cell": "A1:B2", "value": "x"}]})["error"])
        self.assertEqual(self.api.updates, [])

    def test_cap(self):
        many = [{"cell": f"A{i}", "value": "x"} for i in range(1, sheet_tools.MAX_CELLS + 2)]
        self.assertIn("en fazla", self.t.call("write_cells", {"tab": "KASA", "updates": many})["error"])
        self.assertEqual(self.api.updates, [])

    def test_read_truncates(self):
        out = self.t.call("read_range", {"tab": "KASA", "cells": "A1:B200"})
        self.assertEqual(len(out["rows"]), sheet_tools.MAX_READ_ROWS)
        self.assertTrue(out["truncated"])


class AgentLoopTests(unittest.TestCase):
    def test_tool_call_then_answer(self):
        api = FakeApi()
        tools = Toolbox(SheetTools(api), declarations=sheet_tools.TOOL_DECLARATIONS)
        sent = []

        def fake_generate(system, contents, decls):
            sent.append(contents[:])
            if len(sent) == 1:
                call = {"functionCall": {"name": "write_cells", "args": {"tab": "KASA", "updates": [{"cell": "B5", "value": "150"}]}}}
                return {"candidates": [{"content": {"role": "model", "parts": [call]}}]}
            return {"candidates": [{"content": {"role": "model", "parts": [{"text": "KASA B5: 100 -> 150"}]}}]}

        reply = run_agent("B5'i 150 yap", [("user", "selam"), ("bot", "merhaba")], tools, "sys", fake_generate)
        self.assertEqual(reply, "KASA B5: 100 -> 150")
        self.assertEqual(api.updates[0][1], [("B5", "150")])
        first = sent[0]
        self.assertEqual([c["role"] for c in first], ["user", "model", "user"])  # hafıza + yeni mesaj
        fr = sent[1][-1]["parts"][0]["functionResponse"]
        self.assertEqual(fr["name"], "write_cells")
        self.assertIn("changed", fr["response"]["result"])

    def test_unknown_tool_and_empty_response(self):
        tools = Toolbox(SheetTools(FakeApi()), declarations=[])
        calls = iter([
            {"candidates": [{"content": {"role": "model", "parts": [{"functionCall": {"name": "rm_rf", "args": {}}}]}}]},
            {"candidates": []},
        ])
        reply = run_agent("x", [], tools, "sys", lambda *a: next(calls))
        self.assertIn("üretemedim", reply)

    def test_step_limit(self):
        tools = Toolbox(SheetTools(FakeApi()), declarations=[])
        loop = {"candidates": [{"content": {"role": "model", "parts": [{"functionCall": {"name": "list_tabs", "args": {}}}]}}]}
        reply = run_agent("x", [], tools, "sys", lambda *a: loop, max_steps=3)
        self.assertIn("uzadı", reply)

    def test_system_prompt_contains_date_tabs_and_snapshot(self):
        days = {date(2026, 9, 25): "forti", date(2026, 9, 26): None}
        s = build_system(date(2026, 9, 25), ["TAKVIM", "KASA"], days)
        self.assertIn("Cuma 2026-09-25", s)
        self.assertIn("TAKVIM, KASA", s)
        self.assertIn("Cumartesi 2026-09-26: (boş)", s)


if __name__ == "__main__":
    unittest.main()
