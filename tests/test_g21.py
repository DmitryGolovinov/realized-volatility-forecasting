"""Generation 2.1: missing-bar quarticity correction, joint paired losses, public route."""

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rvf.crypto import BARS_PER_DAY, FIVE_MIN, daily_features, load_crypto_panel
from rvf.paired import MEMBER_MEAN, block_indices, contrast, loss_panels

ROOT = Path(__file__).resolve().parents[1]


def _bars(days: int, sigma_day: float, seed: int, drop=()) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 1_000_000)
    n = BARS_PER_DAY * days
    t = t0 + FIVE_MIN * np.arange(n)
    close = 100 * np.exp(np.cumsum(rng.normal(0, sigma_day / np.sqrt(BARS_PER_DAY), n)))
    b = pd.DataFrame({"open": close, "close": close, "quote_volume": 1.0}, index=t)
    return b.drop(index=t[list(drop)])


def test_span_quarticity_equals_complete_grid_on_complete_days_and_uses_spans_on_gaps():
    gap = list(range(BARS_PER_DAY + 100, BARS_PER_DAY + 130))  # 30 bars missing on day 2
    b = _bars(40, 0.03, 0, gap)
    old, new = daily_features(b, "complete_grid"), daily_features(b, "span")
    # the sample's first bar has no previous close: 287 returns on day 1 (a warm-up day that
    # the real panel drops); the span estimator normalizes by the returns actually observed
    assert new["span_k2"].iloc[0] == BARS_PER_DAY - 1
    full = (old["bars"] == BARS_PER_DAY) & (old.index > old.index[0])
    assert (new.loc[full, "rq_d"] == old.loc[full, "rq_d"]).all()  # bit-identical
    assert (new.loc[full, "span_k2"] == BARS_PER_DAY).all()
    day = new.index[1]
    assert old.loc[day, "bars"] == BARS_PER_DAY - 30
    # 257 one-interval returns and one return spanning 31 intervals
    assert new.loc[day, "span_k2"] == BARS_PER_DAY - 31 + 31**2
    r = np.log(b["close"]).diff()
    r4 = float((r[pd.to_datetime(b.index, unit="ms").normalize() == day] ** 4).sum())
    assert new.loc[day, "rq_d"] == pytest.approx(r4 / (3 * new.loc[day, "span_k2"] / 288**2))
    assert old.loc[day, "rq_d"] == pytest.approx(96 * r4)
    other = [c for c in old.columns if c not in ("rq_d", "span_k2")]
    pd.testing.assert_frame_equal(new[other], old[other])


def test_span_quarticity_is_unbiased_under_constant_volatility_and_complete_grid_is_not():
    """E r^4 = 3 sigma^4 delta^2: with a 90-interval gap per day, sum r^4 / (3 sum delta^2)
    targets sigma^4 while (288/3) sum r^4 overstates it (here by (197 + 91^2) / 288 = 29.4).
    One 91-interval return dominates each gap day, so the Monte Carlo sd of the mean ratio is
    about 3.2 / sqrt(2000) = 0.07; the tolerances are about 3.5 sd."""
    sigma, days = 0.02, 2000
    drop = [d * BARS_PER_DAY + j for d in range(1, days) for j in range(100, 190)]
    b = _bars(days, sigma, 1, drop)
    old, new = daily_features(b, "complete_grid"), daily_features(b, "span")
    gap = new["bars"] < BARS_PER_DAY
    ratio_new = new.loc[gap, "rq_d"].mean() / sigma**4
    ratio_old = old.loc[gap, "rq_d"].mean() / sigma**4
    assert ratio_new == pytest.approx(1.0, abs=0.25)
    expected_old = (BARS_PER_DAY - 91 + 91**2) / BARS_PER_DAY
    assert ratio_old == pytest.approx(expected_old, rel=0.25)


