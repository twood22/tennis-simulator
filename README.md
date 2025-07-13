# Tennis Match Simulator

A web-based tennis match simulator that uses real player statistics to run Monte Carlo simulations of matches between top players on different surfaces.

## Features

- **Real Player Statistics**: Uses data from Tennis Abstract covering serve, return, break point, and match statistics
- **Surface-Specific Simulation**: Simulates matches on hard court, clay, and grass surfaces
- **Monte Carlo Analysis**: Runs 1000 match simulations to provide statistical predictions
- **Real-Time Progress**: WebSocket-powered progress updates during simulation
- **Interactive Visualization**: Charts showing set score distributions
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Setup Instructions

### Prerequisites
- Python 3.9 or higher
- Poetry (Python dependency manager)

### Installation

1. Clone or download this repository
2. Navigate to the project directory:
   ```bash
   cd tennis-simulator
   ```

3. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

### Running the Application

1. Start the Flask server:
   ```bash
   poetry run python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5001
   ```

3. The application will automatically load player data and be ready for simulations.

## How to Use

1. **Select Players**: Choose two different players from the dropdown menus
2. **Choose Surface**: Select Hard Court, Clay, or Grass
3. **Pick Format**: Choose Best of 3 or Best of 5 sets
4. **Run Simulation**: Click "Simulate Match" to start the Monte Carlo analysis
5. **View Results**: Watch the progress bar and see detailed results including win percentages and set score distributions

## Simulation Algorithm

### Point-Level Simulation
The simulator uses a sophisticated point-by-point approach:

- **Serve Simulation**: Models first serve percentage, win rates, and double fault rates
- **Dominance Weighting**: Combines server and returner strengths using player dominance ratios
- **Break Points**: Uses dedicated break point conversion and save statistics
- **Surface Adaptation**: Automatically falls back to hard court data when surface-specific data is unavailable

### Match Structure
- Proper tennis scoring (0, 15, 30, 40, deuce)
- Standard set rules (first to 6 games, win by 2)
- Tiebreaks at 6-6 with correct serving rotation
- Configurable match formats (best of 3 or 5 sets)

### Statistical Aggregation
Each simulation runs exactly 1000 matches and tracks:
- Win/loss counts for each player
- Set score distributions (3-0, 3-1, 3-2, etc.)
- Win percentages with decimal precision

## Project Structure

```
tennis-simulator/
├── app.py                 # Flask application with WebSocket support
├── data_loader.py         # CSV data processing and player statistics
├── simulation_engine.py   # Tennis match simulation logic
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main web interface
├── static/
│   ├── style.css         # Application styling
│   └── script.js         # Frontend JavaScript with WebSocket client
└── data/
    ├── Tennis abstract - serve.csv
    ├── Tennis abstract - return.csv
    ├── Tennis abstract - breaks.csv
    └── Tennis abstract - more.csv
```

## Design Decisions

### Data Handling
- **Fallback Logic**: When a player lacks data for a specific surface, the system uses their hard court statistics with a warning to the user
- **Unified Structure**: All CSV files are merged into a single data structure indexed by (player, surface) for efficient access
- **Data Validation**: Percentage values are automatically converted from strings to floats

### Performance Optimization
- **Cached Player Data**: CSV files are loaded once at startup to avoid repeated parsing
- **Efficient Random Generation**: Uses Python's optimized random module for fast point simulation
- **Background Processing**: Simulations run in separate threads to maintain UI responsiveness

### User Experience
- **Real-Time Feedback**: Progress updates every 100 simulations via WebSocket
- **Clear Warnings**: Visual indicators when fallback data is used
- **Responsive Design**: Adapts to different screen sizes and devices
- **Error Handling**: Graceful handling of missing data and network issues

## Attribution

Player statistics provided by [Tennis Abstract](https://tennisabstract.com)

## Technical Requirements

- **Backend**: Flask with SocketIO for real-time communication
- **Frontend**: Vanilla JavaScript with Chart.js for visualizations
- **Data Processing**: Pandas for CSV handling, NumPy for statistical operations
- **Real-Time Communication**: WebSocket for progress updates during simulation
