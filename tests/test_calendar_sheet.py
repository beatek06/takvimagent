import json
import unittest
from datetime import date
from pathlib import Path

from agent.calendar_sheet import empty_days, find_month_blocks, missing_days, read_days

FIXTURE = Path(__file__).parent.parent / "dev" / "fixtures" / "takvim.json"


def synthetic_grid():
    """Eylül 2026 (Salı başlar) tek başına, küçük bir ızgara."""
    g = [[None] * 9 for _ in range(12)]
    g[0][1] = (date(2026, 9, 1) - date(1899, 12, 30)).days
    for i, name in enumerate(("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")):
        g[1][1 + i] = name
    g[2][2:8] = [1, 2, 3, 4, 5, 6]
    g[3][2] = "forti"
    g[4][1:8] = [7, 8, 9, 10, 11, 12, 13]
    return g


class SyntheticTests(unittest.TestCase):
    def test_finds_block_and_reads_notes(self):
        g = synthetic_grid()
        self.assertEqual(find_month_blocks(g), [(0, 1, date(2026, 9, 1))])
        days = read_days(g)
        self.assertEqual(days[date(2026, 9, 1)], "forti")
        self.assertIsNone(days[date(2026, 9, 2)])
        self.assertEqual(min(days), date(2026, 9, 1))
        self.assertEqual(max(days), date(2026, 9, 13))

    def test_empty_and_missing(self):
        days = read_days(synthetic_grid())
        self.assertEqual(empty_days(days, date(2026, 9, 1), date(2026, 9, 3)),
                         [date(2026, 9, 2), date(2026, 9, 3)])
        self.assertEqual(missing_days(days, date(2026, 9, 12), date(2026, 9, 15)),
                         [date(2026, 9, 14), date(2026, 9, 15)])

    def test_invalid_day_raises(self):
        g = synthetic_grid()
        g[4][7] = 31  # Eylül'de 31 yok
        with self.assertRaises(ValueError):
            read_days(g)


@unittest.skipUnless(FIXTURE.exists(), "dev/fixtures/takvim.json yok (extract_fixture.py çalıştır)")
class RealSheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.days = read_days(cls.grid)

    def test_two_month_blocks(self):
        firsts = [b[2] for b in find_month_blocks(self.grid)]
        self.assertEqual(firsts, [date(2026, 9, 1), date(2026, 10, 1)])

    def test_month_lengths(self):
        sep = [d for d in self.days if d.month == 9]
        octo = [d for d in self.days if d.month == 10]
        self.assertEqual(len(sep), 30)
        self.assertEqual(len(octo), 31)

    def test_known_notes(self):
        self.assertEqual(self.days[date(2026, 9, 25)], "forti - kocluk")
        self.assertEqual(self.days[date(2026, 10, 3)], "yana")

    def test_no_double_counting_of_yearly_overview(self):
        # Üstteki yıllık özet (2021..2027) gün olarak okunmamalı.
        self.assertTrue(all(d.year == 2026 for d in self.days))

    def test_november_not_yet_in_sheet(self):
        self.assertEqual(len(missing_days(self.days, date(2026, 11, 1), date(2026, 11, 3))), 3)


if __name__ == "__main__":
    unittest.main()
