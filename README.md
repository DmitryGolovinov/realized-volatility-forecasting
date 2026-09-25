# Realized Volatility Forecasting: Cross-Asset Generalization and Forecast Combination

Which gains in next-day realized-variance forecasting survive a common information set, honest
walk-forward evaluation and a different asset class, and where do they come from? One harness
gives HAR, log-HAR, HAR-X, a random forest, the NN3 network of Christensen, Siggaard & Veliyev,
and an LSTM the same rows, refits and inner validation. It adds pooled-versus-asset-specific fits
and combinations whose weights use only earlier out-of-sample forecasts. The protocol was frozen
on five US stocks and then applied, without retuning, to eight crypto assets built from public
5-minute data. That public crypto study is the main evidence; the stock study is an archival
reproduction on supplied, undated files.

## Background

This project started in the ML in Finance course at the New Economic School (NES). I later extended it with one walk-forward harness that gives every model the same rows and refits, pooled and combined forecasts built only from earlier out-of-sample forecasts, an inferred calendar for the undated stock panel, a frozen-protocol transfer to eight crypto assets built from public Binance data, and predeclared paired contrasts with a joint date bootstrap. Development used AI coding assistance; the reviews mentioned in this repository's documents were AI-assisted, not independent human audits.

**Result.** In the crypto final (2024-01 to 2026-08, reserved and evaluated once with the frozen
procedure), most of the gain over the level HAR model comes from the log target alone. log-HAR's
mean QLIKE is lower by 0.1244 (joint bootstrap interval -0.1887 to -0.0471); its point estimate is
lower for 7 of the 8 assets. Averaging the five models has a lower loss than the members' average
(interval excludes zero; point estimate lower for each of the 8 assets): it protects against
members that fail on particular assets and days. It is not
distinguishable from the strongest single alternatives, though: prior-best selection, log-HAR, or
the pooled NN3, whose point estimate is better (mean QLIKE ratio to HAR 0.737 against 0.752).
Extra features, nonlinear learners and pooling are not resolved in crypto. In the archival stock
final (not in stock development) the richer stock features (including implied volatility) lower
the loss with an interval excluding zero; there, the pooled NN3 beats equal weighting, and
dropping the weak level-HAR member improves the average.

| Paired QLIKE difference, all assets and dates (95% joint bootstrap) | Crypto final 2024-01..2026-08 | Stocks final (archival) |
|---|---:|---:|
| log-HAR minus HAR (log target, same regressors) | -0.1244 [-0.1887, -0.0471] | -0.0172 [-0.0233, -0.0079] |
| HAR-X minus log-HAR (extra asset features) | +0.0240 [-0.0203, +0.1090] | -0.0265 [-0.0387, -0.0174] |
| NN3 pooled minus NN3 asset-specific | -0.0314 [-0.0943, +0.0024] | -0.0017 [-0.0055, +0.0027] |
| Equal weight minus the members' average loss | -0.0366 [-0.0721, -0.0158] | -0.0078 [-0.0091, -0.0067] |
| Equal weight minus best prior model | -0.0253 [-0.1168, +0.0262] | -0.0031 [-0.0086, +0.0004] |
| Equal weight without level HAR minus equal weight | -0.0119 [-0.0281, +0.0071] | -0.0039 [-0.0061, -0.0016] |
| Equal weight minus NN3 pooled | +0.0121 [-0.0159, +0.0326] | +0.0048 [+0.0018, +0.0072] |
| Equal weight minus log-HAR | -0.0098 [-0.0383, +0.0151] | -0.0242 [-0.0375, -0.0159] |

*Negative: the first forecast has the lower loss. QLIKE is L = x - log x - 1 with x = RV /
forecast (zero for a perfect forecast), averaged over all asset-days (973 dates x 8 crypto
assets; 851 x 5 stocks). Intervals resample blocks of 20 dates and keep every asset of a drawn
date together, because assets share volatility shocks; per-asset intervals would treat
simultaneous series as independent evidence. Full contrast tables, pooled ratios and a
Newey-West t for the cross-asset daily mean are in the result reports.*

The mean over assets of each model's QLIKE ratio to HAR, the form used in the reports:

| QLIKE relative to HAR, mean over assets | Stocks, development 2006-01..2014-08 | Stocks, final 2014-08..2017-12 | Crypto, development 2022-06..2023-12 | Crypto, final 2024-01..2026-08 |
|---|---:|---:|---:|---:|
| NN3 pooled across assets | 0.894 | 0.783 | 0.705 | 0.737 |
| NN3 asset-specific | 1.219 | 0.792 | 0.719 | 0.796 |
| HAR-X | 1.055 | 0.795 | 0.705 | 0.827 |
| Random forest | 0.992 | 0.835 | 0.731 | 0.761 |
| LSTM | 1.029 | 0.791 | 0.712 | 0.746 |
| log-HAR | 0.943 | 0.921 | 0.721 | 0.783 |
| Equal-weight combination | 0.898 | 0.806 | 0.721 | 0.752 |
| Median of the five models | 0.924 | 0.792 | 0.703 | 0.735 |
| Trimmed mean (drop highest and lowest) | 0.914 | 0.795 | 0.704 | 0.732 |
| QLIKE-weighted combination | 0.916 | 0.805 | 0.707 | 0.752 |
| Best prior individual model | 0.942 | 0.820 | 0.719 | 0.810 |

![Stability across assets and blocks, crypto final](reports/figures/blocks_crypto_final.png)

