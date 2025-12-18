# Tennis Match Simulator

A web-based tennis match simulator that uses real player statistics to run Monte Carlo simulations of matches between top players on different surfaces.

## Features

- **Real Player Statistics**: Uses data from Tennis Abstract covering serve, return, break point, and match statistics
- **Multi-Surface Analysis**: Simulates matches on hard court, clay, and grass surfaces simultaneously
- **Monte Carlo Analysis**: Runs configurable simulations (100-10,000) for statistical predictions
- **Real-Time Progress**: WebSocket-powered progress updates during simulation
- **Interactive Visualization**: Charts showing set score distributions for each surface
- **Parameter Analysis**: Compare expected vs observed statistics
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Quick Start

### Option 1: Using pip (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/tennis-simulator.git
cd tennis-simulator

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Option 2: Using Poetry

```bash
poetry install
poetry run python app.py
```

Then open http://localhost:5002 in your browser.

## How to Use

1. **Select Players**: Choose two different players from the dropdown menus (ranked by ATP ranking)
2. **Configure Settings**:
   - Choose Best of 3 or Best of 5 sets
   - Set the number of simulations (default: 1000)
3. **Run Simulation**: Click "Run Simulation" to start
4. **View Results**:
   - Win probabilities for each surface
   - Set score distribution charts
   - Detailed parameter analysis showing expected vs observed performance

## Simulation Algorithm

### Point-Level Simulation
- **First Serve**: Checks serve percentage, calculates win probability using dominance ratio weighting
- **Second Serve**: Models double fault probability and second serve win rates
- **Break Points**: Uses dedicated break point save/conversion statistics for high-pressure situations
- **Dominance Weighting**: Combines server and returner strengths using player dominance ratios

### Match Structure
- Standard tennis scoring (0, 15, 30, 40, deuce, advantage)
- Set rules (first to 6 games, win by 2)
- Tiebreaks at 6-6 with correct serving rotation
- Configurable match formats (best of 3 or 5 sets)

## Project Structure

```
tennis-simulator/
├── app.py                 # Flask + SocketIO server
├── data_loader.py         # CSV data processing
├── simulation_engine.py   # Monte Carlo simulation
├── requirements.txt       # Dependencies
├── templates/
│   └── index.html        # Web interface
├── static/
│   ├── style.css         # Styling
│   └── script.js         # Frontend logic
└── data/                 # Player statistics CSVs
```

## Deployment

### Local Development
```bash
python app.py
```

### Production (Gunicorn + Eventlet)
```bash
pip install gunicorn
gunicorn --worker-class eventlet -w 1 app:app -b 0.0.0.0:5002
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5002
CMD ["python", "app.py"]
```

## Attribution

Player statistics provided by [Tennis Abstract](https://tennisabstract.com)

## Tech Stack

- **Backend**: Flask, Flask-SocketIO, Pandas, NumPy
- **Frontend**: Vanilla JavaScript, Chart.js
- **Real-Time**: WebSocket via Socket.IO
