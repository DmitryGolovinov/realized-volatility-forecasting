"""Raw paired forecast losses on the whole cross-section, with dependence-preserving inference.

All assets of a run are forecast on the same dates, so their losses on one date share common
volatility shocks. Inference therefore resamples DATES in moving blocks and keeps every asset
of a drawn date together; bootstrapping each asset separately (or averaging per-asset
intervals) would treat simultaneous series as independent evidence.

For a contrast of forecast a against forecast b with QLIKE loss panels L_a, L_b (dates x assets):

* ``diff``: mean over all (date, asset) cells of L_a - L_b, in raw QLIKE units (negative: a
  has the lower loss);
* ``pooled_ratio``: mean(L_a) / mean(L_b) over all cells;
* ``mean_ratio``: mean over assets of mean_t L_a / mean_t L_b, the form of the per-asset
  relative losses averaged in ``summary_by_model.csv``;
* ``nw_t``: Newey-West t-statistic of the cross-asset mean daily difference
  d_t = mean_n (L_a - L_b)[t].

The three statistics share one set of bootstrap date indices.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .combine import qlike
from .evaluate import nw_tstat

INDIVIDUAL = ["HAR", "HARX", "RF", "NN", "LSTM"]  # the equal-weight members (frozen protocol)
MEMBER_MEAN = "MeanMemberLoss"  # not a forecast: the average of the members' losses per cell

# (contrast, forecast a, forecast b, question). Predeclared 2026-09-24, before any was computed.
CONTRASTS = [
    ("target_scale", "logHAR", "HAR", "log-target OLS versus level OLS, same HAR regressors"),
    ("features", "HARX", "logHAR", "extra asset features in the same log-OLS"),
    ("nonlinear_RF", "RF", "HARX", "random forest versus log-OLS on the same features"),
    ("nonlinear_NN", "NN", "HARX", "feed-forward net versus log-OLS on the same features"),
    ("nonlinear_LSTM", "LSTM", "HARX", "LSTM versus log-OLS on the same features"),
    ("pooling_logHAR", "logHAR_pooled", "logHAR", "pooled across assets versus asset-specific"),
    ("pooling_RF", "RF_pooled", "RF", "pooled across assets versus asset-specific"),
    ("pooling_NN", "NN_pooled", "NN", "pooled across assets versus asset-specific"),
    ("averaging_vs_selection", "EqualWeight", "BestPrior", "the protocol's primary question"),
    (
        "averaging_vs_members",
        "EqualWeight",
        MEMBER_MEAN,
        "averaging forecasts versus the members' mean loss",
    ),
    (
        "protection_drop_HAR",
        "EW_wo_HAR",
        "EqualWeight",
        "equal weights without the level-HAR member",
    ),
    ("protection_median", "Median", "EqualWeight", "median of the five members"),
    ("protection_trimmed", "Trimmed", "EqualWeight", "mean after dropping the extreme members"),
    ("context_pooled_NN", "EqualWeight", "NN_pooled", "equal weights versus the pooled net"),
    ("context_logHAR", "EqualWeight", "logHAR", "equal weights versus log-HAR"),
    (
        "context_pooled_logHAR",
        "EqualWeight",
        "logHAR_pooled",
        "equal weights versus pooled log-HAR",
    ),
]


def loss_panels(
    fcs: dict[str, pd.DataFrame], models: list[str]
) -> tuple[dict[str, np.ndarray], pd.Index]:
    """QLIKE panels (dates x assets) on the rows shared by every asset's evaluation frame."""
    assets = list(fcs)
    rows = fcs[assets[0]].index
    for a in assets[1:]:
        if not fcs[a].index.equals(rows):
            raise ValueError(f"{a}: evaluation rows differ from {assets[0]}")
    rv = np.column_stack([fcs[a]["target"].to_numpy(float) for a in assets])
    out = {}
    for m in models:
        f = np.column_stack([fcs[a][m].to_numpy(float) for a in assets])
        if not (np.isfinite(f).all() and (f > 0).all()):
            raise ValueError(f"{m}: nonpositive or missing forecasts on evaluation rows")
        out[m] = qlike(rv, f)
    if all(m in out for m in INDIVIDUAL):
        out[MEMBER_MEAN] = np.mean([out[m] for m in INDIVIDUAL], axis=0)
    return out, rows


