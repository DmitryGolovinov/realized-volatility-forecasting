# Realized Volatility Forecasting: HAR and Machine Learning

I compared next-day realized-variance forecasts from HAR, log-HAR, HAR-X, random forests,
neural networks and an LSTM. I built a shared walk-forward evaluation with common forecast
dates and refit schedules, then tested forecast combinations and transfer from five US stocks
to eight crypto assets. This extends my ML in Finance course project at the New Economic School.

## Results

The main evaluation covers 973 days across eight crypto assets, from 2024-01 to 2026-08.
QLIKE measures variance-forecast error; lower is better.

| Comparison | Mean QLIKE difference | 95% joint bootstrap interval |
|---|---:|---:|
| log-HAR minus level HAR | -0.1244 | [-0.1887, -0.0471] |
| HAR-X minus log-HAR | +0.0240 | [-0.0203, +0.1090] |
| Equal-weight forecast minus best prior model | -0.0253 | [-0.1168, +0.0262] |

- **The log-HAR specification improved on level HAR.** It had lower loss for seven of eight
  assets; TRX contributed about half of the average gain. Both the target and regressors are
  transformed, so this comparison does not isolate the effect of logging the target.
- **Extra features and model averaging gave mixed results.** Neither HAR-X's difference from
  log-HAR nor equal weighting's difference from the best prior model is statistically resolved
  in this sample. Equal weighting did beat its members' average loss, a different comparison.
- **The stock and crypto rankings differ.** I use the transfer to assess how well conclusions
  carry across datasets, rather than selecting one universal winning model.

![Forecast loss relative to HAR across crypto assets and time blocks](reports/figures/blocks_crypto_final.png)

## Data

- **Crypto:** public Binance five-minute spot prices for BTC, ETH, BNB, XRP, ADA, LTC, TRX and
  XLM, checksum-verified and aggregated to daily realized variance and related features.
- **Stocks:** five course-provided datasets, not redistributed. Their calendar is inferred
  from return signs and is approximate; some feature definitions are undocumented.

The table and figure show the original run. A later correction to quarticity on missing-bar
days preserves the paired contrasts' signs and interval conclusions
([correction results](reports/results_crypto_g21_final.md)). Some stock rows and BTC/ETH dates
overlap earlier work; these are historical forecast comparisons, not evidence of trading profits.

## Method and code

- `src/rvf/harness.py`, `src/rvf/models.py`: expanding-window fits, common forecast rows,
  hyperparameter validation, log-to-variance conversion and past-only feature scaling.
- `src/rvf/combine.py`: equal weight, median, trimmed mean and weights estimated from earlier
  out-of-sample forecasts.
- `src/rvf/paired.py`: paired forecast-loss comparisons, resampling dates jointly across assets
  to preserve common volatility shocks.

I treat the pooled log-HAR/RF comparisons as exploratory: their log-to-variance correction uses
post-refit residuals, unlike the asset-specific versions. The implementation difference and
sample scope are documented in [methodology](docs/methodology.md) and
[research notes](reports/research_note.md).

## Run locally

Use Python `3.11` or `3.12`, from the repository directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make check     # offline tests, lint and saved-result claim checks
make demo      # synthetic example
```

Data preparation and study commands: [docs/data.md](docs/data.md) and
[docs/methodology.md](docs/methodology.md). Full tables:
[crypto](reports/results_crypto_final.md), [stocks](reports/results_final.md).

## References

- Corsi (2009), *A Simple Approximate Long-Memory Model of Realized Volatility*.
- Christensen, Siggaard & Veliyev (2023), *A Machine Learning Approach to Volatility Forecasting*.
- Patton (2011), *Volatility forecast comparison using imperfect volatility proxies*.
