# Future work

These ideas are intentionally not part of the current correctness and automation
pass.

## Modeling

- Adjust serve and return estimates for opponent strength and tour level.
- Use recency weighting instead of a hard rolling-window cutoff.
- Add hierarchical shrinkage so small surface samples regress toward a player's
  all-surface rate and then toward a tour baseline.
- Draw point probabilities from posterior distributions so forecast intervals
  include parameter uncertainty, not only Monte Carlo sampling error.
- Model tournament conditions such as court speed, altitude, indoor/outdoor play,
  fatigue, and injury information when reliable structured inputs exist.
- Support event-specific deciding-set and tiebreak rules.

## Evaluation

- Build walk-forward backtests with frozen pre-match data.
- Report log loss, Brier score, calibration curves, and accuracy by surface,
  tour level, favorite strength, and sample size.
- Backtest against timestamped pre-match prediction-market prices; retain naive
  ranking and surface-Elo as secondary baselines.
- Add provider-specific historical price capture so market comparisons are
  reproducible instead of relying only on live snapshots.
- Add data-quality monitors for incomplete match statistics, player aliases,
  duplicated matches, source lateness, and abrupt metric shifts.

## Engineering

- Replace the four legacy-named aggregate CSVs with one versioned, neutral schema.
- Add end-to-end Flask route tests in an environment that installs runtime
  dependencies.
- Vendor or integrity-pin browser assets instead of loading unversioned CDN URLs.
- Replace the maintained tournament-name surface map with a licensed structured
  schedule feed if the site needs comprehensive matches beyond prediction markets.
