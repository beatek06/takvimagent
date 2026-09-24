import json
import unittest
from datetime import date
from pathlib import Path

from agent.calendar_sheet import read_days
from agent.summary import evening_message, gap_message

FIXTURE = Path(__file__).parent.parent / "dev" / "fixtures" / "takvim.json"


@unittest.skipUnless(FIXTURE.exists(), "dev/fixtures/takvim.json yok")
class SummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = read_days(json.loads(FIXTURE.read_text(encoding="utf-8")))

    def test_friday_evening_tomorrow_is_saturday(self):
        msg = evening_message(self.days, date(2026, 9, 25))  # Cuma
        self.assertIn("Yarın: Cmt 26 Eyl\ncemaat", msg)
        self.assertNotIn("Hafta sonuna kadar", msg)
        self.assertIn("🏖 Hafta sonu\nPaz 27 Eyl: yuliia", msg)
        self.assertNotIn("Cmt 26 Eyl:", msg)  # yarın zaten yukarıda

    def test_sunday_evening_shows_next_week(self):
        msg = evening_message(self.days, date(2026, 9, 27))  # Pazar
        self.assertIn("Yarın: Pzt 28 Eyl\nforti", msg)
        self.assertIn("Sal 29 Eyl: capacity", msg)
        self.assertIn("Cum 2 Eki: digital", msg)
        self.assertEqual(msg.count("Cmt 3 Eki: yana"), 1)  # sadece hafta sonu bölümünde
        self.assertIn("Paz 4 Eki: yana", msg)
        self.assertIn("Cum 2 Eki: digital\n\n🏖", msg)  # hafta içi bölümü cumada biter

    def test_midweek_lists_up_to_friday(self):
        msg = evening_message(self.days, date(2026, 9, 28))  # Pazartesi, yarın Salı
        self.assertIn("Yarın: Sal 29 Eyl\ncapacity", msg)
        self.assertIn("Çar 30 Eyl: digital", msg)
        self.assertIn("Cum 2 Eki: digital", msg)
        self.assertNotIn("Pzt 5 Eki", msg)

    def test_gap_reports_empty_days(self):
        msg = gap_message(self.days, date(2026, 9, 27))  # 28 Eyl - 11 Eki
        self.assertIn("Boş: Cum 9 Eki, Paz 11 Eki", msg)
        self.assertNotIn("hücresi olmayan", msg)

    def test_gap_reports_month_not_added(self):
        msg = gap_message(self.days, date(2026, 10, 25))  # 26 Eki - 8 Kas
        self.assertIn("Takvimde henüz hücresi olmayan:", msg)
        self.assertIn("Paz 1 Kas", msg)


if __name__ == "__main__":
    unittest.main()