def test_span_quarticity_bias_is_resolved_on_small_gaps():
    """A 4-bar gap per day: 283 one-interval returns and one 5-interval return, so the
    complete-grid factor is (283 + 5**2) / 288 = 308 / 288 = 1.069. For Gaussian returns
    Var(r^4) = 96 sigma^8 delta^4, so the daily ratio of the span estimator to sigma^4 has sd
    sqrt(96 (283 + 5**4)) / (3 * 308) = 0.32 and its mean over 2,000 days has sd 0.007: the 0.025
    tolerance (about 3.5 sd) excludes a 3.5% bias, and the complete-grid estimator's 6.9% bias
    lies about 10 sd from 1."""
    sigma, days = 0.02, 2000
    drop = [d * BARS_PER_DAY + j for d in range(1, days) for j in range(100, 104)]
    b = _bars(days, sigma, 2, drop)
    old, new = daily_features(b, "complete_grid"), daily_features(b, "span")
    gap = new["bars"] < BARS_PER_DAY
    assert (new.loc[gap, "span_k2"] == BARS_PER_DAY - 5 + 5**2).all()
    ratio_new = new.loc[gap, "rq_d"].mean() / sigma**4
    ratio_old = old.loc[gap, "rq_d"].mean() / sigma**4
    assert ratio_new == pytest.approx(1.0, abs=0.025)
    assert ratio_old == pytest.approx(308 / 288, abs=0.025 * 308 / 288)
    assert ratio_old / ratio_new == pytest.approx(308 / 288, rel=1e-12)  # exact, same draws


def test_rq_scaling_is_validated():
    with pytest.raises(ValueError, match="rq_scaling"):
        daily_features(_bars(2, 0.02, 0), "other")


def test_missing_public_panel_fails_with_an_instruction(tmp_path):
    cfg = {"data": {"assets": ["BTCUSDT"]}, "splits": {"final_start": "2024-01-01"}}
    with pytest.raises(FileNotFoundError, match="make data-public"):
        load_crypto_panel(tmp_path, cfg, panel="crypto_g21")
    with pytest.raises(ValueError, match="unknown crypto panel"):
        load_crypto_panel(tmp_path, cfg, panel="crypto_v9")


def test_missing_private_stock_files_fail_with_an_instruction(tmp_path):
    from rvf.data import load_panel

    with pytest.raises(FileNotFoundError, match="make data-private.*make data-public"):
        load_panel(tmp_path, ["AAPL", "JPM"])


def _frames(T=300, N=4, seed=0, common=True):
    rng = np.random.default_rng(seed)
    shock = rng.normal(0, 1, T)
    fcs = {}
    for j in range(N):
        z = shock if common else rng.normal(0, 1, T)
        rv = np.exp(-8 + 0.5 * z + 0.1 * rng.normal(0, 1, T))
        base = np.exp(-8 + 0.4 * z)
        fcs[f"A{j}"] = pd.DataFrame(
            {"target": rv, "HAR": base * 1.3, "HARX": base, "RF": base * 0.9, "NN": base * 1.1,
             "LSTM": base, "EqualWeight": base * 1.05},
            index=np.arange(100, 100 + T),
        )  # fmt: skip
    return fcs


def test_loss_panels_align_rows_and_define_member_mean():
    fcs = _frames()
    L, rows = loss_panels(fcs, ["HAR", "HARX", "RF", "NN", "LSTM", "EqualWeight"])
    assert L["HAR"].shape == (300, 4) and rows[0] == 100
    np.testing.assert_allclose(
        L[MEMBER_MEAN], np.mean([L[m] for m in ["HAR", "HARX", "RF", "NN", "LSTM"]], axis=0)
    )
    fcs["A1"] = fcs["A1"].iloc[1:]
    with pytest.raises(ValueError, match="evaluation rows differ"):
        loss_panels(fcs, ["HAR"])


