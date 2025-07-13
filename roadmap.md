# Tennis Simulator Technical Roadmap

## Project Overview
A web-based tennis match simulator that uses real player statistics to run Monte Carlo simulations of matches between top players on different surfaces.

## Architecture Overview
- **Backend**: Python (Flask/FastAPI) for simulation engine
- **Frontend**: HTML/CSS/JavaScript with clean, responsive UI
- **Data Layer**: CSV parsing with intelligent fallback handling
- **Communication**: RESTful API with WebSocket/SSE for progress updates

## Phase 1: Data Processing & Management

### 1.1 Data Loading Module
- Load 4 CSV files: serve, return, breaks, and more statistics
- Parse into unified data structure indexed by (player, surface)
- Implement surface fallback logic (missing surface → hard court data)
- Create data validation to ensure all required fields present

### 1.2 Player Registry
- Build comprehensive player list from all surfaces
- Track which players have native vs. fallback data per surface
- Expose player metadata (ranking, available surfaces)

### 1.3 Statistics Processing
- Convert percentage strings to floats
- Calculate derived statistics (e.g., second_serve_in_pct)
- Normalize data formats across different CSV structures

## Phase 2: Simulation Engine

### 2.1 Point Simulation Logic
```
Core Algorithm:
1. Determine server's first_serve_in (random < first_serve_in_pct)
2. If first serve in:
   - Calculate win_prob using dominance ratio weighting:
     server_strength = server.first_serve_win_pct
     returner_strength = 1 - returner.vs_first_serve_win_pct
     combined = weighted_average(server_strength, returner_strength, dominance_ratios)
3. If first serve out:
   - Calculate second_serve_in (random < (1 - double_fault_per_second_serve))
   - If in: similar calculation with second serve stats
   - If out: returner wins point
4. Special handling for break points using dedicated statistics
```

### 2.2 Game Simulation
- Implement tennis scoring (0, 15, 30, 40, deuce, advantage)
- Track current server and game score
- Handle deuce situations (win by 2)
- Return game winner and final score

### 2.3 Set Simulation  
- Standard set rules (first to 6, win by 2)
- Tiebreak at 6-6:
  - Alternate serving: 1-2-2-2... pattern
  - First to 7 points (win by 2)
  - Proper server rotation after tiebreak
- Track games won and set score

### 2.4 Match Simulation
- Configurable format (best of 3 or 5 sets)
- Alternate starting server each set
- Track set scores and match winner
- Collect match statistics for aggregation

### 2.5 Monte Carlo Wrapper
- Run 1000 match simulations
- Track progress (every 100 simulations)
- Aggregate results:
  - Win/loss counts
  - Set score distributions
  - Average games per set
- Emit progress events for frontend

## Phase 3: API Layer

### 3.1 RESTful Endpoints
```
GET /api/players
Response: {
  players: [
    {name: "Player Name", ranking: 1, surfaces: ["hard", "clay", "grass"]}
  ]
}

POST /api/simulate
Request: {
  player1: "Name",
  player2: "Name", 
  surface: "hard|clay|grass",
  format: "best3|best5"
}
Response: {
  player1_win_pct: 0.65,
  player2_win_pct: 0.35,
  player1_wins: 650,
  player2_wins: 350,
  set_distributions: {
    "3-0": 120,
    "3-1": 230,
    "3-2": 300,
    "2-3": 250,
    "1-3": 80,
    "0-3": 20
  },
  fallback_warnings: ["Player 1 using hard court data for clay"]
}
```

### 3.2 Progress Updates
- WebSocket connection for real-time progress
- Emit updates every 100 simulations
- Include current simulation count and estimated time remaining

## Phase 4: Frontend Development

### 4.1 UI Components
- Player selection dropdowns (searchable)
- Surface selection (radio buttons)
- Format selection (radio buttons)
- Simulate button with loading state
- Progress bar with percentage
- Results panel (hidden until simulation complete)

### 4.2 Results Visualization
- Win percentage display (large, prominent)
- W-L record
- Set score distribution (histogram/bar chart)
- Fallback data warnings (if applicable)
- "Run Another Simulation" button

### 4.3 User Experience
- Disable inputs during simulation
- Smooth progress bar animations
- Clear error messages for edge cases
- Responsive design for mobile/tablet
- Attribution: Display "Player statistics provided by Tennis Abstract" with link to tennisabstract.com

## Phase 5: Testing & Optimization

### 5.1 Performance Optimization
- Profile simulation code for bottlenecks
- Implement numpy vectorization where possible
- Consider multiprocessing for simulations
- Cache player data after initial load

### 5.2 Testing Strategy
- Unit tests for simulation logic
- Integration tests for API endpoints
- Frontend testing for UI interactions
- Edge case testing (missing data, invalid inputs)

## Technical Considerations

### Dependencies
- Backend: Flask/FastAPI, pandas, numpy, websockets
- Frontend: Vanilla JS or lightweight framework
- Visualization: Chart.js or D3.js for histograms

### Error Handling
- Graceful handling of missing player data
- Network error recovery
- Invalid input validation
- Simulation timeout handling

### Scalability Considerations
- Simulation caching for repeated queries
- Concurrent simulation support
- Database integration for future enhancements
- API rate limiting

## Delivery Checklist
- [ ] All source code files
- [ ] Requirements.txt for Python dependencies
- [ ] README with setup instructions
- [ ] Sample run instructions
- [ ] Basic documentation of simulation algorithm
- [ ] Error handling for common edge cases
- [ ] Attribution to Tennis Abstract for player statistics