def block_indices(T: int, block: int, n_boot: int, seed: int = 0) -> np.ndarray:
    """(n_boot, T) moving-block date indices; one row is applied to all assets at once."""
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(T / block))
    starts = rng.integers(0, T - block + 1, (n_boot, nb))
    return (starts[:, :, None] + np.arange(block)).reshape(n_boot, -1)[:, :T]


def _stats(La: np.ndarray, Lb: np.ndarray) -> tuple[float, float, float]:
    return (
        float((La - Lb).mean()),
        float(La.mean() / Lb.mean()),
        float((La.mean(axis=0) / Lb.mean(axis=0)).mean()),
    )


def contrast(La: np.ndarray, Lb: np.ndarray, idx: np.ndarray, hac_lags: int) -> dict:
    diff, pooled, mean_ratio = _stats(La, Lb)
    boot = np.array([_stats(La[i], Lb[i]) for i in idx])
    lo, hi = np.quantile(boot, [0.025, 0.975], axis=0)
    d_t = (La - Lb).mean(axis=1)
    return {
        "n_dates": int(La.shape[0]),
        "n_assets": int(La.shape[1]),
        "loss_a": float(La.mean()),
        "loss_b": float(Lb.mean()),
        "diff": diff,
        "diff_lo": float(lo[0]),
        "diff_hi": float(hi[0]),
        "nw_t": nw_tstat(d_t, hac_lags),
        "pooled_ratio": pooled,
        "pooled_ratio_lo": float(lo[1]),
        "pooled_ratio_hi": float(hi[1]),
        "mean_ratio": mean_ratio,
        "mean_ratio_lo": float(lo[2]),
        "mean_ratio_hi": float(hi[2]),
        "assets_a_lower": int((La.mean(axis=0) < Lb.mean(axis=0)).sum()),
        "dates_a_lower_share": float((d_t < 0).mean()),
    }


def paired_table(
    L: dict[str, np.ndarray], contrasts: list, block: int, n_boot: int, hac_lags: int, seed: int
) -> pd.DataFrame:
    T = next(iter(L.values())).shape[0]
    idx = block_indices(T, block, n_boot, seed)
    rows = []
    for name, a, b, q in contrasts:
        if a in L and b in L:
            rows.append(
                {"contrast": name, "a": a, "b": b, "question": q}
                | contrast(L[a], L[b], idx, hac_lags)
            )
    return pd.DataFrame(rows)


def model_table(
    L: dict[str, np.ndarray], models: list[str], block: int, n_boot: int, hac_lags: int, seed: int
) -> pd.DataFrame:
    """Every forecast's raw panel-mean QLIKE, with its pooled and mean-of-asset ratios to HAR."""
    T = L["HAR"].shape[0]
    idx = block_indices(T, block, n_boot, seed)
    rows = []
    for m in models:
        c = contrast(L[m], L["HAR"], idx, hac_lags)
        rows.append(
            {
                "model": m,
                "QLIKE": c["loss_a"],
                "diff_vs_HAR": c["diff"],
                "diff_lo": c["diff_lo"],
                "diff_hi": c["diff_hi"],
                "pooled_ratio_vs_HAR": c["pooled_ratio"],
                "pooled_ratio_lo": c["pooled_ratio_lo"],
                "pooled_ratio_hi": c["pooled_ratio_hi"],
                "mean_ratio_vs_HAR": c["mean_ratio"],
                "mean_ratio_lo": c["mean_ratio_lo"],
                "mean_ratio_hi": c["mean_ratio_hi"],
            }
        )
    return pd.DataFrame(rows)
