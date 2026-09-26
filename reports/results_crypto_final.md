# Final results (crypto_final)

Generated from `results/crypto_final/` (config `4ed99606705e`, source tree `28b6e6ed6f1a`). Common evaluation rows 1826-2798 (2024-01-01 to 2026-08-30) for every asset and model. Crypto protocol transfer: eight Binance spot assets, 5-minute realized variance, the frozen stock protocol without retuning (no implied volatility, earnings or macro features). Target: next-day realized variance.

Status: crypto final, not used for any design decision in this repository and evaluated once with the frozen procedure on 2026-09-24; now exposed. Its BTC and ETH data overlap the separate Binance study of this portfolio.

## QLIKE relative to HAR by asset

| model         |   ADAUSDT |   BNBUSDT |   BTCUSDT |   ETHUSDT |   LTCUSDT |   TRXUSDT |   XLMUSDT |   XRPUSDT |
|:--------------|----------:|----------:|----------:|----------:|----------:|----------:|----------:|----------:|
| HAR           |     1.000 |     1.000 |     1.000 |     1.000 |     1.000 |     1.000 |     1.000 |     1.000 |
| logHAR        |     1.046 |     0.614 |     0.756 |     0.866 |     0.727 |     0.345 |     0.936 |     0.972 |
| HARX          |     1.153 |     0.794 |     0.709 |     0.818 |     0.893 |     0.323 |     1.033 |     0.891 |
| RF            |     1.020 |     0.581 |     0.709 |     0.855 |     0.699 |     0.408 |     0.949 |     0.868 |
| NN            |     1.091 |     0.629 |     0.694 |     0.791 |     0.938 |     0.326 |     1.053 |     0.846 |
| LSTM          |     1.021 |     0.575 |     0.700 |     0.808 |     0.695 |     0.346 |     0.964 |     0.857 |
| EqualWeight   |     0.980 |     0.617 |     0.707 |     0.781 |     0.739 |     0.443 |     0.893 |     0.852 |
| QLIKEComb     |     1.100 |     0.575 |     0.709 |     0.810 |     0.708 |     0.323 |     0.931 |     0.862 |
| BestPrior     |     1.125 |     0.790 |     0.707 |     0.808 |     0.904 |     0.323 |     0.964 |     0.857 |
| logHAR_pooled |     1.052 |     0.612 |     0.754 |     0.840 |     0.725 |     0.338 |     0.937 |     0.976 |
| RF_pooled     |     1.130 |     0.613 |     0.748 |     0.827 |     0.699 |     0.315 |     0.944 |     0.960 |
| NN_pooled     |     1.001 |     0.586 |     0.708 |     0.788 |     0.713 |     0.320 |     0.888 |     0.889 |
| Median        |     1.015 |     0.571 |     0.681 |     0.792 |     0.712 |     0.337 |     0.921 |     0.846 |
| Trimmed       |     1.001 |     0.569 |     0.689 |     0.794 |     0.702 |     0.338 |     0.908 |     0.852 |
| EW_wo_HAR     |     1.024 |     0.564 |     0.687 |     0.802 |     0.702 |     0.335 |     0.915 |     0.851 |
| EW_wo_HARX    |     0.977 |     0.637 |     0.717 |     0.783 |     0.755 |     0.489 |     0.901 |     0.853 |
| EW_wo_RF      |     0.982 |     0.639 |     0.720 |     0.784 |     0.759 |     0.478 |     0.892 |     0.857 |
| EW_wo_NN      |     0.962 |     0.636 |     0.720 |     0.788 |     0.742 |     0.482 |     0.895 |     0.860 |
| EW_wo_LSTM    |     0.977 |     0.638 |     0.720 |     0.787 |     0.756 |     0.476 |     0.886 |     0.858 |

## Newey-West t-statistic of the QLIKE gain over HAR (positive = better than HAR)

