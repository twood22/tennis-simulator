import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TennisDataLoader:
    """Load reviewed Tennis Abstract snapshots without a dataframe dependency."""

    DISPLAY_SURFACES = ("hard", "clay", "grass")
    FILES = {
        "serve": "Tennis abstract - serve.csv",
        "return": "Tennis abstract - return.csv",
        "breaks": "Tennis abstract - breaks.csv",
        "more": "Tennis abstract - more.csv",
    }

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent / "data"
        self.player_data: Dict[str, Dict[str, Dict]] = {}
        self.fallback_sources: Dict[str, Dict[str, Optional[str]]] = {}
        self.load_all_data()

    @staticmethod
    def clean_percentage(value) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip()
        if text in ("", "-"):
            return None
        try:
            if text.endswith("%"):
                return float(text[:-1]) / 100.0
            number = float(text)
            return number / 100.0 if number > 1 else number
        except (TypeError, ValueError):
            return None

    @staticmethod
    def clean_numeric(value) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip()
        if text in ("", "-"):
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    def load_csv_data(self, filename: str) -> Dict[Tuple[str, str], Dict[str, str]]:
        filepath = self.data_dir / filename
        if not filepath.is_file():
            raise FileNotFoundError(f"Missing tennis data file: {filepath}")

        rows: Dict[Tuple[str, str], Dict[str, str]] = {}
        with filepath.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {"player_name", "surface", "ranking", "matches_played"}
            missing = required.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{filename} missing columns: {sorted(missing)}")
            for row in reader:
                key = (row["player_name"].strip(), row["surface"].strip().lower())
                if key in rows:
                    raise ValueError(f"Duplicate player/surface row in {filename}: {key}")
                rows[key] = row
        return rows

    def load_all_data(self) -> None:
        datasets = {name: self.load_csv_data(filename) for name, filename in self.FILES.items()}
        players = sorted({player for rows in datasets.values() for player, _ in rows})
        surfaces = (*self.DISPLAY_SURFACES, "all")

        for player in players:
            self.player_data[player] = {}
            self.fallback_sources[player] = {}
            for requested_surface in surfaces:
                source_surface = self._choose_source_surface(
                    player, requested_surface, datasets
                )
                if source_surface is None:
                    continue
                stats = self._get_player_surface_data(player, source_surface, datasets)
                if stats is None:
                    continue
                stats["source_surface"] = source_surface
                self.player_data[player][requested_surface] = stats
                self.fallback_sources[player][requested_surface] = (
                    None if source_surface == requested_surface else source_surface
                )

    @staticmethod
    def _choose_source_surface(player: str, requested_surface: str,
                               datasets: Dict[str, Dict]) -> Optional[str]:
        candidates = [requested_surface]
        if requested_surface != "all":
            candidates.extend(["all", "hard"])
        for surface in dict.fromkeys(candidates):
            key = (player, surface)
            if all(key in rows for rows in datasets.values()):
                return surface
        return None

    def _get_player_surface_data(self, player: str, surface: str,
                                 datasets: Dict[str, Dict]) -> Optional[Dict]:
        key = (player, surface)
        try:
            serve = datasets["serve"][key]
            returning = datasets["return"][key]
            breaks = datasets["breaks"][key]
            more = datasets["more"][key]
        except KeyError:
            return None

        stats = {
            "ranking": self.clean_numeric(serve["ranking"]),
            "matches_played": self.clean_numeric(serve["matches_played"]),
            "first_serve_in_pct": self.clean_percentage(serve["first_serve_in_pct"]),
            "first_serve_win_pct": self.clean_percentage(serve["first_serve_win_pct"]),
            "second_serve_win_pct": self.clean_percentage(serve["second_serve_win_pct"]),
            "second_serve_win_pct_in_play": self.clean_percentage(serve["second_serve_win_pct_in_play"]),
            "double_fault_per_second_serve": self.clean_percentage(serve["double_fault_per_second_serve"]),
            "ace_pct": self.clean_percentage(serve["ace_pct"]),
            "double_fault_pct": self.clean_percentage(serve["double_fault_pct"]),
            "vs_first_serve_win_pct": self.clean_percentage(returning["vs_first_serve_win_pct"]),
            "vs_second_serve_win_pct": self.clean_percentage(returning["vs_second_serve_win_pct"]),
            "vs_double_fault_pct": self.clean_percentage(returning["vs_double_fault_pct"]),
            "return_points_won": self.clean_percentage(returning["return_points_won"]),
            "median_opponent_rank": self.clean_numeric(returning.get("median_opponent_rank")),
            "mean_opponent_rank": self.clean_numeric(returning.get("mean_opponent_rank")),
            "break_point_conversion_pct": self.clean_percentage(breaks["break_point_conversion_pct"]),
            "break_point_save_pct": self.clean_percentage(breaks["break_point_save_pct"]),
            "break_points_converted": self.clean_numeric(breaks["break_points_converted"]),
            "break_point_chances": self.clean_numeric(breaks["break_point_chances"]),
            "break_points_saved": self.clean_numeric(breaks["break_points_saved"]),
            "break_points_faced": self.clean_numeric(breaks["break_points_faced"]),
            "dominance_ratio": self.clean_numeric(more["dominance_ratio"]),
            "total_points_won_pct": self.clean_percentage(more["total_points_won_pct"]),
            "tiebreak_win_pct": self.clean_percentage(more["tiebreak_win_pct"]),
            "set_win_pct": self.clean_percentage(more["set_win_pct"]),
            "game_win_pct": self.clean_percentage(more["game_win_pct"]),
        }
        required_model_fields = (
            "first_serve_in_pct", "first_serve_win_pct", "second_serve_win_pct",
            "double_fault_per_second_serve", "vs_first_serve_win_pct",
            "vs_second_serve_win_pct", "dominance_ratio",
        )
        if any(stats[field] is None for field in required_model_fields):
            return None
        return stats

    def get_player_stats(self, player_name: str, surface: str) -> Tuple[Dict, bool]:
        if player_name not in self.player_data:
            raise ValueError(f"Player {player_name} not found in data")
        surface = surface.lower()
        if surface not in self.player_data[player_name]:
            raise ValueError(f"Surface {surface} not available for player {player_name}")
        fallback = self.fallback_sources[player_name][surface] is not None
        return self.player_data[player_name][surface], fallback

    def get_all_players(self) -> List[Dict]:
        players = []
        for player_name, surfaces_data in self.player_data.items():
            available = [surface for surface in self.DISPLAY_SURFACES if surface in surfaces_data]
            if not available:
                continue
            ranking_stats = surfaces_data.get("all") or surfaces_data[available[0]]
            ranking = ranking_stats["ranking"]
            players.append({
                "name": player_name,
                "ranking": int(ranking) if ranking is not None else None,
                "surfaces": available,
            })
        players.sort(key=lambda item: (item["ranking"] is None, item["ranking"] or 10**9, item["name"]))
        return players

    def get_fallback_warning(self, player_name: str, surface: str) -> Optional[str]:
        source = self.fallback_sources.get(player_name, {}).get(surface)
        if source:
            return f"{player_name} uses {source}-surface data for {surface}"
        return None
