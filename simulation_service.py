import random
from typing import Callable, Dict, Optional

from data_loader import TennisDataLoader
from simulation_engine import TennisSimulator


SURFACES = ("hard", "clay", "grass")


class ValidationError(ValueError):
    pass


def validate_request(payload: Dict) -> Dict:
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")
    required = ("player1", "player2", "format", "num_simulations")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValidationError(f"Missing required field: {missing[0]}")

    player1 = str(payload["player1"]).strip()
    player2 = str(payload["player2"]).strip()
    if not player1 or not player2:
        raise ValidationError("Both players are required")
    if player1 == player2:
        raise ValidationError("Players must be different")

    format_type = payload["format"]
    if format_type not in ("best3", "best5"):
        raise ValidationError("Format must be 'best3' or 'best5'")
    try:
        num_simulations = int(payload["num_simulations"])
    except (TypeError, ValueError):
        raise ValidationError("Number of simulations must be an integer") from None
    if isinstance(payload["num_simulations"], bool) or not 1 <= num_simulations <= 10000:
        raise ValidationError("Number of simulations must be between 1 and 10000")

    requested_surfaces = payload.get("surfaces", SURFACES)
    if not isinstance(requested_surfaces, list) or not requested_surfaces:
        raise ValidationError("Surfaces must be a non-empty list")
    surfaces = []
    for surface in requested_surfaces:
        normalized = str(surface).lower()
        if normalized not in SURFACES:
            raise ValidationError(f"Unsupported surface: {surface}")
        if normalized not in surfaces:
            surfaces.append(normalized)

    supplied_seed = payload.get("seed")
    if supplied_seed is None:
        seed = random.SystemRandom().getrandbits(63)
    else:
        try:
            seed = int(supplied_seed)
        except (TypeError, ValueError):
            raise ValidationError("Seed must be an integer") from None
        if seed < 0 or seed >= 2**63:
            raise ValidationError("Seed must be between 0 and 2^63 - 1")

    return {
        "player1": player1,
        "player2": player2,
        "format": format_type,
        "num_simulations": num_simulations,
        "surfaces": surfaces,
        "seed": seed,
    }


def _input_parameters(stats: Dict) -> Dict:
    return {
        "first_serve_in_pct": stats["first_serve_in_pct"],
        "first_serve_win_pct": stats["first_serve_win_pct"],
        "second_serve_in_pct": 1.0 - stats["double_fault_per_second_serve"],
        "second_serve_win_pct": stats["second_serve_win_pct"],
        "break_point_save_pct": stats["break_point_save_pct"],
        "double_fault_per_second_serve": stats["double_fault_per_second_serve"],
        "vs_first_serve_win_pct": stats["vs_first_serve_win_pct"],
        "vs_second_serve_win_pct": stats["vs_second_serve_win_pct"],
        "break_point_conversion_pct": stats["break_point_conversion_pct"],
        "matches_played": stats["matches_played"],
        "source_surface": stats["source_surface"],
    }


def run_simulation_request(payload: Dict, loader: TennisDataLoader,
                           progress_callback: Optional[Callable] = None,
                           market_odds_provider: Optional[Callable] = None) -> Dict:
    request_data = validate_request(payload)
    surfaces = request_data["surfaces"]
    num_simulations = request_data["num_simulations"]
    all_results = {}
    all_warnings = []

    for surface_index, surface in enumerate(surfaces):
        player1_stats, player1_fallback = loader.get_player_stats(request_data["player1"], surface)
        player2_stats, player2_fallback = loader.get_player_stats(request_data["player2"], surface)
        warnings = []
        if player1_fallback:
            warnings.append(loader.get_fallback_warning(request_data["player1"], surface))
        if player2_fallback:
            warnings.append(loader.get_fallback_warning(request_data["player2"], surface))

        def surface_progress(completed, total):
            if progress_callback:
                progress_callback(
                    surface, surface_index * num_simulations + completed,
                    len(surfaces) * num_simulations,
                )

        surface_seed = (request_data["seed"] + surface_index) % (2**63)
        results = TennisSimulator().run_monte_carlo_simulation(
            player1_stats,
            player2_stats,
            request_data["format"],
            num_simulations,
            surface_progress if progress_callback else None,
            track_detailed_stats=True,
            seed=surface_seed,
        )
        all_results[surface] = {
            **results,
            "fallback_warnings": warnings,
            "input_parameters": {
                "player1": _input_parameters(player1_stats),
                "player2": _input_parameters(player2_stats),
            },
        }
        all_warnings.extend(warning for warning in warnings if warning)

    response = {
        "surfaces": all_results,
        "player1_name": request_data["player1"],
        "player2_name": request_data["player2"],
        "format": request_data["format"],
        "num_simulations": num_simulations,
        "total_simulations": num_simulations * len(surfaces),
        "seed": request_data["seed"],
        "fallback_warnings": list(dict.fromkeys(all_warnings)),
    }
    if market_odds_provider:
        model_probabilities = {
            surface: results["player1_win_pct"]
            for surface, results in all_results.items()
        }
        try:
            response["market_comparison"] = market_odds_provider(
                request_data["player1"],
                request_data["player2"],
                model_probabilities,
            )
        except Exception:
            response["market_comparison"] = {
                "status": "unavailable",
                "providers": [],
                "notice": "Prediction-market comparison is temporarily unavailable.",
            }
    return response
