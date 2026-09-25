"""Single date-preserving walk-forward harness shared by every model.

Row clock: a forecast made at the end of row t targets rv_d at row t+1. At a refit origin r
the labels of rows t <= r-1 are known (their outcome row t+1 <= r), so the training window is
rows [start, r). All models share ``start = lookback - 1`` (the LSTM's first full sequence),
the same refit origins, the same inner-validation split, and the same forecast rows.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from .models import FeedForward, LSTMModel, OLSLevel, OLSLog, RandomForest, sequences

SPECS = {
    # name: (model class, feature set key, uses sequences)
    "HAR": (OLSLevel, "har_level", False),
    "logHAR": (OLSLog, "har", False),
    "HARX": (OLSLog, "harx", False),
    "RF": (RandomForest, "harx", False),
    "NN": (FeedForward, "harx", False),
    "LSTM": (LSTMModel, "harx", True),
    # Retrospective sensitivity: macro series with unknown release timing and vintage.
    "HARX_macro": (OLSLog, "harx_macro", False),
    "RF_macro": (RandomForest, "harx_macro", False),
}


def feature_sets(cfg: dict) -> dict[str, list[str]]:
    f = cfg["features"]
    return {
        "har_level": ["rv_d", "rv_w", "rv_m"],
        "har": f["har"],
        "harx": f["har"] + f["asset_extra"],
        "harx_macro": f["har"] + f["asset_extra"] + f["macro"],
    }


def refit_origins(cfg: dict, n_rows: int) -> list[int]:
    s = cfg["splits"]
    return list(range(s["initial_train_rows"], n_rows - 1, s["refit_every_rows"]))


def _split(rows: np.ndarray, frac: float) -> tuple[np.ndarray, np.ndarray]:
    k = int(round(len(rows) * (1 - frac)))
    return rows[:k], rows[k:]


def run_asset(
    df: pd.DataFrame, cfg: dict, models: list[str], seed: int = 0
) -> tuple[pd.DataFrame, list]:
    fsets = feature_sets(cfg)
    lookback = cfg["models"]["lstm"]["lookback"]
    start = lookback - 1
    y_level = df["target"].to_numpy()
    y_log = np.log(y_level)
    last = int(np.flatnonzero(np.isfinite(y_level))[-1])  # last row with a resolved target
    origins = refit_origins(cfg, last + 1)
    out = pd.DataFrame({"target": y_level}, index=df.index).iloc[origins[0] : last + 1]
    logs = []
    for r in origins:
        fc_rows = np.arange(r, min(r + cfg["splits"]["refit_every_rows"], last + 1))
        train = np.arange(start, r)
        tr, va = _split(train, cfg["splits"]["inner_validation_frac"])
        floor = float(np.nanmin(y_level[train]))
        for name in models:
            cls, fkey, seq = SPECS[name]
            X = df[fsets[fkey]].to_numpy(dtype=float)
            tic = time.perf_counter()
            if seq:
                fit = cls().fit(
                    sequences(X, tr, lookback),
                    y_log[tr],
                    sequences(X, va, lookback),
                    y_log[va],
                    cfg["models"],
                    seed,
                )
                raw = fit.predict_log(sequences(X, fc_rows, lookback))
            elif cls is OLSLevel:
                fit = cls().fit(X[tr], y_level[tr], X[va], y_level[va], cfg["models"], seed)
                raw = None
                level = fit.predict_level(X[fc_rows])
            else:
                fit = cls().fit(X[tr], y_log[tr], X[va], y_log[va], cfg["models"], seed)
                raw = fit.predict_log(X[fc_rows])
            if raw is not None:
                level = np.exp(np.asarray(raw, dtype=float)) * fit.smear
            level = np.asarray(level, dtype=float)
            out.loc[fc_rows, name] = np.maximum(level, floor)
            out.loc[fc_rows, f"{name}__floored"] = level < floor
            logs.append(
                {
                    "origin": int(r),
                    "model": name,
                    "train_rows": [int(train[0]), int(r - 1)],
                    "inner_val_rows": [int(va[0]), int(va[-1])],
                    "smear": fit.smear,
                    "floor": floor,
                    "seconds": time.perf_counter() - tic,
                    **{k: v for k, v in fit.info.items() if k != "beta"},
                }
            )
    return out, logs


def run_pooled(panel: dict[str, pd.DataFrame], cfg: dict, models: list[str], seed: int = 0):
    """Pooled models: one fit on all assets stacked, with PAST-ONLY per-asset scaling.

    At each origin every asset's features and log target are standardized with that asset's
    inner-train moments; forecasts are mapped back with the same asset's moments and smeared
    with the asset's own inner-validation residuals. Dates (rows) are identical to the
    asset-specific runs."""
    from .models import Scaler, smear_factor

    fsets = feature_sets(cfg)
    lookback = cfg["models"]["lstm"]["lookback"]
    start = lookback - 1
    assets = list(panel)
    last = min(int(np.flatnonzero(np.isfinite(panel[a]["target"].to_numpy()))[-1]) for a in assets)
    origins = refit_origins(cfg, last + 1)
    outs = {
        a: pd.DataFrame({"target": panel[a]["target"]}).iloc[origins[0] : last + 1] for a in assets
    }
    logs = []
    for r in origins:
        fc_rows = np.arange(r, min(r + cfg["splits"]["refit_every_rows"], last + 1))
        train = np.arange(start, r)
        tr, va = _split(train, cfg["splits"]["inner_validation_frac"])
        for name in models:
            cls, fkey, _ = SPECS[name]
            per = {}
            for a in assets:
                X = panel[a][fsets[fkey]].to_numpy(dtype=float)
                y = np.log(panel[a]["target"].to_numpy())
                sx = Scaler.fit(X[tr])
                ym, ys = y[tr].mean(), y[tr].std()
                per[a] = (sx(X), (y - ym) / ys, ym, ys, float(np.nanmin(np.exp(y[train]))))
            Xtr = np.concatenate([per[a][0][tr] for a in assets])
            ytr = np.concatenate([per[a][1][tr] for a in assets])
            Xva = np.concatenate([per[a][0][va] for a in assets])
            yva = np.concatenate([per[a][1][va] for a in assets])
            tic = time.perf_counter()
            fit = cls().fit(Xtr, ytr, Xva, yva, cfg["models"], seed)
            for a in assets:
                Xs, ysd, ym, ys, floor = per[a]
                pv = np.asarray(fit.predict_log(Xs[va]), dtype=float)
                smear = smear_factor((ysd[va] - pv) * ys)
                pred = np.asarray(fit.predict_log(Xs[fc_rows]), dtype=float)
                level = np.exp(pred * ys + ym) * smear
                outs[a].loc[fc_rows, f"{name}_pooled"] = np.maximum(level, floor)
            logs.append(
                {"origin": int(r), "model": f"{name}_pooled", "seconds": time.perf_counter() - tic}
            )
    return outs, logs
