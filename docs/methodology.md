# Methodology

## Harness

One walk-forward harness for every model: refit origins r = 1000, 1252, ... (every 252 rows);
training rows 21..r-1 (row 21 is the LSTM's first complete 22-row sequence, used by all models
so the information set and dates are common); inner split = first 80% / last 20% of the window
for early stopping, hyperparameters and retransformation; forecasts for rows r..r+251. A target
at row t is known at the end of row t+1, so the window [21, r) contains only matured labels.

## Models (daily horizon, variance space)

- **HAR** (Corsi 2009) in levels: RV_{t+1} = b0 + bd RV_d + bw RV_w + bm RV_m by OLS.
- **logHAR / HAR-X:** OLS on log RV with log HAR terms (plus the ten asset-level features for
  HAR-X).
- **RF:** 300 trees, max_features 1/3, grid min_leaf {5, 20} x max_depth {8, none} chosen on the
  inner validation, then refitted on the whole window.
- **NN:** NN3 of Christensen, Siggaard & Veliyev (hidden layers 16-8-4, leaky ReLU), Adam, L1 weight
  penalty, early stopping on the inner validation, ensemble of 3 seeds, trained on log RV (the
  paper's main specification models RV levels and inspects log volatility separately). The
  original notebook used 8-4-2.
- **LSTM:** one layer, 16 units, 22-row sequences, dropout 0.1, ensemble of 2 seeds; this is the
  original exercise's addition to the paper's comparison.
- **Pooled** logHAR, RF, NN: one fit on all assets of the panel (five stocks or eight crypto
  assets) with each asset's features and log target standardized by that asset's own
  inner-train moments; identical rows to the asset-specific fits.

## From log forecasts to variance levels

exp(E[log RV | x]) estimates a conditional median, not the conditional mean, so a plain exp
is biased low. Every log model multiplies by a Duan smearing factor s = mean(exp(e)) computed
on inner-validation log residuals, winsorized at their 1%/99% quantiles (amendment rvf-1: an
unwinsorized factor reached 3.6e8 for PG HAR-X, recorded in an unpublished superseded run log). This is an approximation, not an exact
conditional-mean correction: Duan's estimator assumes residuals independent of the regressors,
and winsorizing trades a small downward bias for robustness to extreme residuals. All level forecasts are floored at the
training-window minimum RV, fixed before the outcome is known.

## Combination

Equal-weight average of the five individual models (HAR, HAR-X, RF, NN, LSTM); a data-driven
combination whose weights minimize mean QLIKE over the simplex grid with step 0.1 (1,001 points)
on ALL PRIOR out-of-sample rows (at least 252); and the best prior individual model. QLIKE
L = RV/f - log(RV/f) - 1 has d2L/df2 = 2RV/f^3 - 1/f^2 < 0 when f > 2RV, so the combined
objective is not convex in the weights in general; the grid is a global search over a finite set,
and the smallest Hessian eigenvalue in the simplex tangent space at the chosen point is reported.

## Evaluation

QLIKE, MSE and MAE in levels; ratios to HAR, i.e. mean(L_model) / mean(L_HAR) over an asset's
forecast rows, reported per asset and as the unweighted mean over assets. QLIKE is used in the
normalized form above (zero for a perfect forecast); ratios depend on that normalization and on
equal weighting of assets, while paired differences mean(L_a - L_b) do not depend on the
normalization (the QLIKE-weighted versus equal-weight order in the crypto final does, see the
research note). Newey-West (5 lags) t-statistics of the paired
QLIKE difference against HAR; moving-block bootstrap (20 rows) intervals for the QLIKE ratio;
relative bias and Mincer-Zarnowitz regressions RV = a + b f; per-block (252 rows) ratios by
asset. Top-decile realized-RV slices are descriptive ex-post subsets, not regime forecasts.
No option or volatility-trading claim is made.

**Paired losses across the cross-section (Generation 2.1).** Per-asset intervals treat each
asset separately, but all assets are forecast on the same dates and share volatility shocks.
`scripts/paired_losses.py` rebuilds each run's evaluation rows from its saved forecasts (checked
against `comparison.csv` to 1e-10) and reports sixteen paired contrasts (`src/rvf/paired.py`:
target scale, features, nonlinearity, pooling, averaging, protection, context) as raw panel-mean
QLIKE differences, pooled ratios and means of per-asset ratios. Intervals: moving-block bootstrap
over DATES (block 20, 2,000 draws, seed 0) with every asset of a drawn date kept together; a
Newey-West t (5 lags) of the cross-asset mean daily difference is reported alongside. The
"members' mean loss" is the per-cell average of the five members' losses (not a forecast).

