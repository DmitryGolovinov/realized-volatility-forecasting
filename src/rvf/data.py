"""Supplied realized-variance panel: loading, identity checks, features, reserved rows.

The files carry no dates (RangeIndex 0..4256), so the row index is the only clock. Verified
identities (tests/test_data.py): rv_w and rv_m are trailing means of rv_d over rows t-4..t and
t-21..t, and rv_n + rv_p = rv_d. Hence every feature at row t is known at the end of day t and
the target rv_d at row t+1 is the next day's realized variance.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


class ReservedSampleError(RuntimeError):
    pass


LOG_COLS = {
    "log_rv_d": "rv_d",
    "log_rv_w": "rv_w",
    "log_rv_m": "rv_m",
    "log_rv_n": "rv_n",
    "log_rv_p": "rv_p",
}


def file_hashes(src: Path, assets: list[str]) -> dict:
    out = {}
    for name in assets + ["macro"]:
        p = Path(src) / f"{name}_data.parquet"
        out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def load_panel(src: Path, assets: list[str]) -> dict[str, pd.DataFrame]:
    need = [Path(src) / "macro_data.parquet"] + [Path(src) / f"{a}_data.parquet" for a in assets]
    missing = [p.name for p in need if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"{', '.join(missing)} missing in {src}: the archival stock study needs the supplied "
            "*_data.parquet and macro_data.parquet files, which are not redistributed (`make "
            "data-private` explains). The public crypto study does not need them: `make "
            "data-public reproduce-public`."
        )
    macro = pd.read_parquet(Path(src) / "macro_data.parquet")
    out = {}
    for a in assets:
        df = pd.read_parquet(Path(src) / f"{a}_data.parquet")
        if len(df) != len(macro) or not df.index.equals(macro.index):
            raise ValueError(f"{a}: row index does not match the macro file")
        df = df.join(macro)
        for new, old in LOG_COLS.items():
            if (df[old] <= 0).any():
                raise ValueError(f"{a}: nonpositive {old}; log transform undefined")
            df[new] = np.log(df[old])
        df["target"] = df["rv_d"].shift(-1)  # RV_{t+1}; NaN on the last row (unresolved)
        out[a] = df
    return out


def guard(panel: dict[str, pd.DataFrame], final_start_row: int, allow_final: bool) -> dict:
    """Drop reserved rows (and the target that would reach into them) unless allowed."""
    if allow_final:
        return panel
    out = {}
    for a, df in panel.items():
        d = df.iloc[:final_start_row].copy()
        # The target of the last development row is rv_d of the first reserved row: drop it.
        d.loc[d.index[-1], "target"] = np.nan
        out[a] = d
    return out


def check_no_reserved_rows(panel: dict[str, pd.DataFrame], final_start_row: int) -> None:
    for a, df in panel.items():
        if df.index.max() >= final_start_row:
            raise ReservedSampleError(f"{a}: reserved rows present in development data")