def test_joint_bootstrap_keeps_simultaneous_assets_together():
    """Identical assets add no information: the joint interval of the panel difference equals
    the one-asset interval, whereas resampling assets independently would shrink it."""
    fcs = _frames(N=1)
    one, _ = loss_panels(fcs, ["HAR", "HARX"])
    many = {m: np.repeat(v, 6, axis=1) for m, v in one.items()}
    idx = block_indices(300, 20, 500, seed=3)
    c1 = contrast(one["HARX"], one["HAR"], idx, 5)
    c6 = contrast(many["HARX"], many["HAR"], idx, 5)
    for k in ("diff", "diff_lo", "diff_hi", "pooled_ratio_lo", "mean_ratio_hi", "nw_t"):
        assert c6[k] == pytest.approx(c1[k], rel=1e-12)
    assert c6["n_assets"] == 6 and c6["assets_a_lower"] in (0, 6)


def test_contrast_statistics_arithmetic():
    La = np.array([[1.0, 2.0], [3.0, 6.0]])
    Lb = np.array([[2.0, 2.0], [2.0, 2.0]])
    c = contrast(La, Lb, np.array([[0, 1]]), 1)
    assert c["diff"] == pytest.approx(1.0)
    assert c["pooled_ratio"] == pytest.approx(3.0 / 2.0)
    assert c["mean_ratio"] == pytest.approx((2.0 / 2 + 4.0 / 2) / 2)
    idx = block_indices(50, 5, 7, seed=0)
    assert idx.shape == (7, 50) and idx.min() >= 0 and idx.max() <= 49
    assert (np.diff(idx[:, :5], axis=1) == 1).all()  # blocks are consecutive dates


def test_public_make_route_needs_no_private_input():
    for target in ("data-public", "reproduce-public"):
        out = subprocess.run(
            ["make", "-n", target], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout
        assert "recover_dates" not in out and "data/raw" not in out and "run_study" not in out
        assert "scripts/" in out


def test_pooled_scaling_and_forecasts_use_only_past_rows():
    """Pooled fits standardize each asset with its inner-train moments: perturbing every asset
    from row c on cannot change any pooled forecast made at a row < c - 1."""
    import yaml

    from rvf.harness import run_pooled

    cfg = yaml.safe_load((ROOT / "configs" / "study.yaml").read_text())
    cfg = dict(cfg, splits=dict(cfg["splits"], initial_train_rows=300, refit_every_rows=100))
    rng = np.random.default_rng(4)

    def asset(scale):
        x = np.zeros(700)
        for t in range(1, 700):
            x[t] = -9 + 0.6 * (x[t - 1] + 9) + rng.normal(0, 0.5)
        df = pd.DataFrame({"rv_d": scale * np.exp(x)})
        df["rv_w"] = df["rv_d"].rolling(5, min_periods=1).mean()
        df["rv_m"] = df["rv_d"].rolling(22, min_periods=1).mean()
        return df

    def finish(df):
        for c in ("rv_d", "rv_w", "rv_m"):
            df[f"log_{c}"] = np.log(df[c])
        df["target"] = df["rv_d"].shift(-1)
        return df

    raw = {"a": asset(1.0), "b": asset(4.0)}
    panel = {k: finish(v.copy()) for k, v in raw.items()}
    out, _ = run_pooled(panel, cfg, ["logHAR"])
    c = 550
    bumped = {}
    for k, v in raw.items():
        v = v.copy()
        v.loc[c:, "rv_d"] *= 3.0
        v["rv_w"] = v["rv_d"].rolling(5, min_periods=1).mean()
        v["rv_m"] = v["rv_d"].rolling(22, min_periods=1).mean()
        bumped[k] = finish(v)
    out2, _ = run_pooled(bumped, cfg, ["logHAR"])
    for k in raw:
        pd.testing.assert_series_equal(
            out[k].loc[: c - 2, "logHAR_pooled"], out2[k].loc[: c - 2, "logHAR_pooled"]
        )
        assert not np.allclose(out[k].loc[c:, "logHAR_pooled"], out2[k].loc[c:, "logHAR_pooled"])
