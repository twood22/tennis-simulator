import unittest

from simulation_engine import MatchStats, TennisSimulator


BASE_STATS = {
    "first_serve_in_pct": 0.62,
    "first_serve_win_pct": 0.74,
    "second_serve_win_pct": 0.52,
    "double_fault_per_second_serve": 0.08,
    "vs_first_serve_win_pct": 0.30,
    "vs_second_serve_win_pct": 0.50,
    "dominance_ratio": 1.0,
    "break_point_save_pct": 0.65,
    "break_point_conversion_pct": 0.40,
}


class RecordingSetSimulator(TennisSimulator):
    def __init__(self):
        super().__init__(1)
        self.game_servers = []
        self.tiebreak_server = None

    def simulate_game(self, server_stats, returner_stats, server_player, *args, **kwargs):
        self.game_servers.append(server_player)
        return server_player

    def simulate_tiebreak(self, p1_stats, p2_stats, starting_server, match_stats=None):
        self.tiebreak_server = starting_server
        return 1


class SimulationEngineTests(unittest.TestCase):
    def test_tiebreak_starts_with_next_server(self):
        simulator = RecordingSetSimulator()
        result = simulator.simulate_set(BASE_STATS, BASE_STATS, 1)
        self.assertEqual(simulator.game_servers[-1], 2)
        self.assertEqual(simulator.tiebreak_server, 1)
        self.assertEqual(result, (1, 7, 6, 2))

    def test_even_game_set_keeps_same_next_set_opener(self):
        class SixLoveSimulator(TennisSimulator):
            def simulate_game(self, *args, **kwargs):
                return 1

        result = SixLoveSimulator(1).simulate_set(BASE_STATS, BASE_STATS, 1)
        self.assertEqual(result, (1, 6, 0, 1))

    def test_break_point_uses_normal_point_model_and_tracks_serve(self):
        stats = MatchStats()
        server = dict(BASE_STATS, break_point_save_pct=0.0)
        returner = dict(BASE_STATS, break_point_conversion_pct=1.0)
        TennisSimulator(5).simulate_point(server, returner, True, 1, stats)
        self.assertEqual(stats.player1_first_serves_attempted, 1)
        self.assertEqual(stats.player1_break_points_faced, 1)
        self.assertEqual(stats.player2_break_points_opportunities, 1)

    def test_second_serve_win_rate_is_not_charged_for_double_fault_twice(self):
        server = dict(BASE_STATS, first_serve_in_pct=0.0, second_serve_win_pct=0.60,
                      double_fault_per_second_serve=0.10)
        returner = dict(BASE_STATS, vs_second_serve_win_pct=0.40)
        simulator = TennisSimulator(7)
        stats = MatchStats()
        wins = sum(simulator.simulate_point(server, returner, False, 1, stats) for _ in range(50000))
        self.assertAlmostEqual(wins / 50000, 0.60, delta=0.01)
        self.assertAlmostEqual(stats.player1_double_faults / 50000, 0.10, delta=0.01)

    def test_seed_reproduces_results(self):
        first = TennisSimulator().run_monte_carlo_simulation(
            BASE_STATS, BASE_STATS, num_simulations=200, seed=1234
        )
        second = TennisSimulator().run_monte_carlo_simulation(
            BASE_STATS, BASE_STATS, num_simulations=200, seed=1234
        )
        self.assertEqual(first, second)

    def test_detailed_stats_are_aggregated_from_raw_counts(self):
        result = TennisSimulator().run_monte_carlo_simulation(
            BASE_STATS, BASE_STATS, num_simulations=1000,
            track_detailed_stats=True, seed=9
        )
        observed = result["observed_stats"]["player1"]
        self.assertAlmostEqual(observed["first_serve_in_pct"], 0.62, delta=0.02)
        self.assertAlmostEqual(observed["second_serve_win_pct"], 0.52, delta=0.02)
        self.assertAlmostEqual(observed["double_fault_per_second_serve"], 0.08, delta=0.02)

    def test_identical_players_are_symmetric(self):
        result = TennisSimulator().run_monte_carlo_simulation(
            BASE_STATS, BASE_STATS, num_simulations=10000, seed=11
        )
        self.assertAlmostEqual(result["player1_win_pct"], 0.5, delta=0.02)
        self.assertEqual(sum(result["set_distributions"].values()), 10000)


if __name__ == "__main__":
    unittest.main()