| model         |   ADAUSDT |   BNBUSDT |   BTCUSDT |   ETHUSDT |   LTCUSDT |   TRXUSDT |   XLMUSDT |   XRPUSDT |
|:--------------|----------:|----------:|----------:|----------:|----------:|----------:|----------:|----------:|
| HAR           |    nan    |    nan    |    nan    |    nan    |    nan    |    nan    |    nan    |    nan    |
| logHAR        |     -0.23 |      9.52 |      5.22 |      2.68 |      6.73 |     11.48 |      0.52 |      0.23 |
| HARX          |     -0.49 |      0.99 |      5.80 |      3.70 |      0.57 |     12.50 |     -0.14 |      1.23 |
| RF            |     -0.13 |      9.14 |      6.77 |      2.14 |      6.68 |      9.63 |      0.30 |      1.98 |
| NN            |     -0.33 |      5.89 |      6.45 |      3.72 |      0.29 |     13.59 |     -0.20 |      2.08 |
| LSTM          |     -0.11 |      8.25 |      7.07 |      3.47 |      7.53 |     14.51 |      0.19 |      2.02 |
| EqualWeight   |      0.14 |     11.55 |      8.97 |      6.12 |      9.78 |     18.42 |      0.98 |      2.84 |
| QLIKEComb     |     -0.42 |     10.39 |      7.85 |      3.36 |      7.68 |     12.83 |      0.47 |      3.29 |
| BestPrior     |     -0.45 |      1.01 |      5.75 |      3.47 |      0.51 |     12.50 |      0.19 |      2.02 |
| logHAR_pooled |     -0.24 |      9.96 |      5.41 |      3.48 |      6.88 |     12.77 |      0.51 |      0.19 |
| RF_pooled     |     -0.43 |      7.95 |      4.07 |      2.91 |      7.13 |     14.16 |      0.35 |      0.31 |
| NN_pooled     |     -0.01 |     10.55 |      5.58 |      4.47 |      6.67 |     13.88 |      0.93 |      1.07 |
| Median        |     -0.08 |     10.78 |      7.84 |      3.93 |      8.38 |     13.51 |      0.55 |      2.28 |
| Trimmed       |     -0.01 |     10.81 |      7.41 |      4.05 |      8.43 |     13.96 |      0.67 |      2.22 |
| EW_wo_HAR     |     -0.12 |     10.06 |      7.04 |      3.59 |      8.16 |     13.15 |      0.58 |      2.08 |
| EW_wo_HARX    |      0.16 |     11.50 |      9.62 |      6.49 |     10.06 |     19.44 |      0.90 |      3.19 |
| EW_wo_RF      |      0.12 |     11.84 |      9.19 |      6.83 |     10.20 |     19.91 |      1.13 |      2.90 |
| EW_wo_NN      |      0.31 |     11.36 |      9.43 |      6.55 |      9.45 |     19.06 |      1.04 |      2.93 |
| EW_wo_LSTM    |      0.17 |     12.45 |      9.06 |      6.55 |      9.98 |     18.90 |      1.22 |      2.94 |

## Average over assets: relative losses, bias, Mincer-Zarnowitz (RV = a + b f)

