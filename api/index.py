"""Flask entry point used locally and by Vercel."""

import os
import sys

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_loader import TennisDataLoader
from market_odds import get_market_comparison
from simulation_service import ValidationError, run_simulation_request
from upcoming_service import UpcomingMatchService


app = Flask(__name__, template_folder="../templates", static_folder="../static")
data_loader = TennisDataLoader()
upcoming_service = UpcomingMatchService(data_loader)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/players")
def get_players():
    return jsonify({"players": data_loader.get_all_players()})


@app.get("/healthz")
def healthcheck():
    return jsonify({"status": "ok", "data_version": upcoming_service.data_version})


@app.get("/api/upcoming")
def upcoming_matches():
    try:
        days = int(request.args.get("days", 7))
    except ValueError:
        return jsonify({"error": "Days must be an integer"}), 400
    if not 1 <= days <= 7:
        return jsonify({"error": "Days must be between 1 and 7"}), 400
    try:
        response = jsonify(upcoming_service.get_upcoming(days=days))
        response.headers["Cache-Control"] = "public, max-age=60"
        return response
    except Exception:
        app.logger.exception("Upcoming-match discovery failed")
        return jsonify({"error": "Upcoming matches are temporarily unavailable"}), 503


@app.get("/api/upcoming/<match_id>/simulation")
def upcoming_simulation(match_id):
    try:
        response = jsonify(upcoming_service.get_simulation(match_id))
        response.headers["Cache-Control"] = "public, max-age=300"
        return response
    except KeyError:
        return jsonify({"error": "Upcoming match not found"}), 404
    except ValueError as error:
        return jsonify({"error": str(error)}), 422
    except Exception:
        app.logger.exception("Upcoming-match simulation failed")
        return jsonify({"error": "Match simulation is temporarily unavailable"}), 503


@app.post("/api/simulate")
def simulate_match():
    try:
        payload = request.get_json(silent=True)
        return jsonify(run_simulation_request(
            payload, data_loader, market_odds_provider=get_market_comparison
        ))
    except (ValidationError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("Simulation request failed")
        return jsonify({"error": "Simulation failed"}), 500


@app.get("/api/market-odds")
def market_odds():
    player1 = request.args.get("player1", "").strip()
    player2 = request.args.get("player2", "").strip()
    if not player1 or not player2:
        return jsonify({"error": "Both player1 and player2 are required"}), 400
    if player1 == player2:
        return jsonify({"error": "Players must be different"}), 400
    return jsonify(get_market_comparison(player1, player2))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=False)
