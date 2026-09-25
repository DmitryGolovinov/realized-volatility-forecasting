"""SYNTHETIC demonstration (no network): a HAR-type log-variance process run through the same
harness, smearing and combination code. Writes only to results/demo/."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rvf.combine import combine, qlike  # noqa: E402
from rvf.harness import refit_origins, run_asset  # noqa: E402

if __name__ == "__main__":
    rng = np.random.default_rng(0)
    n = 1600
    x = np.zeros(n)
    for t in range(22, n):
        x[t] = (
            -9
            + 0.4 * (x[t - 1] + 9)
            + 0.3 * (x[t - 5 : t].mean() + 9)
            + 0.2 * (x[t - 22 : t].mean() + 9)
            + rng.normal(0, 0.5)
        )
    df = pd.DataFrame({"rv_d": np.exp(x)})
    df["rv_w"] = df["rv_d"].rolling(5, min_periods=1).mean()
    df["rv_m"] = df["rv_d"].rolling(22, min_periods=1).mean()
    df["rv_n"], df["rv_p"] = df["rv_d"] * 0.5, df["rv_d"] * 0.5
    for c in ("rv_d", "rv_w", "rv_m", "rv_n", "rv_p"):
        df[f"log_{c}"] = np.log(df[c])
    for c in ("iv", "ea", "mom1w", "dolvol", "r_d", "r_w", "r_m", "rq_d"):
        df[c] = rng.normal(size=n)
    df["target"] = df["rv_d"].shift(-1)
    cfg = yaml.safe_load((ROOT / "configs" / "study.yaml").read_text())
    cfg["splits"] = dict(cfg["splits"], initial_train_rows=600, refit_every_rows=250)
    cfg["models"]["nn"] = dict(cfg["models"]["nn"], seeds=[0], max_epochs=30)
    cfg["models"]["lstm"] = dict(cfg["models"]["lstm"], seeds=[0], max_epochs=10)
    fc, _ = run_asset(df, cfg, ["HAR", "logHAR", "HARX", "RF", "NN", "LSTM"])
    comb, _ = combine(
        fc, ["HAR", "HARX", "RF", "NN", "LSTM"], refit_origins(cfg, len(df) - 1), 250, 250, 0.1
    )
    fc = fc.join(comb).dropna(subset=["QLIKEComb"])
    res = {
        m: float(qlike(fc["target"], fc[m]).mean() / qlike(fc["target"], fc["HAR"]).mean())
        for m in ["logHAR", "HARX", "RF", "NN", "LSTM", "EqualWeight", "QLIKEComb"]
    }
    out = ROOT / "results" / "demo"
    out.mkdir(parents=True, exist_ok=True)
    pd.Series(res, name="QLIKE_rel_HAR").to_csv(out / "summary.csv")
    (out / "README.txt").write_text("SYNTHETIC demo output; not market evidence.\n")
    print(pd.Series(res).round(3).to_string())
