"""Generation 2 (c): the frozen Generation-1 protocol on the dated crypto RV panel.

Model set, hyperparameters, seeds, row-clock refits, inner validation, smearing, combination
rule and evaluation are taken unchanged from configs/study.yaml. Only the data and the feature
lists come from configs/g2_crypto_transfer.yaml (no implied volatility, earnings or macro data
exist for these assets). Rows >= the first 2024 day are reserved unless ``mode == "final"``.

``panel="crypto"`` is the Generation-2 panel (results/crypto_<mode>/); ``panel="crypto_g21"``
is the Generation-2.1 data correction of the quarticity feature on days with missing bars
(results/crypto_g21_<mode>/, see rvf.crypto). Nothing else differs between the two runs.
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import pandas as pd
import yaml

from .combine import combine, qlike, robust_combinations
from .crypto import PANELS, load_crypto_panel
from .data import ReservedSampleError, guard
from .evaluate import by_block, by_period, compare
from .harness import refit_origins, run_asset, run_pooled
from .manifest import environment, git_commit, sha256_file, tree_hash, write_manifest

INDIVIDUAL = ["HAR", "HARX", "RF", "NN", "LSTM"]
ROBUST = ["Median", "Trimmed"] + [f"EW_wo_{m}" for m in INDIVIDUAL]
PACKAGES = ("numpy", "pandas", "scikit-learn", "torch")


def transfer_config(root: Path) -> tuple[dict, dict]:
    base = yaml.safe_load((Path(root) / "configs" / "study.yaml").read_text())
    t = yaml.safe_load((Path(root) / "configs" / "g2_crypto_transfer.yaml").read_text())
    cfg = copy.deepcopy(base)
    cfg["features"] = {**base["features"], **t["features"]}
    for k in ("initial_train_rows", "refit_every_rows", "inner_validation_frac"):
        if t["splits"][k] != base["splits"][k]:
            raise ValueError(f"transfer config changes the frozen split parameter {k}")
    return cfg, t


def run_crypto(root: Path, mode: str = "dev", panel: str = "crypto") -> dict:
    import torch

    root = Path(root)
    run_name = "crypto" if panel == "crypto" else panel
    tic = time.perf_counter()
    cfg, t = transfer_config(root)
    torch.set_num_threads(cfg.get("threads", 2))
    cfg["models"]["threads"] = cfg.get("threads", 2)
    panel_name = panel
    panel = load_crypto_panel(root, t, allow_final=mode == "final", panel=panel_name)
    assets = list(panel)
    dates = panel[assets[0]]["date"]
    for a in assets:
        if not panel[a]["date"].equals(dates):
            raise ValueError("assets do not share one calendar")
    fs = int((pd.to_datetime(dates) < pd.Timestamp(t["splits"]["final_start"])).sum())
    if mode != "final":
        # the loader already dropped reserved rows; the last development target is unresolved
        for a in assets:
            panel[a].loc[panel[a].index[-1], "target"] = float("nan")
    else:
        panel = guard(panel, fs, True)
    if mode != "final" and any(int(df.index.max()) >= fs for df in panel.values()):
        raise ReservedSampleError("reserved crypto rows present in a development run")
    out = root / "results" / f"{run_name}_{mode}"
    out.mkdir(parents=True, exist_ok=True)
    models = ["HAR", "logHAR", "HARX", "RF", "NN", "LSTM"]
    key = "_".join(
        h[:8]
        for h in (
            sha256_file(root / "configs" / "g2_crypto_transfer.yaml"),
            sha256_file(root / "configs" / "study.yaml"),
            sha256_file(root / "data" / panel_name / "manifest.json"),
            tree_hash(root),
        )
    )
    fcs = {}
    for a in assets:
        cache = out / f"forecasts_{a}_{key}.parquet"
        if cache.exists():
            fcs[a] = pd.read_parquet(cache)
            continue
        fcs[a], log = run_asset(panel[a], cfg, models, cfg.get("seed", 0))
        fcs[a].to_parquet(cache)
        (out / f"fitlog_{a}.json").write_text(json.dumps(log, indent=1, default=str))
        print(a, "done", round(time.perf_counter() - tic, 1), flush=True)
    pooled_cache = out / f"forecasts_pooled_{key}.parquet"
    if pooled_cache.exists():
        pooled = pd.read_parquet(pooled_cache)
    else:
        po, plog = run_pooled(panel, cfg, ["logHAR", "RF", "NN"], cfg.get("seed", 0))
        pooled = pd.DataFrame(
            {f"{a}::{c}": po[a][c] for a in assets for c in po[a].columns if c.endswith("_pooled")}
        )
        pooled.to_parquet(pooled_cache)
        (out / "fitlog_pooled.json").write_text(json.dumps(plog, indent=1))
    for a in assets:
        for c in pooled.columns:
            if c.startswith(a + "::"):
                fcs[a][c.split("::", 1)[1]] = pooled[c]
    cols = (
        INDIVIDUAL
        + [
            "logHAR",
            "EqualWeight",
            "QLIKEComb",
            "BestPrior",
            "logHAR_pooled",
            "RF_pooled",
            "NN_pooled",
        ]
        + ROBUST
    )
    tables, blocks, years, clogs = [], [], [], {}
    for a in assets:
        fc = fcs[a]
        origins = refit_origins(cfg, int(fc.index.max()) + 1)
        comb, clogs[a] = combine(
            fc,
            INDIVIDUAL,
            origins,
            cfg["splits"]["refit_every_rows"],
            cfg["combination"]["min_history_rows"],
            cfg["combination"]["grid_step"],
        )
        fc = fc.join(comb).join(robust_combinations(fc, INDIVIDUAL))
        common = fc.dropna(subset=["QLIKEComb", "BestPrior"])
        if mode == "final":
            common = common[common.index >= fs]
        tb = compare(common, cols, "HAR", cfg)
        tb.insert(0, "asset", a)
        tables.append(tb)
        b = by_block(common, cols, "HAR", cfg["evaluation"]["block_rows"])
        b.insert(0, "asset", a)
        blocks.append(b)
        yr = by_period(common, dates, cols, "HAR")
        yr.insert(0, "asset", a)
        years.append(yr)
        fc.assign(date=dates.reindex(fc.index)).to_parquet(
            out / f"forecasts_{a}_with_combinations.parquet"
        )
        fcs[a] = fc
    table = pd.concat(tables, ignore_index=True)
    table.to_csv(out / "comparison.csv", index=False)
    pd.concat(blocks, ignore_index=True).to_csv(out / "blocks.csv", index=False)
    pd.concat(years, ignore_index=True).to_csv(out / "calendar_years.csv", index=False)
    (out / "combination_log.json").write_text(json.dumps(clogs, indent=1))
    pv = []
    for a in assets:
        c = fcs[a].dropna(subset=["QLIKEComb"])
        if mode == "final":
            c = c[c.index >= fs]
        for m in ("logHAR", "RF", "NN"):
            ls, lp = qlike(c["target"], c[m]).mean(), qlike(c["target"], c[f"{m}_pooled"]).mean()
            pv.append(
                {
                    "asset": a,
                    "model": m,
                    "QLIKE_specific": float(ls),
                    "QLIKE_pooled": float(lp),
                    "pooled_over_specific": float(lp / ls),
                }
            )
    pd.DataFrame(pv).to_csv(out / "pooled_vs_specific.csv", index=False)
    first = {
        a: int(max(fcs[a].dropna(subset=["QLIKEComb"]).index.min(), fs if mode == "final" else 0))
        for a in assets
    }
    record = {
        "study": "realized-volatility-forecasting / crypto protocol transfer",
        "mode": mode,
        "assets": assets,
        "evaluation": {
            a: {
                "first_row": first[a],
                "first_date": str(dates.iloc[first[a]]),
                "last_row": int(fcs[a].index.max()),
                "last_date": str(dates.iloc[int(fcs[a].index.max())]),
            }
            for a in assets
        },
        **({} if panel_name == "crypto" else {"panel": panel_name, "rq": PANELS[panel_name]}),
        "reserved_final_start": t["splits"]["final_start"],
        "reserved_final_start_row": fs,
        "data_manifest_sha256": sha256_file(root / "data" / panel_name / "manifest.json"),
        "config_sha256": sha256_file(root / "configs" / "study.yaml"),
        "transfer_config_sha256": sha256_file(root / "configs" / "g2_crypto_transfer.yaml"),
        "source_tree_sha256": tree_hash(root),
        "git_commit": git_commit(root),
        "runtime_seconds": time.perf_counter() - tic,
        "environment": environment(PACKAGES),
        "command": f"python scripts/run_crypto.py --mode {mode}"
        + ("" if panel_name == "crypto" else f" --panel {panel_name}"),
    }
    outs = [
        out / f
        for f in (
            "comparison.csv",
            "blocks.csv",
            "calendar_years.csv",
            "pooled_vs_specific.csv",
            "combination_log.json",
        )
    ]
    write_manifest(out / "manifest.json", record, outs)
    return record
