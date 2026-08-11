# Tennis Match Simulator

A point-by-point Monte Carlo simulator for ATP singles matches. It combines a
server's rolling serve statistics with the opponent's return statistics, then
plays points, games, sets, and matches using standard scoring.

Live site: [twood-tennis-simulator.fly.dev](https://twood-tennis-simulator.fly.dev/)

## What it provides

- best-of-three and best-of-five simulations on hard, clay, and grass
- reproducible runs via a returned random seed
- 95% Monte Carlo confidence intervals
- set-score distributions and expected-versus-observed diagnostics
- a seven-day dashboard of upcoming market-listed ATP matches
- live, read-only Kalshi and Polymarket match-winner comparisons
- progressive, cached dashboard simulations with data-quality warnings
- rolling 52-week data built from main-tour and Challenger matches
- a daily, reviewed data-refresh pull request

This is an exploratory model, not betting advice. The confidence interval only
measures Monte Carlo sampling error; it does not capture model or data error.
Prediction-market prices can be delayed, illiquid, or unavailable and are not
guarantees of match outcomes.

## Run locally

```bash
git clone https://github.com/twood22/tennis-simulator.git
cd tennis-simulator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5002>. The development server binds to localhost only.

Run the dependency-free model and loader tests with:

```bash
python -m unittest discover -s tests -v
```

## Refresh data

```bash
python scripts/refresh_data.py
```

The refresh downloads the prior and current season's ATP and Challenger files,
plus ongoing tournaments, from the MIT-licensed
[TennisMyLife match database](https://stats.tennismylife.org/tennis-match-database).
It deduplicates matches, keeps a rolling 365-day window, aggregates raw counts,
validates the staged output through the production loader, and only then replaces
the files in `data/`. Provenance, upstream timestamps, and SHA-256 hashes are
written to `data/metadata.json`.

The GitHub Actions workflow runs daily and can also be dispatched manually. It
opens or updates a pull request instead of modifying the default branch directly.
Repository settings must allow GitHub Actions to create pull requests. Scheduled
workflows may be delayed during high load and can be disabled after prolonged
repository inactivity, so the manual trigger is retained.

## Model outline

For each point, the simulator combines:

- server first-serve frequency and first/second-serve points won;
- returner's first/second-serve return points won;
- double-fault rate conditional on reaching a second serve; and
- each player's aggregate dominance ratio.

Break points use the same serve/return point model as ordinary points. Break-point
outcomes are tracked for diagnostics, but noisy raw break-point percentages are
not used as a separate point probability. The opening server is randomized and
service order is carried correctly through tiebreaks and between sets.

Surface samples require five statistically complete matches. If a player lacks a
surface sample, the loader falls back to all-surface data and reports that choice.
The current data combines main-tour and Challenger results without adjusting for
opponent strength, which is especially important for emerging players.

## API

- `GET /api/players`
- `GET /api/upcoming?days=7`
- `GET /api/upcoming/<match-id>/simulation`
- `GET /api/market-odds?player1=Learner%20Tien&player2=Daniel%20Merida`
- `POST /api/simulate`

Example request:

```json
{
  "player1": "Learner Tien",
  "player2": "Daniel Merida",
  "format": "best3",
  "num_simulations": 10000,
  "surfaces": ["hard"],
  "seed": 20260810
}
```

The seed and surfaces are optional. Simulation counts must be between 1 and
10,000. Simulation responses also include a best-effort `market_comparison`;
provider failures never cause the simulation itself to fail.

## Prediction-market comparison

The app queries public, unauthenticated market-data endpoints only. It does not
place trades, connect a wallet, or use account credentials.

- Kalshi ATP match markets are grouped by event. The midpoint of each player's
  YES bid and ask is normalized across the two players.
- Polymarket active moneyline markets use the published outcome prices, also
  normalized defensively across the two players.
- Player names must match both sides of the market. Extra provider surnames such
  as `Daniel Merida Aguilar` are supported.
- When both providers have an exact market, the displayed consensus is their
  unweighted mean. Each surface simulation is shown beside that market baseline
  as a percentage-point difference.

The providers are fetched concurrently with short timeouts. A missing market or
provider outage is displayed explicitly rather than being treated as a zero or
silently substituted. See the official [Kalshi market-data
guide](https://docs.kalshi.com/getting_started/quick_start_market_data) and
[Polymarket market-data overview](https://docs.polymarket.com/market-data/overview)
for the upstream API definitions.

## Upcoming-match dashboard

The landing page discovers ATP match-winner markets for the next seven days with
one bounded request to each provider. It resolves provider aliases to simulator
player names, merges the same match across providers, and loads simulations
progressively so the live schedule appears immediately. Upcoming-market discovery
is cached for five minutes; deterministic 1,000-run match simulations are cached
for the lifetime of the server process.

Tournament-name mappings select the court surface for known events. Matches with
an unknown surface or a player outside the data snapshot still display market
prices, but the app does not invent a simulation. A caution is displayed when a
surface sample is thin or the opponents' historical schedule strength differs
substantially.

## Deploy to Fly.io

The production image runs Flask behind Gunicorn as an unprivileged user. The
included `fly.toml` provisions exactly one `shared-cpu-1x` Machine with 512 MB of
RAM in Los Angeles, HTTPS, health checks, and no database or persistent volume.

```bash
fly deploy --remote-only --ha=false
```

The Machine is kept running for a responsive dashboard while still bounding the
compute bill to one small Machine. Pushes to `main` can deploy through
`.github/workflows/deploy-fly.yml` after the repository has a scoped
`FLY_API_TOKEN` Actions secret.

## Layout

```text
api/index.py              canonical Flask application
app.py                    local compatibility entry point
data_loader.py            validated CSV loader and fallback rules
simulation_engine.py      scoring and Monte Carlo engine
simulation_service.py     request validation and API orchestration
market_odds.py            public Kalshi/Polymarket lookup and comparison
upcoming_service.py       schedule discovery, surface mapping, caching, warnings
scripts/refresh_data.py   rolling data refresh pipeline
tests/                    dependency-free regression tests
```

Future modeling work is deliberately separated in [FUTURE_TODOS.md](FUTURE_TODOS.md).

## Data attribution

Generated match aggregates come from the
[TennisMyLife match database](https://stats.tennismylife.org/tennis-match-database),
published under the MIT License. Live prediction-market prices are the primary
external comparison in the app; ranking or Elo can still be useful as secondary
backtest baselines, but they are not ingested into the simulator.
