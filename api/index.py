"""
Tennis Simulator API - Vercel Compatible Version
Simplified without WebSocket - returns results synchronously
"""

from flask import Flask, request, jsonify, send_from_directory
import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data_loader import TennisDataLoader
from simulation_engine import TennisSimulator

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# Initialize data loader and simulator
data_loader = TennisDataLoader()
simulator = TennisSimulator()

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('../templates', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('../static', path)

@app.route('/api/players', methods=['GET'])
def get_players():
    """Get list of all available players"""
    try:
        players = data_loader.get_all_players()
        return jsonify({"players": players})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/simulate', methods=['POST'])
def simulate_match():
    """
    Run Monte Carlo simulation for a match
    Returns results synchronously (no progress updates)
    """
    try:
        # Get request data
        data = request.get_json()

        # Validate input
        required_fields = ['player1', 'player2', 'format', 'num_simulations']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        player1_name = data['player1']
        player2_name = data['player2']
        format_type = data['format']
        num_simulations = int(data.get('num_simulations', 1000))

        # Validate format and simulation count
        if format_type not in ['best3', 'best5']:
            return jsonify({"error": "Format must be 'best3' or 'best5'"}), 400

        if num_simulations < 1 or num_simulations > 10000:
            return jsonify({"error": "Number of simulations must be between 1 and 10000"}), 400

        # Run simulations for all surfaces
        surfaces = ['hard', 'clay', 'grass']
        all_results = {}
        all_fallback_warnings = []

        for surface in surfaces:
            try:
                p1_stats, p1_fallback = data_loader.get_player_stats(player1_name, surface)
                p2_stats, p2_fallback = data_loader.get_player_stats(player2_name, surface)

                # Track fallback warnings
                surface_warnings = []
                if p1_fallback:
                    warning = data_loader.get_fallback_warning(player1_name, surface)
                    if warning:
                        surface_warnings.append(warning)
                if p2_fallback:
                    warning = data_loader.get_fallback_warning(player2_name, surface)
                    if warning:
                        surface_warnings.append(warning)

                # Run simulation (no progress callback for Vercel)
                results = simulator.run_monte_carlo_simulation(
                    p1_stats, p2_stats, format_type, num_simulations,
                    progress_callback=None,  # No progress tracking
                    track_detailed_stats=True
                )

                # Build response for this surface
                surface_result = {
                    "player1_win_pct": results["player1_win_pct"],
                    "player2_win_pct": results["player2_win_pct"],
                    "player1_wins": results["player1_wins"],
                    "player2_wins": results["player2_wins"],
                    "set_distributions": results["set_distributions"],
                    "total_simulations": results["total_simulations"],
                    "fallback_warnings": surface_warnings,
                    "input_parameters": {
                        "player1": {
                            "first_serve_in_pct": p1_stats['first_serve_in_pct'],
                            "first_serve_win_pct": p1_stats['first_serve_win_pct'],
                            "second_serve_in_pct": 1.0 - p1_stats['double_fault_per_second_serve'],
                            "second_serve_win_pct": p1_stats['second_serve_win_pct'],
                            "vs_first_serve_win_pct": p1_stats['vs_first_serve_win_pct'],
                            "vs_second_serve_win_pct": p1_stats['vs_second_serve_win_pct'],
                            "break_point_save_pct": p1_stats['break_point_save_pct'],
                            "break_point_conversion_pct": p1_stats['break_point_conversion_pct']
                        },
                        "player2": {
                            "first_serve_in_pct": p2_stats['first_serve_in_pct'],
                            "first_serve_win_pct": p2_stats['first_serve_win_pct'],
                            "second_serve_in_pct": 1.0 - p2_stats['double_fault_per_second_serve'],
                            "second_serve_win_pct": p2_stats['second_serve_win_pct'],
                            "vs_first_serve_win_pct": p2_stats['vs_first_serve_win_pct'],
                            "vs_second_serve_win_pct": p2_stats['vs_second_serve_win_pct'],
                            "break_point_save_pct": p2_stats['break_point_save_pct'],
                            "break_point_conversion_pct": p2_stats['break_point_conversion_pct']
                        }
                    }
                }

                # Add observed statistics if available
                if "observed_stats" in results:
                    surface_result["observed_stats"] = results["observed_stats"]

                all_results[surface] = surface_result
                all_fallback_warnings.extend(surface_warnings)

            except ValueError as e:
                return jsonify({"error": f"Error for {surface} surface: {str(e)}"}), 400

        # Return complete results
        response = {
            "surfaces": all_results,
            "player1_name": player1_name,
            "player2_name": player2_name,
            "format": format_type,
            "num_simulations": num_simulations,
            "fallback_warnings": all_fallback_warnings
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Simulation failed: {str(e)}"}), 500

# For local development
if __name__ == '__main__':
    app.run(debug=True, port=5002)
