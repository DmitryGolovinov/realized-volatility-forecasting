from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from rvf.combine import combine, hessian_min_eig, qlike, simplex_grid
from rvf.data import guard, load_panel
from rvf.evaluate import mincer_zarnowitz, nw_tstat
from rvf.harness import run_asset
from rvf.models import OLSLog, sequences

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "study.yaml").read_text())
RAW = ROOT / "data" / "raw"
needs_data = pytest.mark.skipif(
    not (RAW / "AAPL_data.parquet").exists(), reason="supplied parquet files not imported"
)


def _synthetic(T=700, seed=0):
    rng = np.random.default_rng(seed)
    x = np.zeros(T)
    for t in range(1, T):
        x[t] = -9 + 0.6 * (x[t - 1] + 9) + rng.normal(0, 0.5)
    rv = np.exp(x)
    df = pd.DataFrame({"rv_d": rv})
    df["rv_w"] = df["rv_d"].rolling(5, min_periods=1).mean()
    df["rv_m"] = df["rv_d"].rolling(22, min_periods=1).mean()
    for c in ("rv_d", "rv_w", "rv_m"):
        df[f"log_{c}"] = np.log(df[c])
    df["target"] = df["rv_d"].shift(-1)
    return df


@needs_data
def test_supplied_data_identities_and_alignment():
    panel = load_panel(RAW, CFG["data"]["assets"])
    a = panel["AAPL"]
    assert np.allclose(a["rv_n"] + a["rv_p"], a["rv_d"], rtol=0, atol=1e-15)
    w = sum(a["rv_d"].shift(i) for i in range(5)) / 5
    assert np.nanmax(np.abs(w - a["rv_w"]).iloc[5:]) < 1e-15
    m = sum(a["rv_d"].shift(i) for i in range(22)) / 22
    assert np.nanmax(np.abs(m - a["rv_m"]).iloc[22:]) < 1e-15
    assert (a["target"].iloc[:-1].to_numpy() == a["rv_d"].iloc[1:].to_numpy()).all()


@needs_data
def test_guard_removes_reserved_rows_and_boundary_target():
    panel = guard(load_panel(RAW, ["AAPL"]), 3405, allow_final=False)
    d = panel["AAPL"]
    assert d.index.max() == 3404 and np.isnan(d["target"].iloc[-1])


def test_training_rows_end_before_each_origin_and_future_invariance():
    df = _synthetic()
    cfg = dict(CFG, splits=dict(CFG["splits"], initial_train_rows=300, refit_every_rows=100))
    out, logs = run_asset(df, cfg, ["HAR", "logHAR"])
    for lg in logs:
        assert lg["train_rows"][1] == lg["origin"] - 1  # labels up to row origin-1 only
    df2 = df.copy()
    df2.loc[550:, ["rv_d", "rv_w", "rv_m", "log_rv_d", "log_rv_w", "log_rv_m"]] *= 3.0
    df2["target"] = df2["rv_d"].shift(-1)
    out2, _ = run_asset(df2, cfg, ["HAR", "logHAR"])
    # Forecasts made at rows < 549 (whose targets are rows < 550) cannot change.
    pd.testing.assert_frame_equal(
        out.loc[:548, ["HAR", "logHAR"]], out2.loc[:548, ["HAR", "logHAR"]]
    )


def test_sequences_use_only_past_rows():
    X = np.arange(30, dtype=float)[:, None]
    s = sequences(X, np.array([21, 29]), 22)
    assert s[0, -1, 0] == 21 and s[0, 0, 0] == 0 and s[1, -1, 0] == 29
    with pytest.raises(ValueError):
        sequences(X, np.array([20]), 22)


def test_smearing_corrects_lognormal_retransformation_bias():
    rng = np.random.default_rng(1)
    x = rng.normal(size=20000)
    y = 0.5 * x + rng.normal(0, 0.8, x.size)  # log target
    fit = OLSLog().fit(x[:16000, None], y[:16000], x[16000:, None], y[16000:], {}, 0)
    naive = np.exp(fit.predict_log(x[:, None]))
    smeared = naive * fit.smear
    true_mean = np.exp(0.5 * x + 0.32)  # E[exp(y)|x] with sigma^2/2 = 0.32
    assert abs(np.mean(smeared / true_mean) - 1) < 0.02
    assert np.mean(naive / true_mean) < 0.75


def test_qlike_properties_and_nonconvexity():
    rv = np.array([1.0])
    assert qlike(rv, rv)[0] == 0.0
    f = np.linspace(0.2, 5, 200)
    d2 = np.gradient(np.gradient(qlike(np.ones_like(f), f), f), f)
    assert (d2[f < 1.8] > 0).all() and (d2[(f > 2.3) & (f < 4.8)] < 0).all()


