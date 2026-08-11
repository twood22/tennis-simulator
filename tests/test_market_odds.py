import unittest
from datetime import datetime, timezone

from market_odds import (
    fetch_kalshi_odds,
    fetch_polymarket_odds,
    discover_upcoming_matches,
    get_market_comparison,
)


KALSHI_FIXTURE = {
    "markets": [
        {
            "ticker": "EVENT-TIEN",
            "event_ticker": "EVENT",
            "title": "Will Learner Tien win the Merida vs Tien match?",
            "yes_sub_title": "Learner Tien",
            "yes_bid_dollars": "0.65",
            "yes_ask_dollars": "0.67",
            "last_price_dollars": "0.66",
            "volume_fp": "1200.5",
            "updated_time": "2026-08-10T20:00:00Z",
        },
        {
            "ticker": "EVENT-MERIDA",
            "event_ticker": "EVENT",
            "title": "Will Daniel Merida Aguilar win the Merida vs Tien match?",
            "yes_sub_title": "Daniel Merida Aguilar",
            "yes_bid_dollars": "0.33",
            "yes_ask_dollars": "0.35",
            "last_price_dollars": "0.34",
            "volume_fp": "800",
            "updated_time": "2026-08-10T20:01:00Z",
        },
    ]
}

POLYMARKET_FIXTURE = {
    "events": [
        {
            "title": "Old match",
            "slug": "old-match",
            "active": True,
            "closed": True,
            "markets": [],
        },
        {
            "title": "Daniel Merida Aguilar vs Learner Tien",
            "slug": "atp-merida-tien",
            "active": True,
            "closed": False,
            "markets": [
                {
                    "id": "123",
                    "question": "Daniel Merida Aguilar vs Learner Tien",
                    "sportsMarketType": "moneyline",
                    "active": True,
                    "closed": False,
                    "outcomes": '["Daniel Merida Aguilar", "Learner Tien"]',
                    "outcomePrices": '["0.335", "0.665"]',
                    "volume": "9000.25",
                    "liquidity": "110000",
                    "updatedAt": "2026-08-10T20:02:00Z",
                }
            ],
        },
    ]
}


class MarketOddsTests(unittest.TestCase):
    def test_kalshi_maps_fuller_surname_and_normalizes_midpoints(self):
        result = fetch_kalshi_odds(
            "Daniel Merida", "Learner Tien", lambda _url: KALSHI_FIXTURE
        )
        self.assertEqual(result["status"], "available")
        self.assertAlmostEqual(result["player1"]["probability"], 0.34)
        self.assertAlmostEqual(result["player2"]["probability"], 0.66)
        self.assertEqual(result["player1"]["market_label"], "Daniel Merida Aguilar")
        self.assertEqual(result["volume"], 2000.5)

    def test_polymarket_reverses_outcomes_to_requested_player_order(self):
        result = fetch_polymarket_odds(
            "Learner Tien", "Daniel Merida", lambda _url: POLYMARKET_FIXTURE
        )
        self.assertEqual(result["status"], "available")
        self.assertAlmostEqual(result["player1"]["probability"], 0.665)
        self.assertAlmostEqual(result["player2"]["probability"], 0.335)
        self.assertEqual(result["source_url"], "https://polymarket.com/event/atp-merida-tien")

    def test_does_not_accept_a_partial_player_pair(self):
        result = fetch_polymarket_odds(
            "Ben Shelton", "Jakub Mensik", lambda _url: POLYMARKET_FIXTURE
        )
        self.assertEqual(result["status"], "unavailable")

    def test_provider_failure_is_returned_as_data(self):
        def failed_fetch(_url):
            raise TimeoutError("secret provider detail")

        result = fetch_kalshi_odds("Learner Tien", "Daniel Merida", failed_fetch)
        self.assertEqual(result["status"], "error")
        self.assertNotIn("secret", result["reason"])

    def test_consensus_and_surface_differences(self):
        def fixture_fetch(url):
            return KALSHI_FIXTURE if "kalshi.com" in url else POLYMARKET_FIXTURE

        result = get_market_comparison(
            "Daniel Merida",
            "Learner Tien",
            {"hard": 0.61},
            fetcher=fixture_fetch,
        )
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["consensus"]["provider_count"], 2)
        self.assertAlmostEqual(result["consensus"]["player1"]["probability"], 0.3375)
        self.assertEqual(
            result["model_comparison"]["hard"]["player1_model_minus_market_pp"],
            27.25,
        )

    def test_upcoming_discovery_merges_providers_and_resolves_alias(self):
        kalshi = {
            "markets": [
                {**KALSHI_FIXTURE["markets"][0],
                 "occurrence_datetime": "2026-08-11T18:00:00Z"},
                {**KALSHI_FIXTURE["markets"][1],
                 "occurrence_datetime": "2026-08-11T18:00:00Z"},
            ]
        }
        polymarket = {
            "events": [{
                **POLYMARKET_FIXTURE["events"][1],
                "startTime": "2026-08-11T18:00:00Z",
                "markets": [{
                    **POLYMARKET_FIXTURE["events"][1]["markets"][0],
                    "question": "National Bank Open: Daniel Merida Aguilar vs Learner Tien",
                    "gameStartTime": "2026-08-11 18:00:00+00",
                }],
            }]
        }

        def fixture_fetch(url):
            return kalshi if "kalshi.com" in url else polymarket

        result = discover_upcoming_matches(
            ["Daniel Merida", "Learner Tien"],
            now=datetime(2026, 8, 11, 16, tzinfo=timezone.utc),
            fetcher=fixture_fetch,
        )
        self.assertEqual(len(result["matches"]), 1)
        match = result["matches"][0]
        self.assertEqual({match["player1"], match["player2"]}, {
            "Daniel Merida", "Learner Tien"
        })
        self.assertEqual(match["tournament"], "National Bank Open")
        self.assertEqual(match["market_comparison"]["consensus"]["provider_count"], 2)


if __name__ == "__main__":
    unittest.main()
