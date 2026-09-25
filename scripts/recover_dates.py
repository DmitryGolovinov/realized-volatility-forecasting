"""Recover the trading-day calendar of the supplied panel (see src/rvf/dates.py).

Downloads public daily OHLC prices (Yahoo Finance via yfinance, research use; not stored) and
writes data/date_map.csv (row -> date, agreement) plus data/date_map_provenance.json.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rvf.dates import recover_dates  # noqa: E402

if __name__ == "__main__":
    import yfinance as yf

    cfg = yaml.safe_load((ROOT / "configs" / "study.yaml").read_text())
    assets = cfg["data"]["assets"]
    raw = yf.download(
        assets,
        start="2000-06-01",
        end="2018-06-30",
        auto_adjust=False,
        progress=False,
        threads=False,
        group_by="column",
    )
    oc = np.log(raw["Close"][assets] / raw["Open"][assets])
    oc.index = pd.to_datetime(oc.index).tz_localize(None)
    rd = {
        a: pd.read_parquet(ROOT / "data" / "raw" / f"{a}_data.parquet")["r_d"].to_numpy()
        for a in assets
    }
    res = recover_dates(rd, oc, "2001-01-01")
    out = pd.DataFrame(
        {
            "row": np.arange(len(res["dates"])),
            "date": res["dates"].strftime("%Y-%m-%d"),
            "sign_agreement_of_5": res["agreement"].astype(int),
        }
    )
    out.to_csv(ROOT / "data" / "date_map.csv", index=False)
    prov = {
        "method": "Viterbi alignment of sign(r_d < 0) to sign(public open-to-close < 0); "
        "rows may omit exchange days, never repeat or reorder them",
        "reference": "Yahoo Finance daily Open/Close via yfinance (not stored)",
        "yfinance_version": yf.__version__,
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "first_date": out["date"].iloc[0],
        "last_date": out["date"].iloc[-1],
        "rows": int(len(out)),
        "omitted_exchange_days": res["omitted_exchange_days"],
        "mean_sign_agreement_of_5": float(res["agreement"].mean()),
        "rows_with_agreement_le_2": int((res["agreement"] <= 2).sum()),
        "per_asset_sign_agreement": res["per_asset_sign_agreement"],
        "shifted_minus1_agreement": res["shifted_minus1_agreement"],
        "shifted_plus1_agreement": res["shifted_plus1_agreement"],
        "skip_margins": res["skip_margins"],
        "switch_refinement": res["switch_refinement"],
        "min_rolling20_agreement_of_5": res["min_rolling20_agreement"],
        "reads_reserved_rows": "sign and size of r_d (rows >= 3405 included), to date them and "
        "place the omissions; no variance, target, or model output is read",
        "key_rows": {str(r): out["date"].iloc[r] for r in (0, 1000, 3404, 3405, len(out) - 1)},
    }
    (ROOT / "data" / "date_map_provenance.json").write_text(json.dumps(prov, indent=1))
    print(json.dumps(prov, indent=1))
