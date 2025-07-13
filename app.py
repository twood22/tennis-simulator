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
    """Run match simulation"""
    try:
        data = request.get_json()
        
        # Validate input
        required_fields = ['player1', 'player2', 'surface', 'format']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        player1_name = data['player1']
        player2_name = data['player2']
        surface = data['surface']
        format_type = data['format']
        
        # Validate format
        if format_type not in ['best3', 'best5']:
            return jsonify({"error": "Format must be 'best3' or 'best5'"}), 400
        
        # Validate surface
        if surface not in ['hard', 'clay', 'grass']:
            return jsonify({"error": "Surface must be 'hard', 'clay', or 'grass'"}), 400
        
        # Get player statistics
        try:
            p1_stats, p1_fallback = data_loader.get_player_stats(player1_name, surface)
            p2_stats, p2_fallback = data_loader.get_player_stats(player2_name, surface)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        # Prepare fallback warnings
        fallback_warnings = []
        if p1_fallback:
            warning = data_loader.get_fallback_warning(player1_name, surface)
            if warning:
                fallback_warnings.append(warning)
        if p2_fallback:
            warning = data_loader.get_fallback_warning(player2_name, surface)
            if warning:
                fallback_warnings.append(warning)
        
        # Run simulation in a separate thread to allow for progress updates
        simulation_id = request.sid if hasattr(request, 'sid') else 'default'
        
        def progress_callback(completed, total):
            progress_pct = (completed / total) * 100
            socketio.emit('simulation_progress', {
                'completed': completed,
                'total': total,
                'progress': progress_pct
            })
        
        # Run the simulation
        results = simulator.run_monte_carlo_simulation(
            p1_stats, p2_stats, format_type, 1000, progress_callback
        )
        
        # Format response
        response = {
            "player1_win_pct": results["player1_win_pct"],
            "player2_win_pct": results["player2_win_pct"],
            "player1_wins": results["player1_wins"],
            "player2_wins": results["player2_wins"],
            "set_distributions": results["set_distributions"],
            "fallback_warnings": fallback_warnings,
            "total_simulations": results["total_simulations"]
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
    """Handle simulation request via WebSocket"""
    try:
        # Validate input
        required_fields = ['player1', 'player2', 'surface', 'format']
        for field in required_fields:
            if field not in data:
                emit('simulation_error', {"error": f"Missing required field: {field}"})
                return
        
        player1_name = data['player1']
        player2_name = data['player2']
        surface = data['surface']
        format_type = data['format']
        
        # Validate format and surface
        if format_type not in ['best3', 'best5']:
            emit('simulation_error', {"error": "Format must be 'best3' or 'best5'"})
            return
        
        if surface not in ['hard', 'clay', 'grass']:
            emit('simulation_error', {"error": "Surface must be 'hard', 'clay', or 'grass'"})
            return
        
        # Get player statistics
        try:
            p1_stats, p1_fallback = data_loader.get_player_stats(player1_name, surface)
            p2_stats, p2_fallback = data_loader.get_player_stats(player2_name, surface)
        except ValueError as e:
            emit('simulation_error', {"error": str(e)})
            return
        
        # Prepare fallback warnings
        fallback_warnings = []
        if p1_fallback:
            warning = data_loader.get_fallback_warning(player1_name, surface)
            if warning:
                fallback_warnings.append(warning)
        if p2_fallback:
            warning = data_loader.get_fallback_warning(player2_name, surface)
            if warning:
                fallback_warnings.append(warning)
        
        # Get current session ID for emitting to specific client
        session_id = request.sid
        
        # Progress callback function
        def progress_callback(completed, total):
            progress_pct = (completed / total) * 100
            socketio.emit('simulation_progress', {
                'completed': completed,
                'total': total,
                'progress': progress_pct
            }, to=session_id)
        
        # Run simulation in a separate thread
        def run_simulation():
            try:
                results = simulator.run_monte_carlo_simulation(
                    p1_stats, p2_stats, format_type, 1000, progress_callback
                )
                
                response = {
                    "player1_win_pct": results["player1_win_pct"],
                    "player2_win_pct": results["player2_win_pct"],
                    "player1_wins": results["player1_wins"],
                    "player2_wins": results["player2_wins"],
                    "set_distributions": results["set_distributions"],
                    "fallback_warnings": fallback_warnings,
                    "total_simulations": results["total_simulations"]
                }
                
                socketio.emit('simulation_complete', response, to=session_id)
                
            except Exception as e:
                socketio.emit('simulation_error', {"error": f"Simulation failed: {str(e)}"}, to=session_id)
        
        # Start simulation in background thread
        thread = threading.Thread(target=run_simulation)
        thread.daemon = True
        thread.start()
        
        emit('simulation_started', {'status': 'Simulation started'})
        
    except Exception as e:
        emit('simulation_error', {"error": f"Failed to start simulation: {str(e)}"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)