| model         |   QLIKE_rel_HAR |   MSE_rel_HAR |   MAE_rel_HAR |   bias_rel |   MZ_a |   MZ_b |
|:--------------|----------------:|--------------:|--------------:|-----------:|-------:|-------:|
| HAR           |           1.000 |         1.000 |         1.000 |      0.338 |  0.001 |  0.618 |
| logHAR        |           0.783 |         0.954 |         0.704 |     -0.083 |  0.001 |  0.639 |
| HARX          |           0.827 |         0.954 |         0.673 |     -0.073 |  0.001 |  0.746 |
| RF            |           0.761 |         0.921 |         0.670 |     -0.106 |  0.000 |  0.912 |
| NN            |           0.796 |         0.898 |         0.668 |     -0.079 |  0.001 |  0.838 |
| LSTM          |           0.746 |         0.908 |         0.670 |     -0.091 |  0.000 |  1.006 |
| EqualWeight   |           0.752 |         0.903 |         0.707 |     -0.002 |  0.000 |  0.868 |
| QLIKEComb     |           0.752 |         0.924 |         0.679 |     -0.060 |  0.000 |  0.830 |
| BestPrior     |           0.810 |         0.945 |         0.675 |     -0.077 |  0.001 |  0.757 |
| logHAR_pooled |           0.779 |         0.958 |         0.718 |     -0.050 |  0.001 |  0.627 |
| RF_pooled     |           0.780 |         0.908 |         0.644 |     -0.146 |  0.000 |  0.902 |
| NN_pooled     |           0.737 |         0.899 |         0.670 |     -0.056 |  0.000 |  0.809 |
| Median        |           0.735 |         0.896 |         0.664 |     -0.084 |  0.000 |  0.958 |
| Trimmed       |           0.732 |         0.899 |         0.667 |     -0.077 |  0.000 |  0.936 |
| EW_wo_HAR     |           0.735 |         0.901 |         0.660 |     -0.087 |  0.000 |  0.900 |
| EW_wo_HARX    |           0.764 |         0.905 |         0.722 |      0.015 |  0.000 |  0.895 |
| EW_wo_RF      |           0.764 |         0.903 |         0.721 |      0.024 |  0.000 |  0.850 |
| EW_wo_NN      |           0.761 |         0.908 |         0.721 |      0.017 |  0.000 |  0.854 |
| EW_wo_LSTM    |           0.762 |         0.908 |         0.722 |      0.020 |  0.000 |  0.813 |

## Pooled over asset-specific QLIKE (same rows; < 1 = pooled better)

| model   |   ADAUSDT |   BNBUSDT |   BTCUSDT |   ETHUSDT |   LTCUSDT |   TRXUSDT |   XLMUSDT |   XRPUSDT |
|:--------|----------:|----------:|----------:|----------:|----------:|----------:|----------:|----------:|
| NN      |     0.918 |     0.931 |     1.021 |     0.996 |     0.760 |     0.980 |     0.843 |     1.051 |
| RF      |     1.108 |     1.056 |     1.056 |     0.967 |     1.001 |     0.771 |     0.995 |     1.106 |
| logHAR  |     1.006 |     0.997 |     0.997 |     0.970 |     0.996 |     0.980 |     1.001 |     1.004 |

## Latest data-driven combination weights (grid on the simplex, prior OOS history)

|         |   HAR |   HARX |   RF |   NN |   LSTM |
|:--------|------:|-------:|-----:|-----:|-------:|
| BTCUSDT |  0.10 |   0.50 | 0.00 | 0.00 |   0.40 |
| ETHUSDT |  0.00 |   0.00 | 0.00 | 0.50 |   0.50 |
| BNBUSDT |  0.00 |   0.60 | 0.20 | 0.10 |   0.10 |
| XRPUSDT |  0.20 |   0.00 | 0.00 | 0.20 |   0.60 |
| ADAUSDT |  0.20 |   0.00 | 0.80 | 0.00 |   0.00 |
| LTCUSDT |  0.00 |   0.30 | 0.30 | 0.00 |   0.40 |
| TRXUSDT |  0.00 |   0.80 | 0.00 | 0.10 |   0.10 |
| XLMUSDT |  0.20 |   0.80 | 0.00 | 0.00 |   0.00 |

![blocks](figures/blocks_crypto_final.png)

## QLIKE relative to HAR by calendar year (mean over assets)

|   year |   HARX |    NN |   EqualWeight |   QLIKEComb |   BestPrior |   Median |   NN_pooled |
|-------:|-------:|------:|--------------:|------------:|------------:|---------:|------------:|
|   2024 |  0.759 | 0.715 |         0.728 |       0.755 |       0.755 |    0.721 |       0.726 |
|   2025 |  1.003 | 0.963 |         0.841 |       0.850 |       0.973 |    0.842 |       0.853 |
|   2026 |  0.451 | 0.466 |         0.535 |       0.486 |       0.467 |    0.464 |       0.444 |

## Raw losses with cross-asset dependence preserved