def test_simplex_grid_and_combination_uses_history_only():
    g = simplex_grid(3, 0.25)
    assert np.allclose(g.sum(axis=1), 1) and (g >= 0).all() and len(g) == 15
    rng = np.random.default_rng(2)
    idx = pd.RangeIndex(1000, 1800)
    rv = np.exp(rng.normal(-9, 0.5, len(idx)))
    fc = pd.DataFrame(
        {
            "target": rv,
            "A": rv * np.exp(rng.normal(0, 0.3, len(idx))),
            "B": rv * 1.3,
            "C": np.full(len(idx), rv.mean()),
        },
        index=idx,
    )
    comb, logs = combine(fc, ["A", "B", "C"], list(range(1000, 1800, 100)), 100, 200, 0.1)
    fc2 = fc.copy()
    fc2.loc[1500:, "target"] *= 10  # mutate future outcomes
    comb2, logs2 = combine(fc2, ["A", "B", "C"], list(range(1000, 1800, 100)), 100, 200, 0.1)
    for a, b in zip(logs, logs2, strict=True):
        if a["origin"] <= 1500:
            assert a["weights"] == b["weights"]
    assert np.isnan(comb["QLIKEComb"].loc[1000:1199]).all()  # below the minimum history


def test_hessian_check_detects_positive_curvature_near_truth():
    rng = np.random.default_rng(3)
    rv = np.exp(rng.normal(-9, 0.3, 500))
    F = np.c_[rv * 1.05, rv * 0.95]
    assert hessian_min_eig(F, rv, np.array([0.5, 0.5])) > 0


def test_newey_west_and_mincer_zarnowitz():
    rng = np.random.default_rng(4)
    d = rng.normal(0.1, 1.0, 5000)
    assert nw_tstat(d, 5) == pytest.approx(0.1 / (1 / np.sqrt(5000)), rel=0.25)
    f = np.exp(rng.normal(size=1000))
    a, b = mincer_zarnowitz(2 * f + 1, f)
    assert a == pytest.approx(1) and b == pytest.approx(2)


def test_smearing_is_robust_to_one_extreme_validation_residual():
    from rvf.models import smear_factor

    rng = np.random.default_rng(5)
    e = rng.normal(0, 0.5, 1000)
    clean = smear_factor(e)
    e[0] = 20.0  # one extrapolated validation row (the PG counterexample had exp(e) ~ 1e8)
    assert np.mean(np.exp(e)) > 1e5  # the naive Duan factor explodes
    assert abs(smear_factor(e) - clean) < 0.02


def test_date_recovery_finds_start_and_omitted_days():
    """Synthetic panel: rows start 7 days into the reference calendar and omit two days."""
    from rvf.dates import recover_dates

    rng = np.random.default_rng(0)
    cal = pd.bdate_range("2001-01-01", periods=400)
    oc = pd.DataFrame(rng.normal(0, 0.01, (400, 5)), index=cal, columns=list("ABCDE"))
    keep = [i for i in range(7, 390) if i not in (120, 301)]
    rd = {}
    for a in oc:
        x = oc[a].to_numpy()[keep] + rng.normal(0, 0.0005, len(keep))  # measurement noise
        rd[a] = np.minimum(x, 0.0)
    res = recover_dates(rd, oc, "2001-01-01", search_days=20, anchor_rows=100)
    assert list(res["dates"]) == list(cal[keep])
    assert res["omitted_exchange_days"] == [str(cal[120].date()), str(cal[301].date())]
    assert (
        res["shifted_plus1_agreement"]
        < 0.7
        < np.mean(list(res["per_asset_sign_agreement"].values()))
    )


def test_crypto_daily_features_identities():
    """rv_n + rv_p = rv_d; rv_w/rv_m trailing means; gap return booked on the next bar."""
    from rvf.crypto import FIVE_MIN, daily_features

    rng = np.random.default_rng(1)
    t0 = int(pd.Timestamp("2020-01-01", tz="UTC").value // 1_000_000)
    n = 288 * 40
    t = t0 + FIVE_MIN * np.arange(n)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 1e-3, n)))
    b = pd.DataFrame(
        {
            "open": close * (1 + rng.normal(0, 1e-4, n)),
            "close": close,
            "quote_volume": rng.uniform(1, 2, n),
        },
        index=t,
    )
    b = b.drop(index=t[500:505])  # a 25-minute gap on day 1
    f = daily_features(b)
    assert len(f) == 40
    np.testing.assert_allclose(f["rv_n"] + f["rv_p"], f["rv_d"], rtol=1e-12)
    np.testing.assert_allclose(f["rv_w"].iloc[10], f["rv_d"].iloc[4:11].mean())
    np.testing.assert_allclose(f["rv_m"].iloc[35], f["rv_d"].iloc[6:36].mean())
    lc = np.log(b["close"])
    r = lc.diff()
    assert r.loc[t[505]] == pytest.approx(np.log(close[505] / close[499]))
    assert (f["r_d"] <= 0).all() and (f["r_w"].dropna() <= 0).all()


def test_robust_combinations():
    from rvf.combine import robust_combinations

    fc = pd.DataFrame(
        {"a": [1.0, 2.0], "b": [3.0, 2.0], "c": [2.0, 9.0], "d": [4.0, 1.0], "e": [10.0, 3.0]}
    )
    r = robust_combinations(fc, list("abcde"))
    np.testing.assert_allclose(r["Median"], [3.0, 2.0])
    np.testing.assert_allclose(r["Trimmed"], [3.0, 7 / 3])
    np.testing.assert_allclose(r["EW_wo_e"], [2.5, 3.5])
