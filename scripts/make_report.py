"""Tables and figures for the RV note, rebuilt from results/<run>/ artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ORDER = [
    "HAR",
    "logHAR",
    "HARX",
    "RF",
    "NN",
    "LSTM",
    "EqualWeight",
    "QLIKEComb",
    "BestPrior",
    "logHAR_pooled",
    "RF_pooled",
    "NN_pooled",
    "HARX_macro",
    "RF_macro",
    "Median",
    "Trimmed",
    "EW_wo_HAR",
    "EW_wo_HARX",
    "EW_wo_RF",
    "EW_wo_NN",
    "EW_wo_LSTM",
]
KEY = ["HARX", "NN", "EqualWeight", "QLIKEComb", "BestPrior", "Median", "NN_pooled"]


def main(run: str = "dev") -> None:
    res = ROOT / "results" / run
    man = json.loads((res / "manifest.json").read_text())
    comp = pd.read_csv(res / "comparison.csv")
    blocks = pd.read_csv(res / "blocks.csv")
    pooled = pd.read_csv(res / "pooled_vs_specific.csv")
    comb = json.loads((res / "combination_log.json").read_text())
    is_dev = run.split("_")[-1] == "dev"
    crypto = run.startswith("crypto")
    if crypto:
        rows = next(iter(man["evaluation"].values()))
        span = f"{rows['first_date'][:10]} to {rows['last_date'][:10]}"
    else:
        rows = man["evaluation_rows"]["AAPL"]
        dm = ROOT / "data" / "date_map.csv"
        dates = pd.read_csv(dm).set_index("row")["date"] if dm.exists() else None
        span = (
            f"{dates[rows['first_row']]} to {dates[rows['last_row']]} (recovered calendar)"
            if dates is not None
            else f"rows {rows['first_row']}-{rows['last_row']}"
        )
    order = [m for m in ORDER if m in set(comp["model"])]
    fig_dir = ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    rel = comp.pivot(index="model", columns="asset", values="QLIKE_rel_HAR").loc[order]
    fig, ax = plt.subplots(figsize=(9.6, 4.4), dpi=150)
    models = [
        m
        for m in (
            "logHAR",
            "HARX",
            "RF",
            "NN",
            "NN_pooled",
            "LSTM",
            "EqualWeight",
            "Median",
            "Trimmed",
            "QLIKEComb",
            "BestPrior",
        )
        if m in set(blocks["model"])
    ]
    data = [blocks[blocks["model"] == m]["QLIKE_rel"].to_numpy() for m in models]
    ax.boxplot(
        data,
        tick_labels=models,
        showfliers=False,
        widths=0.5,
        medianprops={"color": "#2a78d6", "lw": 1.6},
    )
    ax.axhline(1.0, color="#8a8984", lw=0.8)
    ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    ax.set_ylabel("QLIKE relative to HAR (per 252-row block)")
    ax.set_title(
        f"Stability across assets and blocks, {span}\n"
        f"({'crypto transfer, ' if crypto else ''}"
        f"{'development' if is_dev else 'final rows only'}; outliers not drawn)",
        fontsize=10,
        loc="left",
    )
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(fig_dir / f"blocks_{run}.png")
    plt.close(fig)

    wts = pd.DataFrame({a: v[-1]["weights"] for a, v in comb.items()}).T
    mean = (
        comp.groupby("model")[
            ["QLIKE_rel_HAR", "MSE_rel_HAR", "MAE_rel_HAR", "bias_rel", "MZ_a", "MZ_b"]
        ]
        .mean()
        .loc[order]
    )
    summary = mean.copy()
    summary["assets_below_HAR"] = (rel < 1).sum(axis=1)
    summary.reset_index().to_csv(res / "summary_by_model.csv", index=False)
    stat = comp.pivot(index="model", columns="asset", values="QLIKE_gain_tstat_nw").loc[order]
    lines = [
        f"# {'Development' if is_dev else 'Final'} results ({run})",
        "",
        f"Generated from `results/{run}/` (config `{man['config_sha256'][:12]}`, source tree "
        f"`{man['source_tree_sha256'][:12]}`). Common evaluation rows {rows['first_row']}-"
        f"{rows['last_row']} ({span}) for every asset and model. "
        + (
            "Crypto protocol transfer: eight Binance spot assets, 5-minute realized variance, "
            "the frozen stock protocol without retuning (no implied volatility, earnings or "
            "macro features). "
            if crypto
            else "Refits follow the frozen 252-row clock. "
        )
        + "Target: next-day realized variance.",
        "",
        "Status: "
        + (
            "development sample."
            if is_dev
            else "disclosed recomputation of the exposed crypto final (see above)."
            if man.get("panel") == "crypto_g21"
            else (
                "crypto final, not used for any design decision in this repository and "
                "evaluated once with the frozen procedure on 2026-09-24; now exposed. Its BTC "
                "and ETH data overlap the separate Binance study of this portfolio."
                if crypto
                else "archival stock final (supplied, undated files; calendar inferred), not "
                "used for any design decision and evaluated once with the frozen procedure on "
                "2026-09-24; the AAPL rows of this block were viewed in the original exercise, "
                "and the pooled network's refits use them."
            )
        ),
        "",
        "## QLIKE relative to HAR by asset",
        "",
        rel.to_markdown(floatfmt=".3f"),
        "",
        "## Newey-West t-statistic of the QLIKE gain over HAR (positive = better than HAR)",
        "",
        stat.to_markdown(floatfmt=".2f"),
        "",
        "## Average over assets: relative losses, bias, Mincer-Zarnowitz (RV = a + b f)",
        "",
        mean.to_markdown(floatfmt=".3f"),
        "",
        "## Pooled over asset-specific QLIKE (same rows; < 1 = pooled better)",
        "",
        pooled.pivot(index="model", columns="asset", values="pooled_over_specific").to_markdown(
            floatfmt=".3f"
        ),
        "",
        "## Latest data-driven combination weights (grid on the simplex, prior OOS history)",
        "",
        wts.to_markdown(floatfmt=".2f"),
        "",
        f"![blocks](figures/blocks_{run}.png)",
    ]
    cy = res / "calendar_years.csv"
    if cy.exists():
        y = pd.read_csv(cy)
        y = y[y["model"].isin(KEY)].groupby(["year", "model"])["QLIKE_rel"].mean().unstack()
        lines += [
            "",
            "## QLIKE relative to HAR by calendar year (mean over assets)",
            "",
            y[[m for m in KEY if m in y.columns]].to_markdown(floatfmt=".3f"),
        ]
    lines += paired_sections(res)
    if man.get("panel") == "crypto_g21":
        base = "crypto_" + run.split("_")[-1]
        lines[2:2] = [
            f"Generation 2.1 data-correction rerun of `results/{base}/`: realized quarticity "
            "uses the span-aware scaling on days with missing 5-minute bars "
            "(`data/crypto_g21/`); models, hyperparameters, seeds, splits and evaluation are "
            + (
                "unchanged. The final rows were already exposed; this is a disclosed "
                "recomputation, not a new test."
                if not is_dev
                else "unchanged."
            ),
            "",
        ]
    (ROOT / "reports" / f"results_{run}.md").write_text("\n".join(lines) + "\n")
    print("wrote report")


def _ci(v: float, lo: float, hi: float, f: str) -> str:
    return f"{v:{f}} [{lo:{f}}, {hi:{f}}]"


def paired_sections(res: Path) -> list[str]:
    """Raw paired losses with joint (all assets per date) block-bootstrap intervals."""
    pl, ml = res / "paired_losses.csv", res / "model_losses.csv"
    if not (pl.exists() and ml.exists()):
        return []
    pm = json.loads((res / "paired_losses_manifest.json").read_text())
    c, m = pd.read_csv(pl), pd.read_csv(ml)
    ma = m[m["sample"] == "all"]
    bt = pm["bootstrap"]
    tab = pd.DataFrame(
        {
            "model": ma["model"],
            "raw QLIKE": ma["QLIKE"].map(lambda v: f"{v:.4f}"),
            "difference vs HAR": [
                _ci(r.diff_vs_HAR, r.diff_lo, r.diff_hi, ".4f") for r in ma.itertuples()
            ],
            "pooled ratio vs HAR": [
                _ci(r.pooled_ratio_vs_HAR, r.pooled_ratio_lo, r.pooled_ratio_hi, ".3f")
                for r in ma.itertuples()
            ],
            "mean of asset ratios": [
                _ci(r.mean_ratio_vs_HAR, r.mean_ratio_lo, r.mean_ratio_hi, ".3f")
                for r in ma.itertuples()
            ],
        }
    )

    def contrasts(df: pd.DataFrame) -> str:
        n = int(df["n_assets"].iloc[0])
        return pd.DataFrame(
            {
                "contrast": df["contrast"],
                "a vs b": df["a"] + " vs " + df["b"],
                "raw QLIKE a / b": [f"{r.loss_a:.4f} / {r.loss_b:.4f}" for r in df.itertuples()],
                "difference a - b": [
                    _ci(r.diff, r.diff_lo, r.diff_hi, "+.4f") for r in df.itertuples()
                ],
                "NW t": df["nw_t"].map(lambda v: f"{v:.2f}"),
                "pooled ratio": [
                    _ci(r.pooled_ratio, r.pooled_ratio_lo, r.pooled_ratio_hi, ".3f")
                    for r in df.itertuples()
                ],
                f"assets a lower (of {n})": df["assets_a_lower"],
            }
        ).to_markdown(index=False)

    out = [
        "",
        "## Raw losses with cross-asset dependence preserved",
        "",
        f"Panel means over {pm['samples']['all']['dates']} dates x {len(pm['assets'])} assets. "
        f"Intervals: 95% moving-block bootstrap over DATES (block {bt['block_dates']}, "
        f"{bt['n_boot']} draws), every asset of a drawn date kept together. Ratios are shown "
        "as the pooled ratio of mean losses and as the mean of per-asset ratios (the form used "
        "in the tables above).",
        "",
        tab.to_markdown(index=False),
        "",
        "## Paired contrasts: where does the gain come from?",
        "",
        "Negative difference: the first forecast has the lower loss. `MeanMemberLoss` is the "
        "average loss of the five equal-weight members, not a forecast. NW t: Newey-West "
        f"({pm['hac_lags']} lags) t-statistic of the cross-asset mean daily difference.",
        "",
        contrasts(c[c["sample"] == "all"]),
    ]
    cov = c[c["sample"] == "target_coverage_ge_95pct"]
    if len(cov):
        k = pm["samples"]["target_coverage_ge_95pct"]["dates_excluded"]
        out += [
            "",
            "### Sensitivity: without target days below 95% bar coverage",
            "",
            f"{k} evaluation date(s) excluded (any asset with fewer than 274 of 288 bars on "
            "the target day); the same forecasts are rescored.",
            "",
            contrasts(cov) if k else "No evaluation date is affected; the table is unchanged.",
        ]
    return out


if __name__ == "__main__":
    main(*(sys.argv[1:] or []))
