"""Generation 2 transfer panel: daily realized-variance features for liquid crypto assets from
Binance public spot 5-minute klines (definitions in configs/g2_crypto_transfer.yaml).

Integrity: every monthly archive is verified against the exchange's published SHA-256 before
use; spot archives from 2025 use microsecond timestamps (detected from magnitude); bars must be
on the 5-minute grid; duplicate open times must be identical or the build fails. Missing bars
are not filled: the price change across a gap is booked on the next available bar and each
day's bar coverage is recorded.

Two panels are built from the same verified archives (they differ only in ``rq_d``):

* ``data/crypto/`` (Generation 2, historical): rq_d = (288/3) sum r^4, the complete-grid
  scaling, applied even on days with missing bars;
* ``data/crypto_g21/`` (Generation 2.1 data correction): rq_d = sum r_i^4 / (3 sum delta_i^2),
  delta_i = span of return i as a fraction of the day. Identical on complete days and unbiased
  for sigma^4 when volatility is constant over the day (Gaussian increments, no drift or
  jumps); the complete-grid formula overstates quarticity on gap days (a return spanning k
  intervals has E r^4 = 3 sigma^4 (k/288)^2, not k times 3 sigma^4 / 288^2).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE = "https://data.binance.vision/data/spot/monthly/klines"
FIVE_MIN = 300_000
BARS_PER_DAY = 288
COLS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "count",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]


def month_list(first: str, last: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(first, last, freq="M")]


def fetch_month(session, symbol: str, month: str, raw_dir: Path) -> dict:
    """Download one archive (cached) and verify it against the published checksum."""
    name = f"{symbol}-5m-{month}.zip"
    url = f"{BASE}/{symbol}/5m/{name}"
    dest = Path(raw_dir) / symbol / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    ck = session.get(url + ".CHECKSUM", timeout=60)
    ck.raise_for_status()
    expected = ck.text.split()[0].strip().lower()
    if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest() != expected:
        r = session.get(url, timeout=120)
        r.raise_for_status()
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(r.content)
        tmp.replace(dest)
    got = hashlib.sha256(dest.read_bytes()).hexdigest()
    if got != expected:
        raise RuntimeError(f"checksum mismatch for {name}")
    return {"url": url, "sha256": got, "bytes": dest.stat().st_size}


def read_klines(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        (n,) = [x for x in z.namelist() if x.endswith(".csv")]
        raw = z.read(n)
    header = raw[:9].startswith(b"open_time")
    df = pd.read_csv(io.BytesIO(raw), header=0 if header else None).iloc[:, :12]
    df.columns = COLS
    t = df["open_time"].to_numpy(np.int64)
    if np.median(t) > 1e14:  # microseconds (2025+ spot archives)
        df["open_time"] = t // 1000
    return df


def bars(raw_dir: Path, symbol: str, months: list[str]) -> pd.DataFrame:
    df = pd.concat(
        [read_klines(Path(raw_dir) / symbol / f"{symbol}-5m-{m}.zip") for m in months],
        ignore_index=True,
    )
    df = df.sort_values("open_time")
    dup = df["open_time"].duplicated(keep=False)
    if dup.any():
        g = df[dup].groupby("open_time")[["open", "high", "low", "close", "volume"]].nunique()
        if (g > 1).any().any():
            raise ValueError(f"{symbol}: conflicting duplicate bars")
        df = df.drop_duplicates("open_time")
    if (df["open_time"] % FIVE_MIN != 0).any():
        raise ValueError(f"{symbol}: bar not on the 5-minute grid")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError(f"{symbol}: nonpositive price")
    return df.set_index("open_time")


RQ_SCALINGS = ("complete_grid", "span")
PANELS = {"crypto": "complete_grid", "crypto_g21": "span"}  # panel directory -> rq scaling


def daily_features(b: pd.DataFrame, rq_scaling: str = "complete_grid") -> pd.DataFrame:
    """Daily RV panel from 5-minute bars (index: UTC day).

    ``rq_scaling`` selects the realized-quarticity normalization (module docstring); every other
    column is identical for both. ``span_k2`` is sum k_i^2 over the day's returns, k_i the
    number of 5-minute intervals return i spans (288 on a complete day)."""
    if rq_scaling not in RQ_SCALINGS:
        raise ValueError(f"unknown rq_scaling {rq_scaling!r}")
    lc = np.log(b["close"])
    r = lc.diff()  # a gap's price change is booked on the next available bar
    k = pd.Series(np.diff(b.index.to_numpy(), prepend=b.index[0] - FIVE_MIN) / FIVE_MIN)
    day = pd.to_datetime(b.index, unit="ms").normalize()
    g = pd.DataFrame(
        {
            "r": r.to_numpy(),
            "k2": np.where(np.isfinite(r.to_numpy()), k.to_numpy() ** 2, 0.0),
            "day": day,
            "close": b["close"].to_numpy(),
            "open": b["open"].to_numpy(),
            "qv": b["quote_volume"].to_numpy(),
        }
    )
    grp = g.groupby("day")
    r4 = grp["r"].apply(lambda x: float(np.nansum(x**4)))
    k2 = grp["k2"].sum()
    if rq_scaling == "complete_grid":
        rq = BARS_PER_DAY / 3 * r4
    else:  # sum r^4 / (3 sum (k/288)^2); exactly (288/3) sum r^4 when every k is 1
        rq = r4 * (BARS_PER_DAY**2 / (3 * k2))
    out = pd.DataFrame(
        {
            "rv_d": grp["r"].apply(lambda x: float(np.nansum(x**2))),
            "rv_n": grp["r"].apply(lambda x: float(np.nansum(np.where(x < 0, x, 0.0) ** 2))),
            "rv_p": grp["r"].apply(lambda x: float(np.nansum(np.where(x > 0, x, 0.0) ** 2))),
            "rq_d": rq,
            "open": grp["open"].first(),
            "close": grp["close"].last(),
            "qv": grp["qv"].sum(),
            "bars": grp.size(),
            "span_k2": k2,
        }
    )
    oc = np.log(out["close"] / out["open"])
    out["r_d"] = np.minimum(oc, 0.0)
    out["r_w"] = np.minimum(oc.rolling(7).mean(), 0.0)
    out["r_m"] = np.minimum(oc.rolling(30).mean(), 0.0)
    out["mom1w"] = np.log(out["close"]).diff(7)
    out["dolvol"] = np.log(out["qv"]).diff()
    out["rv_w"] = out["rv_d"].rolling(7).mean()
    out["rv_m"] = out["rv_d"].rolling(30).mean()
    full = pd.date_range(out.index.min(), out.index.max(), freq="D")
    if len(full) != len(out):
        raise ValueError("missing whole UTC days")
    return out


def build(root: Path, cfg: dict, panels: tuple[str, ...] = tuple(PANELS)) -> dict:
    """Download (cached, checksum-verified) and write each requested panel with its manifest."""
    import requests

    root = Path(root)
    d = cfg["data"]
    months = month_list(*d["months"])
    raw_dir = root / "data" / "crypto_raw"
    from concurrent.futures import ThreadPoolExecutor

    jobs = [(sym, m) for sym in d["assets"] for m in months]
    with ThreadPoolExecutor(max_workers=8) as ex:  # I/O bound; each job verifies its checksum
        recs = list(ex.map(lambda j: fetch_month(requests.Session(), j[0], j[1], raw_dir), jobs))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mans = {}
    for panel in panels:
        out_dir = root / "data" / panel
        out_dir.mkdir(parents=True, exist_ok=True)
        man = {"retrieved_utc": stamp, "archives": {}, "qc": {}}
        if PANELS[panel] != "complete_grid":  # the historical manifest format is kept as it was
            man["rq_scaling"] = PANELS[panel]
        for (sym, m), rec in zip(jobs, recs, strict=True):
            man["archives"][f"{sym}/{m}"] = rec
        for sym in d["assets"]:
            f = daily_features(bars(raw_dir, sym, months), PANELS[panel])
            f = f.loc[d["first_day"] : d["last_day"]]
            f.index.name = "date"
            if PANELS[panel] == "complete_grid":
                f = f.drop(columns="span_k2")  # historical column set
            f.to_parquet(out_dir / f"{sym}.parquet")
            man["qc"][sym] = {
                "days": int(len(f)),
                "first": str(f.index.min().date()),
                "last": str(f.index.max().date()),
                "days_below_95pct_bars": int((f["bars"] < 0.95 * BARS_PER_DAY).sum()),
                "min_bars": int(f["bars"].min()),
                "nonpositive_rv_days": int((f["rv_d"] <= 0).sum()),
            }
            if PANELS[panel] != "complete_grid":
                man["qc"][sym]["days_with_missing_bars"] = int((f["bars"] < BARS_PER_DAY).sum())
        (out_dir / "manifest.json").write_text(json.dumps(man, indent=1))
        mans[panel] = man
    return mans


def load_crypto_panel(
    root: Path, cfg: dict, allow_final: bool = False, panel: str = "crypto"
) -> dict[str, pd.DataFrame]:
    """Row-indexed panel (0..n-1) with a ``date`` column, log features and next-day target.

    Without ``allow_final`` the reserved rows are dropped BEFORE any check, so no property of
    the final sample can influence a development run (not even through an exception)."""
    if panel not in PANELS:
        raise ValueError(f"unknown crypto panel {panel!r}; expected one of {list(PANELS)}")
    out = {}
    final_start = pd.Timestamp(cfg["splits"]["final_start"])
    for sym in cfg["data"]["assets"]:
        path = Path(root) / "data" / panel / f"{sym}.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Build the public panels first with `make data-public` "
                "(downloads Binance public spot 5-minute klines, ~0.3 GB, SHA-256 verified)."
            )
        f = pd.read_parquet(path)
        if not allow_final:
            f = f[f.index < final_start]
        df = f.reset_index()
        for c in ("rv_d", "rv_w", "rv_m", "rv_n", "rv_p"):
            if (df[c] <= 0).any():
                raise ValueError(f"{sym}: nonpositive {c}; log transform undefined")
            df[f"log_{c}"] = np.log(df[c])
        df["target"] = df["rv_d"].shift(-1)
        out[sym] = df
    return out