**Missing 5-minute bars (Generation 2.1).** 21 days per crypto asset have missing bars, 17 of
them exchange-wide outages below 95% coverage; all fall before 2024, and one lies in the
development evaluation window. Realized variance over a gap is still the sum over the observed, coarser partition. Realized
quarticity, however, had been scaled as if the grid were complete, which overstates it on gap
days. A predeclared span-aware estimator, sum r^4 / (3 sum delta^2), fixes this. Rerunning both
crypto samples with it moved no model's mean QLIKE ratio by more than 0.0016 and changed no
contrast's sign or interval verdict (`results/g21_vs_g2.json`, `results/crypto_g21_*`). The
final rerun is a disclosed recomputation of an exposed sample, not a new test.

**Critical limitations.** Every final sample here has now been viewed. The crypto final was
reserved within this repository, but BTC and ETH trade data from 2023-2025 were analyzed for
return prediction in the separate Binance study of this portfolio, including that study's 2025
final sample (its 1-second final was evaluated minutes before this final ran; both protocols
were frozen beforehand). The samples are not independent across the portfolio. The stock final overlaps a period
whose AAPL rows were viewed in the original exercise. Crypto features are a restricted set (no
implied volatility, earnings or macro data). Lower variance-forecast loss is not evidence of
option or volatility-trading profits, and none is claimed.

**Inferred calendar (stocks).** The supplied files have a row index only; every stock date in
this repository is an inference, not an authoritative calendar. `r_d` equals min(open-to-close
return, 0). Matching its sign pattern to public daily prices with a monotone alignment places
the rows at 2001-01-29 to 2018-01-02 with two exchange days absent (95-98% sign agreement per
stock; `data/date_map.csv`, `scripts/recover_dates.py`). Four rows agree for at most two of the
five stocks, and one omission is weakly identified. The forecasts use the row index only; dates
affect labels and calendar-year tables.

Tables: [reports/results_crypto_final.md](reports/results_crypto_final.md),
[reports/results_crypto_g21_final.md](reports/results_crypto_g21_final.md),
[reports/results_crypto_dev.md](reports/results_crypto_dev.md),
[reports/results_final.md](reports/results_final.md),
[reports/results_dev.md](reports/results_dev.md); note:
[reports/research_note.md](reports/research_note.md).

```bash
make test               # offline: harness timing, smearing, QLIKE, combination history, paired losses
make demo               # synthetic HAR process, no network
make data-public        # public Binance spot 5-minute klines -> both crypto panels (~0.3 GB, checksummed)
make reproduce-public   # crypto transfer on development rows (both panels), paired losses, reports
make data-private reproduce-private   # archival stock study: needs the supplied files (not redistributed)
```

Final-sample commands and the reproduction record are in [docs/methodology.md](docs/methodology.md).

## Read the code

1. One walk-forward harness for every model (row clock, refits, inner validation, smearing,
   past-only per-asset scaling for pooled fits): `src/rvf/harness.py`, `src/rvf/models.py`.
2. Combinations from prior out-of-sample history, QLIKE curvature check, robust combinations:
   `src/rvf/combine.py`.
3. Paired losses with a joint date bootstrap and the predeclared contrasts: `src/rvf/paired.py`.
4. Crypto panel with span-aware quarticity: `src/rvf/crypto.py` (`daily_features`).
5. Timing and invariance tests: `tests/test_rvf.py`, `tests/test_g21.py`.

## What is reproduced, changed, and new

- **Reproduced (partially):** the HAR / HAR-X / RF / NN horse race of Christensen, Siggaard &
  Veliyev with their NN3 (16-8-4, leaky ReLU), and the LSTM that the original exercise added.
- **Corrected:** genuine expanding-window refits; a common information set and identical forecast
  rows; log forecasts mapped to variance with a training-only, robust smearing factor;
  quarticity on days with missing bars.
- **Added relative to the original exercise (not claimed as new to the literature):** pooled versus asset-specific models; forecast combinations with a curvature check;
  estimation-free robust combinations; a frozen-protocol transfer to a new asset class; paired
  contrasts that separate target scale, features, pooling and averaging.

## References

- F. Corsi. A Simple Approximate Long-Memory Model of Realized Volatility. *Journal of Financial
  Econometrics* 7(2), 174-196, 2009. https://doi.org/10.1093/jjfinec/nbp001 (HAR benchmark).
- K. Christensen, M. Siggaard, B. Veliyev. A Machine Learning Approach to Volatility
  Forecasting. *Journal of Financial Econometrics* 21(5), 1680-1727, 2023.
  https://doi.org/10.1093/jjfinec/nbac020; correction https://doi.org/10.1093/jjfinec/nbac032
  (HAR-X, random forest and NN3 comparison partially replicated).
- F. Corsi, R. Reno. Discrete-Time Volatility Forecasting With Persistent Leverage Effect and the
  Link With Continuous-Time Volatility Modeling. *Journal of Business & Economic Statistics*
  30(3), 368-380, 2012. https://doi.org/10.1080/07350015.2012.663261 (leverage features).
- A. J. Patton. Volatility forecast comparison using imperfect volatility proxies. *Journal of
  Econometrics* 160(1), 246-256, 2011. https://doi.org/10.1016/j.jeconom.2010.03.034 (QLIKE loss).
- O. E. Barndorff-Nielsen, N. Shephard. Econometric analysis of realized volatility and its use
  in estimating stochastic volatility models. *Journal of the Royal Statistical Society B* 64(2),
  253-280, 2002. https://doi.org/10.1111/1467-9868.00336 (realized quarticity).

The LSTM and the combination and transfer experiments are additions. Full list:
[docs/references.md](docs/references.md). Data card: [docs/data.md](docs/data.md).