Panel means over 973 dates x 8 assets. Intervals: 95% moving-block bootstrap over DATES (block 20, 2000 draws), every asset of a drawn date kept together. Ratios are shown as the pooled ratio of mean losses and as the mean of per-asset ratios (the form used in the tables above).

| model         |   raw QLIKE | difference vs HAR          | pooled ratio vs HAR   | mean of asset ratios   |
|:--------------|------------:|:---------------------------|:----------------------|:-----------------------|
| HAR           |      0.508  | 0.0000 [0.0000, 0.0000]    | 1.000 [1.000, 1.000]  | 1.000 [1.000, 1.000]   |
| logHAR        |      0.3837 | -0.1244 [-0.1887, -0.0471] | 0.755 [0.548, 0.933]  | 0.783 [0.598, 0.900]   |
| HARX          |      0.4077 | -0.1004 [-0.2013, 0.0606]  | 0.802 [0.516, 1.087]  | 0.827 [0.562, 1.024]   |
| RF            |      0.3761 | -0.1320 [-0.1886, -0.0692] | 0.740 [0.550, 0.899]  | 0.761 [0.588, 0.864]   |
| NN            |      0.3932 | -0.1148 [-0.2039, 0.0246]  | 0.774 [0.512, 1.035]  | 0.796 [0.556, 0.968]   |
| LSTM          |      0.3673 | -0.1407 [-0.1971, -0.0710] | 0.723 [0.530, 0.897]  | 0.746 [0.572, 0.854]   |
| EqualWeight   |      0.3739 | -0.1341 [-0.1755, -0.0818] | 0.736 [0.581, 0.882]  | 0.752 [0.611, 0.842]   |
| QLIKEComb     |      0.3707 | -0.1373 [-0.1949, -0.0639] | 0.730 [0.532, 0.911]  | 0.752 [0.581, 0.860]   |
| BestPrior     |      0.3992 | -0.1089 [-0.2001, 0.0331]  | 0.786 [0.517, 1.046]  | 0.810 [0.565, 0.992]   |
| logHAR_pooled |      0.3824 | -0.1256 [-0.1900, -0.0460] | 0.753 [0.545, 0.935]  | 0.779 [0.594, 0.899]   |
| RF_pooled     |      0.3832 | -0.1248 [-0.1993, -0.0218] | 0.754 [0.516, 0.970]  | 0.780 [0.563, 0.923]   |
| NN_pooled     |      0.3618 | -0.1462 [-0.2064, -0.0698] | 0.712 [0.505, 0.904]  | 0.737 [0.547, 0.864]   |
| Median        |      0.362  | -0.1460 [-0.2016, -0.0767] | 0.713 [0.517, 0.890]  | 0.735 [0.560, 0.845]   |
| Trimmed       |      0.3602 | -0.1478 [-0.2008, -0.0829] | 0.709 [0.519, 0.881]  | 0.732 [0.562, 0.840]   |
| EW_wo_HAR     |      0.362  | -0.1460 [-0.2032, -0.0758] | 0.713 [0.513, 0.891]  | 0.735 [0.556, 0.847]   |
| EW_wo_HARX    |      0.3816 | -0.1264 [-0.1646, -0.0776] | 0.751 [0.608, 0.888]  | 0.764 [0.632, 0.849]   |
| EW_wo_RF      |      0.3809 | -0.1271 [-0.1657, -0.0771] | 0.750 [0.604, 0.889]  | 0.764 [0.631, 0.850]   |
| EW_wo_NN      |      0.3791 | -0.1290 [-0.1658, -0.0840] | 0.746 [0.605, 0.878]  | 0.761 [0.631, 0.843]   |
| EW_wo_LSTM    |      0.38   | -0.1280 [-0.1665, -0.0792] | 0.748 [0.602, 0.886]  | 0.762 [0.629, 0.849]   |

## Paired contrasts: where does the gain come from?

Negative difference: the first forecast has the lower loss. `MeanMemberLoss` is the average loss of the five equal-weight members, not a forecast. NW t: Newey-West (5 lags) t-statistic of the cross-asset mean daily difference.

