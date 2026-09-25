"""Recovering the calendar of the supplied (undated) panel.

The supplied files carry no dates. ``r_d`` is the negative part of the open-to-close return,
min(r_oc, 0) (it is never positive and is zero on up days). Its sign pattern identifies each
row's trading day: for the correct day, the five stocks' signs agree with public open-to-close
returns on about 97% of asset-days; for a wrong day, on about 50%.

Alignment: row i is matched to exchange trading day j(i) = j0 + i + k(i) where k(i) >= 0 is
non-decreasing (the panel can omit exchange days but never repeats or reorders them). The score
of a row is the number of stocks whose sign agrees; each omitted day costs ``skip_penalty``.
The optimal path is found by dynamic programming (Viterbi). ``recover_dates`` returns the dates,
per-row agreement, and the omitted days. The external prices are used only to date rows; they
are not stored or redistributed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sign_scores(rd: dict, oc: dict, n: int, j0: int, k_max: int) -> np.ndarray:
    """(n, k_max + 1) array: number of assets whose sign(r_d < 0) matches sign(oc < 0) for
    row i matched to day j0 + i + k. Days beyond the reference calendar score -inf."""
    L = len(next(iter(oc.values())))
    M = np.full((n, k_max + 1), -np.inf)
    for k in range(k_max + 1):
        j = j0 + np.arange(n) + k
        ok = j < L
        s = np.zeros(n)
        for a in rd:
            x = np.asarray(oc[a], float)[np.minimum(j, L - 1)]
            s += ((np.asarray(rd[a]) < 0) == (x < 0)).astype(float)
        M[:, k] = np.where(ok, s, -np.inf)
    return M


def viterbi_offsets(M: np.ndarray, skip_penalty: float) -> np.ndarray:
    """Non-decreasing offset path k(i) maximizing sum M[i, k(i)] - penalty * total skips."""
    n, K = M.shape
    V = np.full((n, K), -np.inf)
    back = np.zeros((n, K), dtype=int)
    V[0] = M[0] - skip_penalty * np.arange(K)  # an offset before row 0 is an omission too
    for i in range(1, n):
        for k in range(K):
            cand = V[i - 1, : k + 1] - skip_penalty * (k - np.arange(k + 1))
            kk = int(np.argmax(cand))
            V[i, k] = cand[kk] + M[i, k]
            back[i, k] = kk
    path = np.empty(n, dtype=int)
    k = int(np.argmax(V[-1]))
    for i in range(n - 1, -1, -1):
        path[i] = k
        k = back[i, k]
    return path


def value_distance(rd: dict, oca: dict, rows: np.ndarray, days: np.ndarray) -> float:
    """Sum over assets of |r_d - min(open-to-close, 0)| for the given row -> day matches."""
    tot = 0.0
    for a in rd:
        x = np.minimum(np.asarray(oca[a], float)[days], 0.0)
        tot += float(np.nansum(np.abs(np.asarray(rd[a])[rows] - x)))
    return tot


def refine_switches(path: np.ndarray, rd: dict, oca: dict, j0: int, radius: int = 3):
    """Place each omission (offset switch) at the position within +/- ``radius`` rows that best
    matches the SIZE of r_d to public open-to-close returns. Sign agreement cannot separate
    adjacent days when their signs coincide; sizes do (a correct match differs by a few basis
    points, a neighbouring day by about one percent). Returns the path and, per switch, the
    value distance of the chosen and the runner-up position."""
    path = path.copy()
    n = len(path)
    out = []
    for r in np.flatnonzero(np.diff(path)) + 1:
        k0, k1 = int(path[r - 1]), int(path[r])
        lo, hi = max(1, r - radius), min(n - 1, r + radius)
        rows = np.arange(lo - 1, hi + 1)
        scores = {}
        for q in range(lo, hi + 1):
            k = np.where(rows < q, k0, k1)
            scores[q] = value_distance(rd, oca, rows, j0 + rows + k)
        best = min(scores, key=scores.get)
        others = sorted(v for q, v in scores.items() if q != best)
        path[lo - 1 : hi + 1] = np.where(rows < best, k0, k1)
        out.append(
            {
                "viterbi_row": int(r),
                "chosen_row": int(best),
                "value_distance_chosen": scores[best],
                "value_distance_runner_up": others[0] if others else None,
            }
        )
    return path, out


def recover_dates(
    rd: dict,
    oc: pd.DataFrame,
    start: str,
    search_days: int = 60,
    anchor_rows: int = 250,
    k_max: int = 4,
    skip_penalty: float = 10.0,
) -> dict:
    """``rd``: asset -> supplied r_d array; ``oc``: public open-to-close log returns (one
    column per asset) on the exchange calendar; ``start``: earliest candidate day for row 0.

    Row 0 is anchored first: the start day (within ``search_days`` of ``start``) maximizing the
    mean agreement of the first ``anchor_rows`` rows with no omitted day. This keeps a few
    uninformative early rows (all-zero r_d matches any up day) from buying spurious skips. Then
    the Viterbi path allows up to ``k_max`` omitted days; each costs ``skip_penalty`` agreement
    points, so an omission needs several rows of evidence."""
    n = len(next(iter(rd.values())))
    cal = oc.index
    oca = {a: oc[a].to_numpy() for a in rd}
    base = int(np.searchsorted(cal, pd.Timestamp(start)))
    head = {a: np.asarray(v)[:anchor_rows] for a, v in rd.items()}
    anchor = sign_scores(head, oca, anchor_rows, base, search_days)
    j0 = base + int(np.argmax(anchor.mean(axis=0)))
    M = sign_scores(rd, oca, n, j0, k_max)
    path = viterbi_offsets(M, skip_penalty)
    path, refine = refine_switches(path, rd, oca, j0)
    j = j0 + np.arange(n) + path
    dates = cal[j]
    used = set(j.tolist())
    omitted = [cal[q] for q in range(j[0], j[-1] + 1) if q not in used]
    agree = M[np.arange(n), path]
    per_asset = {}
    for a in rd:
        x = oc[a].to_numpy()[j]
        per_asset[a] = float(np.mean((np.asarray(rd[a]) < 0) == (x < 0)))
    # Evidence against the runner-up: the same rows shifted by one day either way.
    alt = {}
    for s in (-1, 1):
        jj = np.clip(j + s, 0, len(cal) - 1)
        alt[s] = float(
            np.mean([np.mean((np.asarray(rd[a]) < 0) == (oc[a].to_numpy()[jj] < 0)) for a in rd])
        )
    # Identification diagnostics (audit): the score margin of every omission against moving it
    # 1-3 rows earlier or later (a small margin means the rows next to the omission could be
    # one day off), the longest offset used versus k_max, and the weakest 20-row agreement.
    sw = np.flatnonzero(np.diff(path)) + 1
    margins = []
    for r in sw:
        k0, k1 = path[r - 1], path[r]
        best_alt = -np.inf
        for m in (-3, -2, -1, 1, 2, 3):
            q = r + m
            if q <= 0 or q >= n:
                continue
            lo, hi = min(q, r), max(q, r)
            # moving the switch from r to q changes the offset of rows [lo, hi)
            gain = M[lo:hi, k1 if q < r else k0].sum() - M[lo:hi, k0 if q < r else k1].sum()
            best_alt = max(best_alt, gain)
        margins.append(
            {
                "row": int(r),
                "omitted_days": int(k1 - k0),
                "margin_vs_shift_1_3_rows": float(-best_alt),
            }
        )
    roll = pd.Series(agree).rolling(20).mean()
    if path.max() >= k_max:
        raise ValueError("offset reached k_max: more omissions than allowed; widen k_max")
    return {
        "skip_margins": margins,
        "switch_refinement": refine,
        "min_rolling20_agreement": float(roll.min()),
        "k_max_reached": bool(path.max() >= k_max),
        "dates": pd.DatetimeIndex(dates),
        "agreement": agree,
        "omitted_exchange_days": [str(d.date()) for d in omitted],
        "per_asset_sign_agreement": per_asset,
        "shifted_minus1_agreement": alt[-1],
        "shifted_plus1_agreement": alt[1],
    }
