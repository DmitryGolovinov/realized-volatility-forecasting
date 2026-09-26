# Research note: where variance-forecast gains come from, and whether combining holds up

*Numbers: [results_crypto_final.md](results_crypto_final.md),
[results_crypto_g21_final.md](results_crypto_g21_final.md), [results_final.md](results_final.md),
[results_crypto_dev.md](results_crypto_dev.md), [results_dev.md](results_dev.md) and
`results/*/paired_losses.csv`. Final samples were reserved from all design decisions and
evaluated once with the frozen procedure (as declared, the 252-row refits and the combination
weights inside a final sample use its earlier rows); they have now been viewed. The crypto
final overlaps BTC and ETH trade data from 2023-2025 that the separate Binance study of this
portfolio analyzed for return prediction, including that study's 2025 final sample (its
1-second final was evaluated minutes before this final); the samples are not independent across
the portfolio.*

## Design

Target: next-day realized variance, evaluated with QLIKE L = x - log x - 1, x = RV / forecast
(robust to noise in the proxy; Patton 2011), and level losses. Every model (HAR, log-HAR, HAR-X,
random forest, NN3 16-8-4, LSTM) is refitted on the same 252-row clock with the same inner
validation and forecasts the same rows. Log forecasts are mapped to variance with a
training-only robust smearing factor. Combinations use only prior out-of-sample forecasts;
because QLIKE is not convex in the forecast, the weighted combination is searched on a simplex
grid with a curvature check. The median and trimmed mean were added before any final run to test
whether equal weighting works by diversification or by averaging away one unstable member.

Samples: five US stocks (supplied files; calendar inferred from the data, not authoritative:
development 2006-01..2014-08, final 2014-08..2017-12) and eight crypto assets from public Binance
5-minute bars under the same frozen protocol (development 2022-06..2023-12, final
2024-01..2026-08). The crypto study is the stronger evidence: its data are public and dated.

## Where the gains come from: paired contrasts

Raw QLIKE differences over all asset-days (negative: the first forecast has the lower loss).
Intervals: 95% moving-block bootstrap over dates (blocks of 20, 2,000 draws) with every asset of
a drawn date kept together, because the assets share volatility shocks. `*`: the interval
excludes zero. The sixteen contrasts were fixed before they were computed (`src/rvf/paired.py`);
no learner was added.

| Contrast (a - b) | Stocks dev | Stocks final | Crypto dev | Crypto final |
|---|---:|---:|---:|---:|
| log-HAR - HAR | -0.0098 [-0.0131, -0.0064]* | -0.0172 [-0.0233, -0.0079]* | -0.1546 [-0.2372, -0.0739]* | -0.1244 [-0.1887, -0.0471]* |
| HAR-X - log-HAR | +0.0151 [-0.0122, +0.0637] | -0.0265 [-0.0387, -0.0174]* | -0.0074 [-0.0161, +0.0009] | +0.0240 [-0.0203, +0.1090] |
| RF - HAR-X | -0.0076 [-0.0475, +0.0137] | +0.0084 [+0.0011, +0.0148]* | +0.0148 [+0.0004, +0.0307]* | -0.0316 [-0.1300, +0.0201] |
| NN3 - HAR-X | +0.0257 [+0.0047, +0.0608]* | -0.0008 [-0.0045, +0.0018] | +0.0073 [-0.0105, +0.0225] | -0.0145 [-0.0397, +0.0013] |
| LSTM - HAR-X | -0.0021 [-0.0295, +0.0129] | -0.0009 [-0.0059, +0.0025] | +0.0049 [-0.0204, +0.0258] | -0.0403 [-0.1323, +0.0085] |
| log-HAR pooled - specific | +0.0010 [+0.0003, +0.0019]* | -0.0002 [-0.0013, +0.0007] | -0.0024 [-0.0061, +0.0006] | -0.0013 [-0.0051, +0.0042] |
| RF pooled - specific | -0.0126 [-0.0196, -0.0063]* | -0.0012 [-0.0060, +0.0054] | -0.0115 [-0.0345, +0.0064] | +0.0072 [-0.0163, +0.0509] |
| NN3 pooled - specific | -0.0493 [-0.1220, -0.0076]* | -0.0017 [-0.0055, +0.0027] | -0.0067 [-0.0173, +0.0035] | -0.0314 [-0.0943, +0.0024] |
| EW - members' mean loss | -0.0247 [-0.0535, -0.0074]* | -0.0078 [-0.0091, -0.0067]* | -0.0268 [-0.0428, -0.0144]* | -0.0366 [-0.0721, -0.0158]* |
| EW - best prior | -0.0060 [-0.0156, +0.0004] | -0.0031 [-0.0086, +0.0004] | +0.0035 [-0.0281, +0.0329] | -0.0253 [-0.1168, +0.0262] |
| EW without HAR - EW | +0.0047 [-0.0004, +0.0131] | -0.0039 [-0.0061, -0.0016]* | -0.0120 [-0.0356, +0.0131] | -0.0119 [-0.0281, +0.0071] |
| Median - EW | +0.0039 [-0.0007, +0.0111] | -0.0031 [-0.0051, -0.0011]* | -0.0115 [-0.0311, +0.0084] | -0.0118 [-0.0264, +0.0063] |
| Trimmed - EW | +0.0023 [-0.0008, +0.0075] | -0.0023 [-0.0039, -0.0007]* | -0.0112 [-0.0293, +0.0075] | -0.0137 [-0.0257, -0.0003]* |
| EW - NN3 pooled | +0.0010 [-0.0085, +0.0066] | +0.0048 [+0.0018, +0.0072]* | +0.0104 [-0.0179, +0.0383] | +0.0121 [-0.0159, +0.0326] |
| EW - log-HAR | -0.0074 [-0.0123, -0.0020]* | -0.0242 [-0.0375, -0.0159]* | +0.0036 [-0.0371, +0.0411] | -0.0098 [-0.0383, +0.0151] |

