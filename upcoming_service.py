"""Cached upcoming-match dashboard orchestration."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import threading
import time
import unicodedata

from market_odds import build_market_comparison, discover_upcoming_matches
from simulation_service import run_simulation_request


DISCOVERY_TTL_SECONDS = 300
DASHBOARD_SIMULATIONS = 1000

TOURNAMENT_TIERS = {
    "grand_slam": {"label": "Grand Slam", "priority": 0},
    "atp_finals": {"label": "ATP Finals", "priority": 1},
    "masters_1000": {"label": "ATP Masters 1000", "priority": 2},
    "atp_500": {"label": "ATP 500", "priority": 3},
    "atp_250": {"label": "ATP 250", "priority": 4},
}

# The current ATP Tour calendar is intentionally explicit. Unknown events are
# excluded from the public dashboard rather than accidentally showing a
# Challenger or ITF event as a tour-level tournament.
TOURNAMENT_CATALOG = (
    ("Australian Open", "grand_slam", "hard", ("australian open",)),
    ("Roland Garros", "grand_slam", "clay", ("roland garros", "french open")),
    ("Wimbledon", "grand_slam", "grass", ("wimbledon",)),
    ("US Open", "grand_slam", "hard", ("us open",)),
    ("Nitto ATP Finals", "atp_finals", "hard", ("atp finals", "nitto finals")),
    ("BNP Paribas Open", "masters_1000", "hard", ("indian wells", "bnp paribas open")),
    ("Miami Open", "masters_1000", "hard", ("miami open",)),
    ("Monte-Carlo Masters", "masters_1000", "clay", ("monte carlo", "monte-carlo")),
    ("Madrid Open", "masters_1000", "clay", ("madrid open",)),
    ("Italian Open", "masters_1000", "clay", ("internazionali bnl", "italian open", "rome masters")),
    ("National Bank Open", "masters_1000", "hard", ("national bank open", "canada open", "canadian open", "montreal masters", "toronto masters")),
    ("Cincinnati Open", "masters_1000", "hard", ("cincinnati",)),
    ("Shanghai Masters", "masters_1000", "hard", ("shanghai masters",)),
    ("Paris Masters", "masters_1000", "hard", ("paris masters",)),
    ("Dallas Open", "atp_500", "hard", ("dallas open",)),
    ("ABN AMRO Open", "atp_500", "hard", ("abn amro", "rotterdam")),
    ("Qatar Open", "atp_500", "hard", ("qatar exxonmobil", "qatar open", "doha")),
    ("Rio Open", "atp_500", "clay", ("rio open",)),
    ("Mexican Open", "atp_500", "hard", ("abierto mexicano", "acapulco")),
    ("Dubai Tennis Championships", "atp_500", "hard", ("dubai duty free", "dubai tennis")),
    ("Barcelona Open", "atp_500", "clay", ("barcelona open",)),
    ("BMW Open", "atp_500", "clay", ("bmw open", "munich open")),
    ("Hamburg Open", "atp_500", "clay", ("hamburg open",)),
    ("Halle Open", "atp_500", "grass", ("terra wortmann", "halle open")),
    ("Queen's Club Championships", "atp_500", "grass", ("hsbc championships", "queens club", "queen s club")),
    ("Washington Open", "atp_500", "hard", ("mubadala citi dc", "washington open", "dc open")),
    ("Japan Open", "atp_500", "hard", ("japan open", "kinoshita group")),
    ("China Open", "atp_500", "hard", ("china open", "beijing open")),
    ("Swiss Indoors", "atp_500", "hard", ("swiss indoors", "basel open")),
    ("Vienna Open", "atp_500", "hard", ("erste bank open", "vienna open")),
    ("Brisbane International", "atp_250", "hard", ("brisbane international",)),
    ("Hong Kong Open", "atp_250", "hard", ("hong kong tennis open", "hong kong open")),
    ("Adelaide International", "atp_250", "hard", ("adelaide international",)),
    ("ASB Classic", "atp_250", "hard", ("asb classic", "auckland open")),
    ("Open Occitanie", "atp_250", "hard", ("open occitanie", "montpellier open")),
    ("Argentina Open", "atp_250", "clay", ("argentina open", "buenos aires open")),
    ("Delray Beach Open", "atp_250", "hard", ("delray beach",)),
    ("Chile Open", "atp_250", "clay", ("chileopen", "chile open", "santiago open")),
    ("Bucharest Open", "atp_250", "clay", ("tiriac open", "bucharest open")),
    ("US Men's Clay Court Championship", "atp_250", "clay", ("men s clay court", "houston open")),
    ("Grand Prix Hassan II", "atp_250", "clay", ("grand prix hassan", "marrakech open")),
    ("Geneva Open", "atp_250", "clay", ("geneva open",)),
    ("Stuttgart Open", "atp_250", "grass", ("boss open", "stuttgart open")),
    ("Libema Open", "atp_250", "grass", ("libema open", "hertogenbosch")),
    ("Mallorca Championships", "atp_250", "grass", ("mallorca championships",)),
    ("Eastbourne Open", "atp_250", "grass", ("eastbourne open",)),
    ("Nordea Open", "atp_250", "clay", ("nordea open", "bastad open")),
    ("Swiss Open Gstaad", "atp_250", "clay", ("swiss open gstaad", "gstaad open")),
    ("Croatia Open", "atp_250", "clay", ("croatia open", "umag open")),
    ("Generali Open", "atp_250", "clay", ("generali open", "kitzbuhel open", "kitzbühel open")),
    ("Estoril Open", "atp_250", "clay", ("estoril open",)),
    ("Los Cabos Open", "atp_250", "hard", ("mifel tennis", "los cabos")),
    ("Winston-Salem Open", "atp_250", "hard", ("winston salem", "winston-salem")),
    ("Chengdu Open", "atp_250", "hard", ("chengdu open",)),
    ("Hangzhou Open", "atp_250", "hard", ("hangzhou open",)),
    ("Almaty Open", "atp_250", "hard", ("almaty open",)),
    ("European Open", "atp_250", "hard", ("european open", "brussels open")),
    ("Lyon Open", "atp_250", "hard", ("auvergne rhone alpes", "lyon open")),
    ("Nordic Open", "atp_250", "hard", ("nordic open", "stockholm open")),
)

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


def classify_tournament(tournament):
    normalized = _normalized_text(tournament)
    if not normalized:
        return None
    for name, tier, surface, patterns in TOURNAMENT_CATALOG:
        if any(_normalized_text(pattern) in normalized for pattern in patterns):
            tier_details = TOURNAMENT_TIERS[tier]
            return {
                "name": name,
                "tier": tier,
                "tier_label": tier_details["label"],
                "priority": tier_details["priority"],
                "surface": surface,
            }
    return None


def tennis_abstract_url(player_name):
    ascii_name = unicodedata.normalize("NFKD", str(player_name or "")).encode(
        "ascii", "ignore"
    ).decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]", "", ascii_name)
    return f"https://www.tennisabstract.com/cgi-bin/player.cgi?p={slug}"


def infer_surface(tournament):
    classification = classify_tournament(tournament)
    if classification:
        return classification["surface"]
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
                included_matches = []
                excluded_count = 0
                for match in result["matches"]:
                    tournament = classify_tournament(match.get("tournament"))
                    if tournament is None:
                        excluded_count += 1
                        continue
                    match["tournament_name"] = tournament["name"]
                    match["tournament_tier"] = tournament["tier"]
                    match["tournament_tier_label"] = tournament["tier_label"]
                    match["tournament_priority"] = tournament["priority"]
                    tournament_text = _normalized_text(match.get("tournament"))
                    is_qualification = (
                        "qualification" in tournament_text
                        or "qualifying" in tournament_text
                    )
                    match["tournament_stage"] = "Qualification" if is_qualification else "Main draw"
                    match["tournament_stage_priority"] = 1 if is_qualification else 0
                    match["surface"] = infer_surface(match.get("tournament"))
                    match["format"] = infer_format(match.get("tournament"))
                    match["player1_url"] = tennis_abstract_url(match["player1"])
                    match["player2_url"] = tennis_abstract_url(match["player2"])
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
                    included_matches.append(match)
                included_matches.sort(key=lambda match: (
                    match["start_time"],
                    match["tournament_priority"],
                    match["tournament_stage_priority"],
                    match["tournament_name"],
                    match["player1"],
                ))
                result["matches"] = included_matches
                result["excluded_match_count"] = excluded_count
                result["tour_level_only"] = True
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
