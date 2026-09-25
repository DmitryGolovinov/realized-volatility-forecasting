"""Loader and reserved-row guard on a small synthetic panel written in the supplied-file layout.

The two data tests in test_rvf.py need the supplied parquet files, which are not published; this
test exercises the same code paths (row alignment, log columns, target shift, guard) offline."""

import numpy as np
import pandas as pd
import pytest

from rvf.data import ReservedSampleError, check_no_reserved_rows, guard, load_panel


def _write_panel(root, T=60, seed=0):
    rng = np.random.default_rng(seed)
    rv_n = np.exp(rng.normal(-10, 0.5, T))
    rv_p = np.exp(rng.normal(-10, 0.5, T))
    df = pd.DataFrame({"rv_n": rv_n, "rv_p": rv_p, "rv_d": rv_n + rv_p})
    df["rv_w"] = df["rv_d"].rolling(5, min_periods=1).mean()
    df["rv_m"] = df["rv_d"].rolling(22, min_periods=1).mean()
    df.to_parquet(root / "AAPL_data.parquet")
    pd.DataFrame({"vix": rng.uniform(10, 30, T)}).to_parquet(root / "macro_data.parquet")
    return df


def test_loader_and_guard_on_synthetic_panel(tmp_path):
    raw = _write_panel(tmp_path)
    a = load_panel(tmp_path, ["AAPL"])["AAPL"]
    assert np.allclose(a["log_rv_d"], np.log(raw["rv_d"]))
    assert (a["target"].iloc[:-1].to_numpy() == raw["rv_d"].iloc[1:].to_numpy()).all()
    assert np.isnan(a["target"].iloc[-1])  # the last row's target is unresolved

    final_start = 40
    with pytest.raises(ReservedSampleError):
        check_no_reserved_rows({"AAPL": a}, final_start)
    dev = guard({"AAPL": a}, final_start, allow_final=False)
    d = dev["AAPL"]
    check_no_reserved_rows(dev, final_start)
    assert d.index.max() == final_start - 1
    assert np.isnan(d["target"].iloc[-1])  # would have been rv_d of the first reserved row
    assert (d["target"].iloc[:-1] == a["target"].iloc[: final_start - 1]).all()
    assert guard({"AAPL": a}, final_start, allow_final=True)["AAPL"] is a


def test_loader_rejects_misaligned_rows(tmp_path):
    _write_panel(tmp_path)
    pd.DataFrame({"vix": np.ones(59)}).to_parquet(tmp_path / "macro_data.parquet")
    with pytest.raises(ValueError, match="row index"):
        load_panel(tmp_path, ["AAPL"])
