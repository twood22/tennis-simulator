# Tennis Match Simulator - Implementation Instructions

Create a tennis match simulator with the following specifications: 

## Project Structure
Create a web application with a Python backend and HTML/JS frontend that simulates tennis matches between players using real statistics.

## Data Files
You have 4 CSV files with tennis statistics in the data directory:
- `Tennis abstract serve.csv`: serving statistics  
- `Tennis abstract return.csv`: return statistics
- `Tennis abstract breaks.csv`: break point statistics
- `Tennis abstract more.csv`: additional match statistics

Each file contains data for players on different surfaces (hard, clay, grass). Note that not all players have data for all surfaces.

## Backend Requirements (Python)

### 1. Data Loading Module
Create a module that:
- Loads all CSV files into memory
- Creates a unified data structure mapping (player_name, surface) → statistics
- Implements fallback logic: when a player lacks data for a specific surface, use their hard court statistics instead
- Tracks which players are using fallback data for UI warnings
- Handles data type conversions (percentages from strings to floats)

### 2. Simulation Engine

#### Point Simulation Logic:
```python
def simulate_point(server_stats, returner_stats, is_break_point=False):
    """
    For break points:
    - Use server's break_point_save_pct directly
    - Use returner's break_point_conversion_pct directly
    
    For regular points:
    1. Check if first serve is in (random < first_serve_in_pct)
    2. If first serve in:
       - server_strength = server.first_serve_win_pct
       - returner_strength = 1 - returner.vs_first_serve_win_pct  
       - Use dominance_ratio to weight: 
         win_prob = (server_strength * server.dominance_ratio + 
                    returner_strength * returner.dominance_ratio) / 
                    (server.dominance_ratio + returner.dominance_ratio)
    3. If first serve out:
       - second_serve_in_pct = 1 - server.double_fault_per_second_serve
       - If second serve in: similar calculation with second serve stats
       - If second serve out: returner wins point
    """
```

#### Game Logic:
- Standard tennis scoring: 0, 15, 30, 40, game
- Deuce at 40-40, must win by 2 points
- Track whether game point is also a break point

#### Tiebreak Logic:
- Starts at 6-6 in a set
- First server serves 1 point, then players alternate every 2 points
- First to 7 points with 2-point margin wins
- Proper server rotation after tiebreak ends

#### Set/Match Logic:
- First to 6 games (win by 2) wins the set
- Tiebreak at 6-6
- Match formats: best of 3 or best of 5 sets
- Alternate starting server each set

### 3. API Endpoints

```python
# GET /api/players
# Returns: {
#   "players": [
#     {"name": "Player Name", "ranking": 1, "surfaces": ["hard", "clay", "grass"]}
#   ]
# }

# POST /api/simulate  
# Request body: {
#   "player1": "Player Name",
#   "player2": "Player Name",
#   "surface": "hard|clay|grass", 
#   "format": "best3|best5"
# }
# Returns: {
#   "player1_win_pct": 0.65,
#   "player2_win_pct": 0.35,
#   "player1_wins": 650,
#   "player2_wins": 350,
#   "set_distributions": {
#     "3-0": 120, "3-1": 230, "3-2": 300,
#     "2-3": 250, "1-3": 80, "0-3": 20
#   },
#   "fallback_warnings": ["Player 1 using hard court data for clay surface"]
# }
```

### 4. Monte Carlo Simulation
- Run exactly 1000 match simulations
- Use WebSocket or Server-Sent Events to send progress updates every 100 simulations
- Track and aggregate:
  - Win/loss counts for each player
  - Distribution of set scores (e.g., 3-0, 3-1, 3-2, etc.)
  - Any other interesting statistics from the data

## Frontend Requirements

### 1. UI Layout
Create a clean, intuitive interface with:
- Two dropdown menus for player selection (populate from /api/players)
- Radio button group for surface selection (Hard/Clay/Grass)
- Radio button group for match format (Best of 3/Best of 5)
- "Simulate" button that triggers the simulation
- Progress bar that updates during simulation (0-100%)
- Results panel (initially hidden) that displays after simulation completes

### 2. Results Display
Show:
- Large, prominent win percentages for each player
- W-L record from the 1000 simulations
- Histogram or bar chart showing set score distributions
- Visual warning if either player's statistics use fallback data
- "Run Another Simulation" button to reset

### 3. User Experience
- Disable all inputs while simulation is running
- Show smooth progress bar updates via WebSocket/SSE
- Display clear error messages for any issues
- Make the interface responsive for different screen sizes

### 4. Attribution
- Include clear attribution on the page: "Player statistics provided by Tennis Abstract"
- Include a link to Tennis Abstract (tennisabstract.com) in the attribution
- Place attribution in the footer or near the results section where it's visible but not intrusive

## Implementation Guidelines

### Python Backend:
- Use Flask or FastAPI for the web framework
- Use pandas for CSV processing
- Use numpy for efficient random number generation
- Implement proper error handling for missing data
- Structure code with clear separation of concerns

### Frontend:
- Can use vanilla JavaScript or a lightweight framework
- Use fetch API for HTTP requests
- Implement WebSocket or EventSource for progress updates
- Consider using Chart.js or similar for the histogram
- Keep the design clean and professional

### Performance Considerations:
- The simulation should complete 1000 matches in a reasonable time (< 10 seconds)
- Consider using numpy arrays for batch operations where possible
- Cache player data after initial load to avoid repeated CSV parsing

## Deliverables

Create a complete, working application with:
1. All Python backend files with clear module structure
2. HTML file with the UI layout
3. CSS file for styling (clean, modern design)
4. JavaScript file for frontend logic
5. requirements.txt with all Python dependencies
6. README.md with:
   - Setup instructions
   - How to run the application
   - Brief explanation of the simulation algorithm
   - Any assumptions or design decisions made
   - Attribution: "Player statistics provided by Tennis Abstract (tennisabstract.com)"

## Additional Notes
- Ensure the code is well-commented and readable
- Handle edge cases gracefully (missing players, invalid inputs, etc.)
- The simulation should accurately model tennis rules and scoring
- Make the progress updates smooth and informative
- Test with various player combinations and surfaces