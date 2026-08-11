import os
import tempfile
import unittest

from data_loader import TennisDataLoader


class DataLoaderTests(unittest.TestCase):
    def test_default_data_path_is_independent_of_working_directory(self):
        previous = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                loader = TennisDataLoader()
        finally:
            os.chdir(previous)
        self.assertGreaterEqual(len(loader.get_all_players()), 50)

    def test_all_surface_rows_are_not_exposed_as_court_choices(self):
        players = TennisDataLoader().get_all_players()
        self.assertNotIn("all", {surface for player in players for surface in player["surfaces"]})

    def test_missing_grass_uses_all_surface_before_hard(self):
        loader = TennisDataLoader()
        candidate = next(
            player for player, sources in loader.fallback_sources.items()
            if sources.get("grass") == "all"
        )
        stats, fallback = loader.get_player_stats(candidate, "grass")
        self.assertTrue(fallback)
        self.assertEqual(stats["source_surface"], "all")
        self.assertIn("all-surface", loader.get_fallback_warning(candidate, "grass"))

    def test_missing_percentage_is_preserved(self):
        self.assertIsNone(TennisDataLoader.clean_percentage(""))
        self.assertIsNone(TennisDataLoader.clean_percentage("-"))


if __name__ == "__main__":
    unittest.main()
