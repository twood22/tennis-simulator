from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import json
import threading
from data_loader import TennisDataLoader
from simulation_engine import TennisSimulator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tennis_simulator_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize data loader and simulator
data_loader = TennisDataLoader()
simulator = TennisSimulator()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/players', methods=['GET'])
def get_players():
    """Get all available players with their rankings and surfaces"""
    try:
        players = data_loader.get_all_players()
        return jsonify({"players": players})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/simulate', methods=['POST'])
def simulate_match():
    """Run unified match simulation for all surfaces"""
    try:
        data = request.get_json()
        
        # Validate input
        required_fields = ['player1', 'player2', 'format', 'num_simulations']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        player1_name = data['player1']
        player2_name = data['player2']
        format_type = data['format']
        num_simulations = int(data['num_simulations'])
        
        # Validate format
        if format_type not in ['best3', 'best5']:
            return jsonify({"error": "Format must be 'best3' or 'best5'"}), 400
        
        # Validate number of simulations
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
                
                # Track fallback warnings for this surface
                surface_warnings = []
                if p1_fallback:
                    warning = data_loader.get_fallback_warning(player1_name, surface)
                    if warning:
                        surface_warnings.append(warning)
                if p2_fallback:
                    warning = data_loader.get_fallback_warning(player2_name, surface)
                    if warning:
                        surface_warnings.append(warning)
                
                # Run simulation for this surface
                def progress_callback(completed, total):
                    # Calculate overall progress across all surfaces
                    surface_index = surfaces.index(surface)
                    overall_completed = (surface_index * num_simulations) + completed
                    overall_total = len(surfaces) * num_simulations
                    progress_pct = (overall_completed / overall_total) * 100
                    socketio.emit('simulation_progress', {
                        'completed': overall_completed,
                        'total': overall_total,
                        'progress': progress_pct,
                        'current_surface': surface
                    })
                
                # Always track detailed stats for parameter comparison
                track_detailed = True
                
                results = simulator.run_monte_carlo_simulation(
                    p1_stats, p2_stats, format_type, num_simulations, 
                    progress_callback, track_detailed
                )
                
                # Add input parameters and observed stats comparison
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
                            "break_point_save_pct": p1_stats['break_point_save_pct'],
                            "double_fault_per_second_serve": p1_stats['double_fault_per_second_serve'],
                            "vs_first_serve_win_pct": p1_stats['vs_first_serve_win_pct'],
                            "vs_second_serve_win_pct": p1_stats['vs_second_serve_win_pct'],
                            "break_point_conversion_pct": p1_stats['break_point_conversion_pct']
                        },
                        "player2": {
                            "first_serve_in_pct": p2_stats['first_serve_in_pct'],
                            "first_serve_win_pct": p2_stats['first_serve_win_pct'],
                            "second_serve_in_pct": 1.0 - p2_stats['double_fault_per_second_serve'],
                            "second_serve_win_pct": p2_stats['second_serve_win_pct'],
                            "break_point_save_pct": p2_stats['break_point_save_pct'],
                            "double_fault_per_second_serve": p2_stats['double_fault_per_second_serve'],
                            "vs_first_serve_win_pct": p2_stats['vs_first_serve_win_pct'],
                            "vs_second_serve_win_pct": p2_stats['vs_second_serve_win_pct'],
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
        
        # Format final response
        response = {
            "surfaces": all_results,
            "player1_name": player1_name,
            "player2_name": player2_name,
            "format": format_type,
            "num_simulations": num_simulations,
            "fallback_warnings": all_fallback_warnings
        }
        
        # Emit completion event
        socketio.emit('simulation_complete', response)
        
        return jsonify(response)
        
    except Exception as e:
        error_msg = {"error": f"Simulation failed: {str(e)}"}
        socketio.emit('simulation_error', error_msg)
        return jsonify(error_msg), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'status': 'Connected to tennis simulator'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('start_simulation')
def handle_simulation_request(data):
    """Handle unified simulation request via WebSocket"""
    print(f"[DEBUG] Received start_simulation event with data: {data}")
    try:
        # Validate input
        required_fields = ['player1', 'player2', 'format', 'num_simulations']
        for field in required_fields:
            if field not in data:
                emit('simulation_error', {"error": f"Missing required field: {field}"})
                return
        
        player1_name = data['player1']
        player2_name = data['player2']
        format_type = data['format']
        num_simulations = int(data.get('num_simulations', 1000))
        
        # Validate format and simulation count
        if format_type not in ['best3', 'best5']:
            emit('simulation_error', {"error": "Format must be 'best3' or 'best5'"})
            return
        
        if num_simulations < 1 or num_simulations > 10000:
            emit('simulation_error', {"error": "Number of simulations must be between 1 and 10000"})
            return
        
        # Get current session ID for emitting to specific client
        session_id = request.sid
        
        # Run simulations for all surfaces in a separate thread
        def run_simulation():
            print("[DEBUG] Simulation thread started")
            try:
                surfaces = ['hard', 'clay', 'grass']
                all_results = {}
                all_fallback_warnings = []

                for surface in surfaces:
                    print(f"[DEBUG] Processing surface: {surface}")
                    try:
                        p1_stats, p1_fallback = data_loader.get_player_stats(player1_name, surface)
                        p2_stats, p2_fallback = data_loader.get_player_stats(player2_name, surface)
                        
                        # Track fallback warnings for this surface
                        surface_warnings = []
                        if p1_fallback:
                            warning = data_loader.get_fallback_warning(player1_name, surface)
                            if warning:
                                surface_warnings.append(warning)
                        if p2_fallback:
                            warning = data_loader.get_fallback_warning(player2_name, surface)
                            if warning:
                                surface_warnings.append(warning)
                        
                        # Progress callback function - capture current surface value
                        current_surface = surface
                        surface_index = surfaces.index(current_surface)

                        def make_progress_callback(surf, surf_idx):
                            def progress_callback(completed, total):
                                overall_completed = (surf_idx * num_simulations) + completed
                                overall_total = len(surfaces) * num_simulations
                                progress_pct = (overall_completed / overall_total) * 100
                                socketio.emit('simulation_progress', {
                                    'completed': overall_completed,
                                    'total': overall_total,
                                    'progress': progress_pct,
                                    'current_surface': surf
                                }, to=session_id)
                            return progress_callback

                        progress_callback = make_progress_callback(current_surface, surface_index)
                        
                        # Always track detailed stats for parameter comparison
                        track_detailed = True
                        
                        results = simulator.run_monte_carlo_simulation(
                            p1_stats, p2_stats, format_type, num_simulations, 
                            progress_callback, track_detailed
                        )
                        
                        # Add input parameters and observed stats comparison
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
                                    "break_point_save_pct": p1_stats['break_point_save_pct'],
                                    "double_fault_per_second_serve": p1_stats['double_fault_per_second_serve'],
                                    "vs_first_serve_win_pct": p1_stats['vs_first_serve_win_pct'],
                                    "vs_second_serve_win_pct": p1_stats['vs_second_serve_win_pct'],
                                    "break_point_conversion_pct": p1_stats['break_point_conversion_pct']
                                },
                                "player2": {
                                    "first_serve_in_pct": p2_stats['first_serve_in_pct'],
                                    "first_serve_win_pct": p2_stats['first_serve_win_pct'],
                                    "second_serve_in_pct": 1.0 - p2_stats['double_fault_per_second_serve'],
                                    "second_serve_win_pct": p2_stats['second_serve_win_pct'],
                                    "break_point_save_pct": p2_stats['break_point_save_pct'],
                                    "double_fault_per_second_serve": p2_stats['double_fault_per_second_serve'],
                                    "vs_first_serve_win_pct": p2_stats['vs_first_serve_win_pct'],
                                    "vs_second_serve_win_pct": p2_stats['vs_second_serve_win_pct'],
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
                        socketio.emit('simulation_error', {"error": f"Error for {surface} surface: {str(e)}"}, to=session_id)
                        return
                
                # Format final response
                response = {
                    "surfaces": all_results,
                    "player1_name": player1_name,
                    "player2_name": player2_name,
                    "format": format_type,
                    "num_simulations": num_simulations,
                    "fallback_warnings": all_fallback_warnings
                }
                
                print("[DEBUG] Emitting simulation_complete event")
                socketio.emit('simulation_complete', response, to=session_id)
                print("[DEBUG] Simulation complete event emitted successfully")

            except Exception as e:
                print(f"[DEBUG] Simulation error: {str(e)}")
                socketio.emit('simulation_error', {"error": f"Simulation failed: {str(e)}"}, to=session_id)
        
        # Start simulation in background thread using socketio's background task
        print(f"[DEBUG] Starting simulation thread for {player1_name} vs {player2_name}")
        socketio.start_background_task(run_simulation)

        print("[DEBUG] Emitting simulation_started event")
        emit('simulation_started', {'status': 'Simulation started'})
        
    except Exception as e:
        emit('simulation_error', {"error": f"Failed to start simulation: {str(e)}"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5002, debug=True, allow_unsafe_werkzeug=True)