## Missing bars and quarticity (Generation 2.1)

The crypto panel books the price change across missing 5-minute bars on the next available bar,
so a gap return spans k > 1 intervals. For realized variance this is a coarser partition of the
same day and needs no change. For realized quarticity, E r^4 = 3 sigma^4 delta^2 for a Gaussian
return spanning delta of a day when volatility is constant over the day (no drift, no jumps), so
the complete-grid estimator (288/3) sum r^4 has expectation sigma^4 (sum k^2) / 288: it is
biased by the factor (sum k^2) / 288 (up to 51 on 2019-05-15). The factor is at least 1 because
sum k = 288 on every day, which holds because no gap straddles midnight. The correction, decided
and recorded on 2026-09-24 before any corrected forecast was computed, uses
sum r_i^4 / (3 sum delta_i^2), identical on complete days (bit-for-bit) and unbiased for sigma^4
under the same assumptions (`tests/test_g21.py`). If volatility varies within the day, its
expectation is sum sigma_i^4 delta_i^2 / sum delta_i^2 (sigma_i the root-mean-square volatility
over return i's span): on a gap day a gap-weighted average of sigma^4 that is not integrated
quarticity (sum sigma_i^4 delta_i); on a complete day the weights are equal and it is. The Generation-2 panel
(`data/crypto/`) and the corrected one (`data/crypto_g21/`) are built from the same verified
archives; `results/crypto_g21_<mode>/` reruns the frozen protocol on the corrected panel, and
`results/g21_vs_g2.json` compares the two. Sensitivity: the same forecasts rescored without
target days below 95% bar coverage (one development date, no final date).

## Timing and estimation audit (Generation 2.1)

| Item | Implementation | Test |
|---|---|---|
| Common information set | every model forecasts row t+1 from features of rows <= t; the LSTM's 22-row sequences end at t | `test_sequences_use_only_past_rows` |
| Row maturity | training window [21, r) at origin r: the label of row r-1 (rv of row r) is known when the forecast for row r+1 is made | `test_training_rows_end_before_each_origin_and_future_invariance` |
| Pooled per-asset scaling | each asset's moments from its own inner-train rows only | `test_pooled_scaling_and_forecasts_use_only_past_rows` |
| Smearing | inner-validation residuals of the training window, winsorized | `test_smearing_*` |
| Positivity floor | minimum training RV; binds for 6 of 7,784 crypto-final cells (HAR-X 4, NN 2), none in the stock final | forecast files (`*__floored`; parquet, not published) |
| Refit policy | expanding window, every 252 rows, identical origins for all models | harness logs (`fitlog_*.json`) |
| Combination history | weights and prior-best choice from out-of-sample rows < r only | `test_simplex_grid_and_combination_uses_history_only` |
| Reserved rows | dropped before any check in development runs | `test_guard_removes_reserved_rows_and_boundary_target`, loader |
| Missing bars | span-aware quarticity; coverage recorded per day | `test_span_quarticity_*` |


## Final evaluation (reproduction)

The reserved final samples were evaluated exactly once, on 2026-09-24, with the frozen code
and protocols recorded in each result manifest (`results/*final*/manifest*.json`). The commands
(from the repository root, after `make data-public` for crypto or `make data-private` for the
supplied stock files, and the development runs) were:

```bash
python scripts/run_study.py --mode final --i-understand-this-is-the-final-evaluation
python scripts/run_crypto.py --mode final --i-understand-this-is-the-final-evaluation
python scripts/make_report.py final
python scripts/make_report.py crypto_final
```

Generation 2.1 (disclosed recomputation of the exposed crypto final on the corrected panel, and
paired losses from saved forecasts):

```bash
python scripts/run_crypto.py --mode final --panel crypto_g21 --i-understand-this-is-the-final-evaluation
python scripts/paired_losses.py dev final crypto_dev crypto_final crypto_g21_dev crypto_g21_final
python scripts/compare_g21.py
python scripts/make_report.py crypto_g21_final
```

Re-running them reproduces the published final artifacts; it is not a new untouched test.
Comments in configuration files written before the release call the final evaluation
"Stage 3" (the project's internal stage names); they are left unchanged because the runs record
those files' hashes. Historical manifests keep the source tree that produced them; `docs/release_lineage.json`
records why each still stands under the current code.
