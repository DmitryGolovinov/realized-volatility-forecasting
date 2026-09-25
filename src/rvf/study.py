"""Predeclared RV study: five assets, pooled vs asset-specific, combinations, evaluation."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import yaml

from .combine import combine, qlike, robust_combinations
from .data import check_no_reserved_rows, file_hashes, guard, load_panel
from .evaluate import by_block, by_period, compare
from .harness import SPECS, refit_origins, run_asset, run_pooled
from .manifest import environment, git_commit, sha256_file, tree_hash, write_manifest

PACKAGES = ("numpy", "pandas", "scikit-learn", "torch")
INDIVIDUAL = ["HAR", "HARX", "RF", "NN", "LSTM"]
ROBUST = ["Median", "Trimmed"] + [f"EW_wo_{m}" for m in INDIVIDUAL]


def run(root: Path, mode: str = "dev") -> dict:
    import torch

    root = Path(root)
    tic = time.perf_counter()
    cfg = yaml.safe_load((root / "configs" / "study.yaml").read_text())
    torch.set_num_threads(cfg.get("threads", 2))
    cfg["models"]["threads"] = cfg.get("threads", 2)
    assets = cfg["data"]["assets"]
    fs = cfg["splits"]["final_start_row"]
    panel = guard(load_panel(root / cfg["data"]["source_dir"], assets), fs, mode == "final")
    if mode == "dev":
        check_no_reserved_rows(panel, fs)
    out = root / "results" / mode
    out.mkdir(parents=True, exist_ok=True)

    models = list(SPECS)
    fcs, logs = {}, {}
    key = sha256_file(root / "configs" / "study.yaml")[:8] + "_" + tree_hash(root)[:8]
    for a in assets:
        cache = out / f"forecasts_{a}_{key}.parquet"
        if cache.exists():  # resumable: reuse a completed asset run with the same config
            fcs[a] = pd.read_parquet(cache)
            continue
        fcs[a], logs[a] = run_asset(panel[a], cfg, models, cfg.get("seed", 0))
        fcs[a].to_parquet(cache)
        (out / f"fitlog_{a}.json").write_text(json.dumps(logs[a], indent=1, default=str))
        print(a, "done", round(time.perf_counter() - tic, 1), flush=True)
    pooled_cache = out / f"forecasts_pooled_{key}.parquet"
    if pooled_cache.exists():
        pooled = pd.read_parquet(pooled_cache)
        for a in assets:
            for c in pooled.columns:
                if c.startswith(a + "::"):
                    fcs[a][c.split("::", 1)[1]] = pooled[c]
    else:
        pooled_out, plog = run_pooled(panel, cfg, ["logHAR", "RF", "NN"], cfg.get("seed", 0))
        frame = {}
        for a in assets:
            for c in pooled_out[a].columns:
                if c.endswith("_pooled"):
                    fcs[a][c] = pooled_out[a][c]
                    frame[f"{a}::{c}"] = pooled_out[a][c]
        pd.DataFrame(frame).to_parquet(pooled_cache)
        (out / "fitlog_pooled.json").write_text(json.dumps(plog, indent=1))

    comb_logs, tables, blocks, desc, years = {}, [], [], [], []
    dm = root / "data" / "date_map.csv"
    dates = pd.read_csv(dm).set_index("row")["date"] if dm.exists() else None
    for a in assets:
        fc = fcs[a]
        origins = refit_origins(cfg, int(fc.index.max()) + 1)
        comb, clog = combine(
            fc,
            INDIVIDUAL,
            origins,
            cfg["splits"]["refit_every_rows"],
            cfg["combination"]["min_history_rows"],
            cfg["combination"]["grid_step"],
        )
        comb_logs[a] = clog
        fc = fc.join(comb).join(robust_combinations(fc, INDIVIDUAL))
        fcs[a] = fc
        # Headline comparisons on the rows where every forecast (incl. combinations) exists.
        common = fc.dropna(subset=["QLIKEComb", "BestPrior"])
        if mode == "final":  # final evaluation: score only the reserved rows
            common = common[common.index >= fs]
        cols = INDIVIDUAL + [
            "logHAR",
            "EqualWeight",
            "QLIKEComb",
            "BestPrior",
            "logHAR_pooled",
            "RF_pooled",
            "NN_pooled",
            "HARX_macro",
            "RF_macro",
        ] + ROBUST
        t = compare(common, cols, "HAR", cfg)
        t.insert(0, "asset", a)
        tables.append(t)
        b = by_block(common, cols, "HAR", cfg["evaluation"]["block_rows"])
        b.insert(0, "asset", a)
        blocks.append(b)
        if dates is not None:  # recovered calendar (data/date_map.csv, scripts/recover_dates.py)
            yr = by_period(common, dates, cols, "HAR")
            yr.insert(0, "asset", a)
            years.append(yr)
        # Descriptive ex-post slice: top decile of realized next-day RV (NOT a regime forecast).
        hi = common[common["target"] >= common["target"].quantile(0.9)]
        for m in cols:
            desc.append(
                {
                    "asset": a,
                    "model": m,
                    "slice": "top_decile_realized_rv",
                    "QLIKE_rel_HAR": float(
                        qlike(hi["target"], hi[m]).mean() / qlike(hi["target"], hi["HAR"]).mean()
                    ),
                }
            )
        fc.to_parquet(out / f"forecasts_{a}_with_combinations.parquet")
    table = pd.concat(tables, ignore_index=True)
    table.to_csv(out / "comparison.csv", index=False)
    pd.concat(blocks, ignore_index=True).to_csv(out / "blocks.csv", index=False)
    if years:
        pd.concat(years, ignore_index=True).to_csv(out / "calendar_years.csv", index=False)
    pd.DataFrame(desc).to_csv(out / "descriptive_high_rv_slice.csv", index=False)
    (out / "combination_log.json").write_text(json.dumps(comb_logs, indent=1))

    # Pooled vs asset-specific: paired QLIKE ratio on identical rows.
    pv = []
    for a in assets:
        c = fcs[a].dropna(subset=["QLIKEComb"])
        if mode == "final":
            c = c[c.index >= fs]
        for m in ("logHAR", "RF", "NN"):
            ls = qlike(c["target"], c[m]).mean()
            lp = qlike(c["target"], c[f"{m}_pooled"]).mean()
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

    rows = {
        a: {
            "first_row": int(
                max(fcs[a].dropna(subset=["QLIKEComb"]).index.min(), fs if mode == "final" else 0)
            ),
            "last_row": int(fcs[a].index.max()),
        }
        for a in assets
    }
    record = {
        "study": "realized-volatility-forecasting",
        "mode": mode,
        "evaluation_rows": rows,
        "reserved_final_start_row": fs,
        "aapl_final_block_previously_viewed": True,
        "data_sha256": file_hashes(root / cfg["data"]["source_dir"], assets),
        "config_sha256": sha256_file(root / "configs" / "study.yaml"),
        "source_tree_sha256": tree_hash(root),
        "git_commit": git_commit(root),
        "runtime_seconds": time.perf_counter() - tic,
        "environment": environment(PACKAGES),
        "command": f"python scripts/run_study.py --mode {mode}",
        "seed": cfg.get("seed", 0),
        "calendar": json.loads((root / "data" / "date_map_provenance.json").read_text())
        if (root / "data" / "date_map_provenance.json").exists()
        else None,
    }
    outs = [
        out / f
        for f in (
            "comparison.csv",
            "blocks.csv",
            "pooled_vs_specific.csv",
            "combination_log.json",
            "descriptive_high_rv_slice.csv",
        )
    ] + ([out / "calendar_years.csv"] if years else [])
    write_manifest(out / "manifest.json", record, outs)
    return record