| contrast               | a vs b                        | raw QLIKE a / b   | difference a - b           |   NW t | pooled ratio         |   assets a lower (of 8) |
|:-----------------------|:------------------------------|:------------------|:---------------------------|-------:|:---------------------|------------------------:|
| target_scale           | logHAR vs HAR                 | 0.3837 / 0.5080   | -0.1244 [-0.1887, -0.0471] |  -3.42 | 0.755 [0.548, 0.933] |                       7 |
| features               | HARX vs logHAR                | 0.4077 / 0.3837   | +0.0240 [-0.0203, +0.1090] |   0.6  | 1.063 [0.927, 1.196] |                       4 |
| nonlinear_RF           | RF vs HARX                    | 0.3761 / 0.4077   | -0.0316 [-0.1300, +0.0201] |  -0.69 | 0.922 [0.809, 1.082] |                       6 |
| nonlinear_NN           | NN vs HARX                    | 0.3932 / 0.4077   | -0.0145 [-0.0397, +0.0013] |  -1.14 | 0.964 [0.921, 1.005] |                       5 |
| nonlinear_LSTM         | LSTM vs HARX                  | 0.3673 / 0.4077   | -0.0403 [-0.1323, +0.0085] |  -0.97 | 0.901 [0.806, 1.039] |                       7 |
| pooling_logHAR         | logHAR_pooled vs logHAR       | 0.3824 / 0.3837   | -0.0013 [-0.0051, +0.0042] |  -0.56 | 0.997 [0.982, 1.007] |                       5 |
| pooling_RF             | RF_pooled vs RF               | 0.3832 / 0.3761   | +0.0072 [-0.0163, +0.0509] |   0.37 | 1.019 [0.933, 1.084] |                       3 |
| pooling_NN             | NN_pooled vs NN               | 0.3618 / 0.3932   | -0.0314 [-0.0943, +0.0024] |  -1.08 | 0.920 [0.856, 1.010] |                       6 |
| averaging_vs_selection | EqualWeight vs BestPrior      | 0.3739 / 0.3992   | -0.0253 [-0.1168, +0.0262] |  -0.62 | 0.937 [0.838, 1.122] |                       7 |
| averaging_vs_members   | EqualWeight vs MeanMemberLoss | 0.3739 / 0.4105   | -0.0366 [-0.0721, -0.0158] |  -2.26 | 0.911 [0.881, 0.941] |                       8 |
| protection_drop_HAR    | EW_wo_HAR vs EqualWeight      | 0.3620 / 0.3739   | -0.0119 [-0.0281, +0.0071] |  -1.26 | 0.968 [0.883, 1.012] |                       5 |
| protection_median      | Median vs EqualWeight         | 0.3620 / 0.3739   | -0.0118 [-0.0264, +0.0063] |  -1.37 | 0.968 [0.890, 1.010] |                       5 |
| protection_trimmed     | Trimmed vs EqualWeight        | 0.3602 / 0.3739   | -0.0137 [-0.0257, -0.0003] |  -2.04 | 0.963 [0.893, 0.999] |                       5 |
| context_pooled_NN      | EqualWeight vs NN_pooled      | 0.3739 / 0.3618   | +0.0121 [-0.0159, +0.0326] |   0.93 | 1.033 [0.974, 1.155] |                       4 |
| context_logHAR         | EqualWeight vs logHAR         | 0.3739 / 0.3837   | -0.0098 [-0.0383, +0.0151] |  -0.7  | 0.974 [0.932, 1.067] |                       5 |
| context_pooled_logHAR  | EqualWeight vs logHAR_pooled  | 0.3739 / 0.3824   | -0.0085 [-0.0404, +0.0164] |  -0.58 | 0.978 [0.934, 1.073] |                       5 |

### Sensitivity: without target days below 95% bar coverage

0 evaluation date(s) excluded (any asset with fewer than 274 of 288 bars on the target day); the same forecasts are rescored.

No evaluation date is affected; the table is unchanged.
