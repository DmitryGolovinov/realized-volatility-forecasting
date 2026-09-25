"""Forecast combination from honestly out-of-sample history, and loss functions.

QLIKE (Patton 2011, normalized): L(RV, f) = RV/f - log(RV/f) - 1 >= 0, zero iff f = RV.
d2L/df2 = 2 RV / f^3 - 1 / f^2, which is NEGATIVE when f > 2 RV: the loss is not convex in the
forecast, so the average QLIKE of a convex combination f_w = sum_i w_i f_i need not be convex
in w even though the weights live on a simplex. We therefore search a simplex GRID (a global
search over a finite set) and report a numerical curvature check at the chosen point.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def qlike(rv: np.ndarray, f: np.ndarray) -> np.ndarray:
    x = rv / f
    return x - np.log(x) - 1.0


def simplex_grid(k: int, step: float) -> np.ndarray:
    m = int(round(1 / step))
    pts = [c for c in itertools.product(range(m + 1), repeat=k - 1) if sum(c) <= m]
    return np.array([list(c) + [m - sum(c)] for c in pts], dtype=float) / m


def best_weights(F: np.ndarray, rv: np.ndarray, grid: np.ndarray) -> tuple[np.ndarray, float]:
    """Grid minimizer of mean QLIKE of F @ w (F: T x k positive forecasts)."""
    fw = F @ grid.T  # T x G
    loss = qlike(rv[:, None], fw).mean(axis=0)
    j = int(np.argmin(loss))
    return grid[j], float(loss[j])


def hessian_min_eig(F: np.ndarray, rv: np.ndarray, w: np.ndarray) -> float:
    """Smallest eigenvalue of the Hessian of mean QLIKE(F w) in the simplex tangent space."""
    f = F @ w
    h = 2 * rv / f**3 - 1 / f**2  # per-observation second derivative in f
    H = (F * h[:, None]).T @ F / len(f)
    k = F.shape[1]
    # Basis of {d : sum d = 0}
    B = np.eye(k)[:, :-1] - np.eye(k)[:, [-1]]
    Q, _ = np.linalg.qr(B)
    return float(np.linalg.eigvalsh(Q.T @ H @ Q).min())


def combine(
    fc: pd.DataFrame,
    models: list[str],
    origins: list[int],
    refit_every: int,
    min_history: int,
    step: float,
) -> tuple[pd.DataFrame, list[dict]]:
    """Equal-weight, grid-QLIKE and best-individual forecasts using only earlier OOS rows.

    For origin r the history is OOS rows < r (whose targets are known by the end of row r).
    """
    grid = simplex_grid(len(models), step)
    out = pd.DataFrame(index=fc.index)
    out["EqualWeight"] = fc[models].mean(axis=1)
    logs = []
    first = fc.index.min()
    for r in origins:
        rows = fc.index[(fc.index >= r) & (fc.index < r + refit_every)]
        hist = fc.index[(fc.index >= first) & (fc.index < r)]
        if len(hist) < min_history or len(rows) == 0:
            continue
        F = fc.loc[hist, models].to_numpy()
        rv = fc.loc[hist, "target"].to_numpy()
        w, loss = best_weights(F, rv, grid)
        per_model = qlike(rv[:, None], F).mean(axis=0)
        best_i = int(np.argmin(per_model))
        out.loc[rows, "QLIKEComb"] = fc.loc[rows, models].to_numpy() @ w
        out.loc[rows, "BestPrior"] = fc.loc[rows, models[best_i]]
        logs.append(
            {
                "origin": int(r),
                "history_rows": int(len(hist)),
                "weights": dict(zip(models, w.round(3).tolist(), strict=True)),
                "hist_qlike": loss,
                "best_prior": models[best_i],
                "hessian_min_eig": hessian_min_eig(F, rv, w),
                "share_f_gt_2rv": float(np.mean(F @ w > 2 * rv)),
            }
        )
    return out, logs


def robust_combinations(fc: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    """Estimation-free diagnostics for the question "is the equal-weight gain diversification,
    or just averaging away one unstable model?": the median and the trimmed mean (drop the
    lowest and highest forecast) across models, and equal weights leaving each model out."""
    F = fc[models].to_numpy(dtype=float)
    out = pd.DataFrame(index=fc.index)
    out["Median"] = np.median(F, axis=1)
    S = np.sort(F, axis=1)
    out["Trimmed"] = S[:, 1:-1].mean(axis=1)
    for i, m in enumerate(models):
        out[f"EW_wo_{m}"] = np.delete(F, i, axis=1).mean(axis=1)
    return out
