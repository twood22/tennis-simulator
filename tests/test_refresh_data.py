import unittest

from scripts.refresh_data import STAT_FIELDS, add_player, add_score, empty_stats


class RefreshDataTests(unittest.TestCase):
    def test_score_parser_counts_sets_games_and_tiebreaks(self):
        winner = empty_stats()
        loser = empty_stats()
        add_score(winner, "7-6(4) 3-6 6-3", True)
        add_score(loser, "7-6(4) 3-6 6-3", False)
        self.assertEqual((winner["sets_won"], winner["sets_lost"]), (2, 1))
        self.assertEqual((winner["games_won"], winner["games_lost"]), (16, 15))
        self.assertEqual((winner["tiebreaks"], winner["tiebreaks_won"]), (1, 1))
        self.assertEqual((loser["tiebreaks"], loser["tiebreaks_won"]), (1, 0))

    def test_impossible_source_counters_are_rejected(self):
        row = {
            "score": "6-4 6-4",
            "loser_rank": "20",
            "winner_rank": "10",
        }
        valid = {
            "ace": 5, "df": 2, "svpt": 60, "1stIn": 36,
            "1stWon": 26, "2ndWon": 12, "SvGms": 10,
            "bpSaved": 4, "bpFaced": 6,
        }
        for prefix in ("w", "l"):
            for field in STAT_FIELDS:
                row[f"{prefix}_{field}"] = str(valid[field])
        row["w_bpSaved"] = "7"
        self.assertFalse(add_player(empty_stats(), row, "w", "l", True))


if __name__ == "__main__":
    unittest.main()
