"""Cached upcoming-match dashboard orchestration."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import threading
import time

from market_odds import build_market_comparison, discover_upcoming_matches
from simulation_service import run_simulation_request


DISCOVERY_TTL_SECONDS = 300
DASHBOARD_SIMULATIONS = 1000

SURFACE_PATTERNS = {
    "hard": (
        "astana", "atlanta", "australian open", "basel", "beijing",
        "brownsburg", "canada", "cincinnati", "dallas", "delray beach",
        "doha", "dubai", "indian wells", "miami", "montreal",
        "national bank open", "paris masters", "rotterdam", "shanghai",
        "stockholm", "tokyo", "toronto", "us open", "washington",
        "winston salem",
    ),
    "clay": (
        "bastad", "barcelona", "buenos aires", "geneva", "gstaad",
        "hamburg", "houston", "kitzbuhel", "madrid", "marrakech",
        "monte carlo", "munich", "rio open", "roland garros", "rome",
        "santiago", "todi",
    ),
    "grass": (
        "eastbourne", "halle", "majorca", "mallorca", "nottingham",
        "queens", "stuttgart", "wimbledon",
    ),
}


def _normalized_text(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def infer_surface(tournament):
    normalized = _normalized_text(tournament)
    for surface, patterns in SURFACE_PATTERNS.items():
        if any(_normalized_text(pattern) in normalized for pattern in patterns):
            return surface
    return None


def infer_format(tournament):
    normalized = _normalized_text(tournament)
    grand_slams = ("australian open", "roland garros", "wimbledon", "us open")
    if "qualification" not in normalized and any(name in normalized for name in grand_slams):
        return "best5"
    return "best3"


class UpcomingMatchService:
    def __init__(self, loader, discoverer=discover_upcoming_matches,
                 clock=time.monotonic, metadata_path=None):
        self.loader = loader
        self.discoverer = discoverer
        self.clock = clock
        self.metadata_path = Path(metadata_path) if metadata_path else (
            Path(__file__).resolve().parent / "data" / "metadata.json"
        )
        self._discovery_lock = threading.Lock()
        self._simulation_lock = threading.Lock()
        self._matches = None
        self._matches_cached_at = 0
        self._simulation_cache = {}
        self.data_version = self._load_data_version()

    def _load_data_version(self):
        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            return str(metadata.get("as_of") or metadata.get("generated_at") or "unknown")
        except (OSError, ValueError):
            return "unknown"

    def _known_names(self):
        return [player["name"] for player in self.loader.get_all_players()]

    def get_upcoming(self, days=7, force=False):
        now = self.clock()
        if (
            not force
            and self._matches is not None
            and now - self._matches_cached_at < DISCOVERY_TTL_SECONDS
        ):
            return deepcopy(self._matches)

        with self._discovery_lock:
            now = self.clock()
            if (
                not force
                and self._matches is not None
                and now - self._matches_cached_at < DISCOVERY_TTL_SECONDS
            ):
                return deepcopy(self._matches)
            try:
                result = self.discoverer(self._known_names(), days=days)
                for match in result["matches"]:
                    match["surface"] = infer_surface(match.get("tournament"))
                    match["format"] = infer_format(match.get("tournament"))
                    match["simulation_available"] = bool(
                        match["player1_in_model"]
                        and match["player2_in_model"]
                        and match["surface"]
                    )
                    if not match["simulation_available"]:
                        if not match["player1_in_model"] or not match["player2_in_model"]:
                            match["simulation_unavailable_reason"] = (
                                "One or both players are not in the current statistics snapshot."
                            )
                        else:
                            match["simulation_unavailable_reason"] = (
                                "Tournament surface is not mapped yet."
                            )
                result["data_version"] = self.data_version
                result["cache_seconds"] = DISCOVERY_TTL_SECONDS
                self._matches = result
                self._matches_cached_at = now
            except Exception:
                if self._matches is None:
                    raise
                self._matches["errors"] = list(dict.fromkeys([
                    *self._matches.get("errors", []),
                    "Serving a cached schedule because live discovery failed.",
                ]))
            return deepcopy(self._matches)

    def _find_match(self, match_id):
        dashboard = self.get_upcoming()
        return next(
            (match for match in dashboard["matches"] if match["id"] == match_id),
            None,
        )

    def _seed_for(self, match):
        material = f"{self.data_version}|{match['id']}|{match['surface']}"
        return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big") % (2**63)

    def _quality_summary(self, match):
        first, _ = self.loader.get_player_stats(match["player1"], match["surface"])
        second, _ = self.loader.get_player_stats(match["player2"], match["surface"])
        players = []
        for name, stats in ((match["player1"], first), (match["player2"], second)):
            players.append({
                "name": name,
                "matches": int(stats["matches_played"]),
                "median_opponent_rank": stats.get("median_opponent_rank"),
                "mean_opponent_rank": stats.get("mean_opponent_rank"),
                "source_surface": stats["source_surface"],
            })

        warnings = []
        if min(player["matches"] for player in players) < 15:
            warnings.append("At least one player has fewer than 15 matches on this surface.")
        opponent_means = [player["mean_opponent_rank"] for player in players]
        if None not in opponent_means and abs(opponent_means[0] - opponent_means[1]) >= 75:
            warnings.append(
                "The players faced substantially different opponent quality; the model does not adjust for schedule strength."
            )
        return {
            "status": "caution" if warnings else "standard",
            "players": players,
            "warnings": warnings,
        }

    def get_simulation(self, match_id):
        match = self._find_match(match_id)
        if match is None:
            raise KeyError("Upcoming match not found")
        if not match["simulation_available"]:
            raise ValueError(match["simulation_unavailable_reason"])

        cache_key = (self.data_version, match_id, match["surface"], match["format"])
        with self._simulation_lock:
            cached = self._simulation_cache.get(cache_key)
            if cached is None:
                payload = {
                    "player1": match["player1"],
                    "player2": match["player2"],
                    "format": match["format"],
                    "num_simulations": DASHBOARD_SIMULATIONS,
                    "surfaces": [match["surface"]],
                    "seed": self._seed_for(match),
                }
                simulation = run_simulation_request(payload, self.loader)
                surface_result = simulation["surfaces"][match["surface"]]
                cached = {
                    "player1": match["player1"],
                    "player2": match["player2"],
                    "surface": match["surface"],
                    "format": match["format"],
                    "num_simulations": DASHBOARD_SIMULATIONS,
                    "seed": simulation["seed"],
                    "player1_probability": surface_result["player1_win_pct"],
                    "player2_probability": surface_result["player2_win_pct"],
                    "player1_ci95": surface_result["player1_win_ci95"],
                    "quality": self._quality_summary(match),
                    "fallback_warnings": simulation["fallback_warnings"],
                }
                self._simulation_cache[cache_key] = cached

        response = deepcopy(cached)
        providers = match["market_comparison"].get("providers", [])
        response["market_comparison"] = build_market_comparison(
            match["player1"],
            match["player2"],
            providers,
            {match["surface"]: cached["player1_probability"]},
        )
        return response
