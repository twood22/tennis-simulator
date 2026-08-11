import unittest

from data_loader import TennisDataLoader
from simulation_service import ValidationError, run_simulation_request, validate_request


class SimulationServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = TennisDataLoader()
        cls.players = [player["name"] for player in cls.loader.get_all_players()]

    def valid_payload(self):
        return {
            "player1": self.players[0],
            "player2": self.players[1],
            "format": "best3",
            "num_simulations": 10,
            "surfaces": ["hard"],
            "seed": 42,
        }

    def test_rejects_non_object_and_same_player(self):
        with self.assertRaises(ValidationError):
            validate_request(None)
        payload = self.valid_payload()
        payload["player2"] = payload["player1"]
        with self.assertRaisesRegex(ValidationError, "different"):
            validate_request(payload)

    def test_rejects_bad_count_and_surface(self):
        payload = self.valid_payload()
        payload["num_simulations"] = "many"
        with self.assertRaisesRegex(ValidationError, "integer"):
            validate_request(payload)
        payload = self.valid_payload()
        payload["surfaces"] = ["carpet"]
        with self.assertRaisesRegex(ValidationError, "Unsupported"):
            validate_request(payload)

    def test_response_is_seeded_and_counts_actual_total(self):
        first = run_simulation_request(self.valid_payload(), self.loader)
        second = run_simulation_request(self.valid_payload(), self.loader)
        self.assertEqual(first, second)
        self.assertEqual(first["total_simulations"], 10)
        self.assertEqual(first["seed"], 42)
        self.assertIn("player1_win_ci95", first["surfaces"]["hard"])

    def test_market_comparison_receives_surface_model_probabilities(self):
        calls = []

        def fake_market_provider(player1, player2, model_probabilities):
            calls.append((player1, player2, model_probabilities))
            return {"status": "available"}

        result = run_simulation_request(
            self.valid_payload(),
            self.loader,
            market_odds_provider=fake_market_provider,
        )
        self.assertEqual(result["market_comparison"], {"status": "available"})
        self.assertEqual(calls[0][0:2], (result["player1_name"], result["player2_name"]))
        self.assertEqual(
            calls[0][2]["hard"], result["surfaces"]["hard"]["player1_win_pct"]
        )


if __name__ == "__main__":
    unittest.main()
