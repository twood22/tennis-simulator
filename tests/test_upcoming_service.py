import unittest

from data_loader import TennisDataLoader
from market_odds import build_market_comparison
from upcoming_service import UpcomingMatchService, infer_format, infer_surface


def provider(name, player1_probability):
    return {
        "provider": name,
        "status": "available",
        "player1": {"name": "Daniel Merida", "probability": player1_probability},
        "player2": {"name": "Learner Tien", "probability": 1 - player1_probability},
        "fetched_at": "2026-08-11T16:00:00Z",
    }


class UpcomingServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = TennisDataLoader()

    def test_surface_and_format_inference(self):
        self.assertEqual(infer_surface("Cincinnati Open, Qualification"), "hard")
        self.assertEqual(infer_surface("Todi"), "clay")
        self.assertEqual(infer_surface("Wimbledon"), "grass")
        self.assertIsNone(infer_surface("Unknown Invitational"))
        self.assertEqual(infer_format("US Open"), "best5")
        self.assertEqual(infer_format("US Open, Qualification"), "best3")

    def test_discovery_is_cached_and_simulation_flags_quality_mismatch(self):
        calls = []
        providers = [provider("kalshi", 0.34), provider("polymarket", 0.335)]

        def discoverer(_known_names, days):
            calls.append(days)
            return {
                "matches": [{
                    "id": "merida-tien",
                    "player1": "Daniel Merida",
                    "player2": "Learner Tien",
                    "player1_in_model": True,
                    "player2_in_model": True,
                    "start_time": "2026-08-11T22:00:00Z",
                    "tournament": "National Bank Open",
                    "round": "Quarterfinal",
                    "market_comparison": build_market_comparison(
                        "Daniel Merida", "Learner Tien", providers
                    ),
                }],
                "errors": [],
                "generated_at": "2026-08-11T16:00:00Z",
                "window_end": "2026-08-18T16:00:00Z",
            }

        service = UpcomingMatchService(self.loader, discoverer=discoverer)
        first = service.get_upcoming()
        second = service.get_upcoming()
        self.assertEqual(calls, [7])
        self.assertEqual(first, second)
        self.assertTrue(first["matches"][0]["simulation_available"])

        result = service.get_simulation("merida-tien")
        self.assertEqual(result["surface"], "hard")
        self.assertEqual(result["quality"]["status"], "caution")
        self.assertTrue(any(
            "schedule strength" in warning for warning in result["quality"]["warnings"]
        ))
        self.assertIn("hard", result["market_comparison"]["model_comparison"])


if __name__ == "__main__":
    unittest.main()
