"""Raw paired losses for completed runs, from their saved forecast files (no refitting).

    python scripts/paired_losses.py crypto_final crypto_g21_final ...

For each run: the evaluation rows are rebuilt exactly as the run scored them (rows with a
resolved combination and prior-best forecast; in final mode only rows >= the reserved start),
every asset's mean QLIKE is checked against the run's ``comparison.csv``, and the paired
contrasts of ``rvf.paired`` are written to ``results/<run>/paired_losses.csv`` with a joint
(all assets per date) moving-block bootstrap. Crypto runs add a sensitivity sample without the
target days on which any asset has fewer than 95% of its 288 five-minute bars.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rvf.crypto import BARS_PER_DAY  # noqa: E402
from rvf.manifest import sha256_file, tree_hash, write_manifest  # noqa: E402
from rvf.paired import CONTRASTS, loss_panels, model_table, paired_table  # noqa: E402

N_BOOT, SEED = 2000, 0  # predeclared; block and HAC lags come from configs/study.yaml
MODELS = [
    "HAR", "logHAR", "HARX", "RF", "NN", "LSTM", "EqualWeight", "QLIKEComb", "BestPrior",
    "logHAR_pooled", "RF_pooled", "NN_pooled", "Median", "Trimmed",
    "EW_wo_HAR", "EW_wo_HARX", "EW_wo_RF", "EW_wo_NN", "EW_wo_LSTM",
]  # fmt: skip


def evaluation_frames(run: str) -> tuple[dict[str, pd.DataFrame], dict]:
    res = ROOT / "results" / run
    man = json.loads((res / "manifest.json").read_text())
    assets = man.get("assets") or list(man["evaluation_rows"])
    fs = int(man["reserved_final_start_row"])
    fcs = {}
    for a in assets:
        fc = pd.read_parquet(res / f"forecasts_{a}_with_combinations.parquet")
        fc = fc.dropna(subset=["QLIKEComb", "BestPrior"])
        if man["mode"] == "final":
            fc = fc[fc.index >= fs]
        fcs[a] = fc
    return fcs, man


def check_against_run(run: str, L: dict[str, np.ndarray], assets: list[str]) -> float:
    comp = pd.read_csv(ROOT / "results" / run / "comparison.csv")
    worst = 0.0
    for m in MODELS:
        if m not in L:
            continue
        for j, a in enumerate(assets):
            rec = comp[(comp["asset"] == a) & (comp["model"] == m)]["QLIKE"]
            if len(rec) != 1:
                raise ValueError(f"{run}: {a}/{m} missing from comparison.csv")
            worst = max(worst, abs(L[m][:, j].mean() - float(rec.iloc[0])) / float(rec.iloc[0]))
    if worst > 1e-10:
        raise ValueError(f"{run}: rebuilt losses differ from comparison.csv (rel {worst:.2e})")
    return worst


def coverage_mask(run: str, man: dict, fcs: dict[str, pd.DataFrame]) -> np.ndarray | None:
    """True for rows whose TARGET day has >= 95% bar coverage for every asset (crypto only)."""
    if not run.startswith("crypto"):
        return None
    panel = man.get("panel", "crypto")
    keep = None
    for a, fc in fcs.items():
        bars = pd.read_parquet(ROOT / "data" / panel / f"{a}.parquet")["bars"]
        target_day = pd.to_datetime(fc["date"]) + pd.Timedelta(days=1)
        ok = bars.reindex(target_day).to_numpy() >= 0.95 * BARS_PER_DAY
        keep = ok if keep is None else keep & ok
    return keep


def run_one(run: str, cfg: dict) -> dict:
    ev = cfg["evaluation"]
    block, lags = ev["bootstrap"]["block"], ev["hac_lags"]
    fcs, man = evaluation_frames(run)
    assets = list(fcs)
    models = [m for m in MODELS if m in fcs[assets[0]].columns]
    L, rows = loss_panels(fcs, models)
    worst = check_against_run(run, L, assets)
    samples = {"all": np.ones(len(rows), bool)}
    mask = coverage_mask(run, man, fcs)
    if mask is not None:
        samples["target_coverage_ge_95pct"] = mask
    tabs, mtabs, sizes = [], [], {}
    for s, keep in samples.items():
        Ls = {m: v[keep] for m, v in L.items()}
        t = paired_table(Ls, CONTRASTS, block, N_BOOT, lags, SEED)
        t.insert(0, "sample", s)
        tabs.append(t)
        mt = model_table(Ls, models, block, N_BOOT, lags, SEED)
        mt.insert(0, "sample", s)
        mtabs.append(mt)
        sizes[s] = {"dates": int(keep.sum()), "dates_excluded": int((~keep).sum())}
    res = ROOT / "results" / run
    pd.concat(tabs, ignore_index=True).to_csv(res / "paired_losses.csv", index=False)
    pd.concat(mtabs, ignore_index=True).to_csv(res / "model_losses.csv", index=False)
    rec = {
        "study": "realized-volatility-forecasting / raw paired losses (joint date bootstrap)",
        "run": run,
        "run_manifest_sha256": sha256_file(res / "manifest.json"),
        "forecast_files_sha256": {
            a: sha256_file(res / f"forecasts_{a}_with_combinations.parquet") for a in assets
        },
        "assets": assets,
        "evaluation_first_row": int(rows.min()),
        "evaluation_last_row": int(rows.max()),
        "samples": sizes,
        "bootstrap": {
            "block_dates": block,
            "n_boot": N_BOOT,
            "seed": SEED,
            "joint_over_assets": True,
        },
        "hac_lags": lags,
        "max_rel_diff_vs_comparison_csv": worst,
        "source_tree_sha256": tree_hash(ROOT),
        "command": f"python scripts/paired_losses.py {run}",
    }
    write_manifest(
        res / "paired_losses_manifest.json",
        rec,
        [res / "paired_losses.csv", res / "model_losses.csv"],
    )
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    a = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "configs" / "study.yaml").read_text())
    for run in a.runs:
        if not (ROOT / "results" / run / "manifest.json").exists():
            sys.exit(f"results/{run}/manifest.json not found: run that study first (see Makefile)")
        rec = run_one(run, cfg)
        print(
            run,
            rec["samples"],
            f"max rel diff vs comparison.csv {rec['max_rel_diff_vs_comparison_csv']:.1e}",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
