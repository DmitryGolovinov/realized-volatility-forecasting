"""Forecast evaluation: losses, relative losses, dependence-aware comparisons, calibration."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .combine import qlike


def losses(rv: np.ndarray, f: np.ndarray) -> dict[str, np.ndarray]:
    return {"QLIKE": qlike(rv, f), "MSE": (rv - f) ** 2, "MAE": np.abs(rv - f)}


def nw_tstat(d: np.ndarray, lags: int) -> float:
    """t-statistic of mean(d) with a Newey-West (Bartlett) long-run variance.

    Forecast errors are serially dependent (volatility clusters), so i.i.d. standard errors
    would overstate precision."""
    T = len(d)
    u = d - d.mean()
    s = u @ u / T
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (u[L:] @ u[:-L]) / T
    return float(d.mean() / np.sqrt(s / T)) if s > 0 else np.nan


def block_bootstrap_ratio(
    la: np.ndarray, lb: np.ndarray, block: int, n_boot: int, seed: int = 0
) -> tuple[float, float]:
    """Moving-block bootstrap 95% interval for mean(la) / mean(lb) on paired rows."""
    rng = np.random.default_rng(seed)
    T = len(la)
    nb = int(np.ceil(T / block))
    stats = np.empty(n_boot)
    for i in range(n_boot):
        idx = (rng.integers(0, T - block + 1, nb)[:, None] + np.arange(block)).ravel()[:T]
        stats[i] = la[idx].mean() / lb[idx].mean()
    lo, hi = np.quantile(stats, [0.025, 0.975])
    return float(lo), float(hi)


def mincer_zarnowitz(rv: np.ndarray, f: np.ndarray) -> tuple[float, float]:
    A = np.c_[np.ones(len(f)), f]
    (a, b), *_ = np.linalg.lstsq(A, rv, rcond=None)
    return float(a), float(b)


def compare(fc: pd.DataFrame, models: list[str], benchmark: str, cfg: dict) -> pd.DataFrame:
    ev = cfg["evaluation"]
    rv = fc["target"].to_numpy()
    base = losses(rv, fc[benchmark].to_numpy())
    rows = []
    for m in models:
        f = fc[m].to_numpy()
        L = losses(rv, f)
        a, b = mincer_zarnowitz(rv, f)
        row = {"model": m, "n": len(rv)}
        for k in L:
            row[k] = float(L[k].mean())
            row[f"{k}_rel_{benchmark}"] = float(L[k].mean() / base[k].mean())
        d = base["QLIKE"] - L["QLIKE"]
        row["QLIKE_gain_tstat_nw"] = nw_tstat(d, ev["hac_lags"]) if m != benchmark else np.nan
        lo, hi = block_bootstrap_ratio(
            L["QLIKE"], base["QLIKE"], ev["bootstrap"]["block"], ev["bootstrap"]["n_boot"]
        )
        row["QLIKE_rel_ci_lo"], row["QLIKE_rel_ci_hi"] = lo, hi
        row["bias_rel"] = float((f - rv).mean() / rv.mean())
        row["MZ_a"], row["MZ_b"] = a, b
        rows.append(row)
    return pd.DataFrame(rows)


def by_block(fc: pd.DataFrame, models: list[str], benchmark: str, block: int) -> pd.DataFrame:
    rows = []
    for b0 in range(int(fc.index.min()), int(fc.index.max()) + 1, block):
        seg = fc.loc[b0 : b0 + block - 1]
        if len(seg) < block // 2:
            continue
        base = qlike(seg["target"].to_numpy(), seg[benchmark].to_numpy()).mean()
        for m in models:
            rows.append(
                {
                    "block_start_row": b0,
                    "model": m,
                    "QLIKE_rel": float(
                        qlike(seg["target"].to_numpy(), seg[m].to_numpy()).mean() / base
                    ),
                }
            )
    return pd.DataFrame(rows)


def by_period(
    fc: pd.DataFrame, dates: pd.Series, models: list[str], benchmark: str
) -> pd.DataFrame:
    """QLIKE relative to the benchmark per calendar year (``dates``: forecast-row dates; the
    target is the next row's variance, so a row belongs to the year of its forecast date)."""
    d = pd.to_datetime(dates.reindex(fc.index))
    rows = []
    for y, seg in fc.groupby(d.dt.year):
        base = qlike(seg["target"].to_numpy(), seg[benchmark].to_numpy()).mean()
        for m in models:
            rows.append(
                {
                    "year": int(y),
                    "model": m,
                    "rows": int(len(seg)),
                    "QLIKE_rel": float(
                        qlike(seg["target"].to_numpy(), seg[m].to_numpy()).mean() / base
                    ),
                }
            )
    return pd.DataFrame(rows)
