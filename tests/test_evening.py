import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from agent import memory
from agent.evening import in_send_window

ZH = ZoneInfo("Europe/Zurich")


class FakeSheets:
    def __init__(self):
        self.rows = []
        self.tab_calls = 0

    def ensure_tab(self, tab):
        self.tab_calls += 1

    def get_values(self, tab, cells, render="UNFORMATTED_VALUE"):
        assert cells == "A:C"  # tüm sütun okunmalı, sabit satır sınırı olmamalı
        return [list(r) for r in self.rows]

    def append_rows(self, tab, rows):
        self.rows.extend(rows)


class SendWindowTests(unittest.TestCase):
    def test_window(self):
        at = lambda h, m=0: datetime(2026, 9, 25, h, m, tzinfo=ZH)
        self.assertFalse(in_send_window(at(18, 59)))
        self.assertTrue(in_send_window(at(19, 0)))
        self.assertTrue(in_send_window(at(22, 12)))   # GitHub'ın geciktirdiği gerçek çalışma
        self.assertTrue(in_send_window(at(23, 59)))
        self.assertFalse(in_send_window(datetime(2026, 9, 26, 0, 5, tzinfo=ZH)))

    def test_utc_cron_times_map_to_zurich_hour_19_in_both_seasons(self):
        utc = ZoneInfo("UTC")
        summer = datetime(2026, 9, 25, 17, 0, tzinfo=utc).astimezone(ZH)
        winter = datetime(2026, 12, 15, 18, 0, tzinfo=utc).astimezone(ZH)
        self.assertEqual((summer.hour, winter.hour), (19, 19))
        # Kışın 17:00 UTC = 18:00 Zürih: pencere dışı, atlanır
        self.assertFalse(in_send_window(datetime(2026, 12, 15, 17, 0, tzinfo=utc).astimezone(ZH)))


class SentMarkerTests(unittest.TestCase):
    def test_mark_and_check_per_day(self):
        s = FakeSheets()
        now = datetime(2026, 9, 25, 19, 1, tzinfo=ZH)
        self.assertFalse(memory.already_sent(s, "evening:2026-09-25"))
        memory.mark_sent(s, now, "evening:2026-09-25")
        self.assertTrue(memory.already_sent(s, "evening:2026-09-25"))
        self.assertFalse(memory.already_sent(s, "evening:2026-09-26"))

    def test_marker_ignores_other_roles_and_history_ignores_marker(self):
        s = FakeSheets()
        s.rows = [["t", "user", "evening:2026-09-25"], ["t", "sent", "evening:2026-09-24"]]
        self.assertFalse(memory.already_sent(s, "evening:2026-09-25"))  # sadece 'sent' rolü sayılır
        memory.mark_sent(s, datetime(2026, 9, 25, 19, 0, tzinfo=ZH), "evening:2026-09-25")
        history = memory.load_history(s)
        self.assertEqual(history, [("user", "evening:2026-09-25")])  # 'sent' sohbete karışmaz

    def test_history_returns_latest_turns(self):
        s = FakeSheets()
        s.rows = [["t", "user" if i % 2 == 0 else "bot", f"m{i}"] for i in range(30)]
        self.assertEqual([t for _, t in memory.load_history(s, limit=3)], ["m27", "m28", "m29"])


if __name__ == "__main__":
    unittest.main()