## Findings

1. **The log target is the one gain that holds everywhere.** log-HAR beats level HAR in all four
   samples, with intervals that exclude zero. In the crypto final it accounts for 0.124 of the
   0.134 by which equal weighting improves on HAR's mean QLIKE (0.508).
2. **Averaging reliably beats the average member, not the best alternatives.** Equal weighting
   has a lower loss than its members' average loss in all four samples. Against selecting the
   best model on prior out-of-sample data, no sample resolves the difference (the point estimate
   favors equal weighting in three of four). The pooled NN3 has the lower point estimate than
   equal weighting in all four samples, and the difference is resolved in the stock final.
3. **Features and nonlinear learners are not reliable gains.** The extra features lower the
   loss with an interval excluding zero only in the stock final (where they include implied volatility and earnings dates). Against
   log-OLS on the same features, the random forest is worse with intervals excluding zero in the
   stock final and crypto development, the NN3 is worse in stock development, and the rest is
   unresolved. Model rankings do not travel between periods or asset classes.
4. **Pooling helps some models in some samples.** Pooling the random forest and the NN3 across
   assets resolves a gain in stock development only, where pooled log-HAR is marginally but
   resolvably worse; elsewhere the intervals include zero.
5. **Part of the combination gain is robustness to a weak member.** Dropping level HAR, the
   median and the trimmed mean all improve on equal weighting in the stock final (resolved) and
   the trimmed mean marginally in the crypto final. In stock development they are worse
   (unresolved), so the member set, not only averaging, matters.
6. **The QLIKE-optimized grid weights had a lower mean ratio than equal weights only in crypto
   development** (0.707 against 0.721; a point estimate, no interval was computed for this
   contrast). In the stock final they were
   marginally lower (0.805 against 0.806). In the crypto final the two are within 0.001 of each
   other in mean ratio, while the grid weights have the lower raw panel loss (0.3707 against
   0.3739), so the order depends on how losses are aggregated over assets. In stock development
   equal weights were lower (0.898 against 0.916). This is consistent with the
   forecast-combination puzzle, where estimated weights add noise that equal weights avoid.

## Generation 2.1: missing bars

Twenty-one days per crypto asset have missing 5-minute bars (17 exchange-wide outages below 95%
coverage, all before 2024). Realized variance over a gap remains the sum over the observed
partition. Realized quarticity, scaled as if the grid were complete, was overstated on those days
(by a median factor of 3.8). A predeclared span-aware estimator, sum r^4 / (3 sum delta^2), is
unbiased for sigma^4 when volatility is constant over the day, with Gaussian increments and no
drift or jumps (`tests/test_g21.py`); if volatility varies within the day it estimates a
gap-weighted average of sigma^4, not integrated quarticity. Rerunning both crypto samples
with it changed forecasts of the quarticity-using models on individual days. It moved no mean
QLIKE ratio by more than 0.0016 and changed no contrast's sign or interval verdict
(`results/g21_vs_g2.json`). The final rerun is a disclosed recomputation of an exposed sample.

## Limitations

The stock sample is five large US stocks from one supplied file with partly undocumented feature
units (its `rq_d` is negative in most rows, so it is not a raw quarticity) and an inferred
calendar; the stock final overlaps AAPL rows seen in the original exercise. Crypto lacks implied
volatility and macro information and trades 24/7, so its weekly/monthly HAR windows are 7/30
days. Eight crypto assets share one exchange and strongly co-move: the joint bootstrap accounts
for that dependence but cannot create independent evidence. The contrasts are average-loss
comparisons and do not support any volatility-trading claim.
