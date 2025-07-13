# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a tennis match simulator that uses real player statistics to run Monte Carlo simulations. The project consists of a Python backend simulation engine and an HTML/CSS/JavaScript frontend with WebSocket communication for real-time progress updates.

## Data Structure
The project uses 4 CSV files in the `data/` directory:
- `Tennis abstract serve.csv`: serving statistics
- `Tennis abstract return.csv`: return statistics  
- `Tennis abstract breaks.csv`: break point statistics
- `Tennis abstract more.csv`: additional match statistics

Data is indexed by (player_name, surface) with fallback logic: when a player lacks data for a specific surface, use their hard court statistics instead.

## Architecture Overview

### Backend (Python)
- **Framework**: Flask or FastAPI
- **Data Processing**: pandas for CSV loading, numpy for simulation calculations
- **Simulation Engine**: Monte Carlo approach running exactly 1000 match simulations
- **Communication**: RESTful API with WebSocket/SSE for progress updates

### Frontend 
- **Technology**: HTML/CSS/JavaScript (vanilla or lightweight framework)
- **Visualization**: Chart.js or similar for set score distribution histograms
- **Real-time Updates**: WebSocket or EventSource for simulation progress

### Key API Endpoints
- `GET /api/players` - Returns available players with rankings and surfaces
- `POST /api/simulate` - Runs simulation with player1, player2, surface, and format parameters

## Simulation Algorithm

### Point Simulation Logic
For break points: Use dedicated break_point_save_pct and break_point_conversion_pct statistics.

For regular points:
1. Check first serve percentage (random < first_serve_in_pct)
2. If first serve in: Calculate win probability using dominance ratio weighting
3. If first serve out: Check second serve (1 - double_fault_per_second_serve)
4. Apply similar calculations for second serve or award point to returner on double fault

### Game/Set/Match Logic
- Standard tennis scoring with deuce handling
- Tiebreaks at 6-6 with proper server rotation
- Configurable match formats (best of 3 or 5 sets)
- Alternate starting server each set

## Performance Requirements
- Simulation should complete 1000 matches in under 10 seconds
- Progress updates every 100 simulations
- Cache player data after initial load to avoid repeated CSV parsing

## Attribution Requirements
All implementations must include clear attribution: "Player statistics provided by Tennis Abstract (tennisabstract.com)" with a link to the source website.

## Development Notes
- No existing code files are present - this is a greenfield project
- Focus on clean separation of concerns between data loading, simulation engine, and API layer
- Implement comprehensive error handling for missing data and invalid inputs
- Structure code for testability with unit tests for simulation logic