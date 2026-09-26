"""How much did the Generation-2.1 quarticity correction change the crypto results?

Compares results/crypto_<mode>/ (Generation 2 panel) with results/crypto_g21_<mode>/ (span-aware
quarticity on days with missing bars) for mode in dev, final: mean relative QLIKE per model and
every paired contrast. Writes results/g21_vs_g2.json. Reads saved artifacts only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rvf.manifest import sha256_file, tree_hash  # noqa: E402


def main() -> int:
    out = {"source_tree_sha256": tree_hash(ROOT), "modes": {}}
    for mode in ("dev", "final"):
        a, b = ROOT / "results" / f"crypto_{mode}", ROOT / "results" / f"crypto_g21_{mode}"
        if not (a / "paired_losses.csv").exists() or not (b / "paired_losses.csv").exists():
            sys.exit(f"run scripts/paired_losses.py crypto_{mode} crypto_g21_{mode} first")
        sa = pd.read_csv(a / "summary_by_model.csv").set_index("model")["QLIKE_rel_HAR"]
        sb = pd.read_csv(b / "summary_by_model.csv").set_index("model")["QLIKE_rel_HAR"]
        d = (sb - sa).dropna()
        pa, pb = pd.read_csv(a / "paired_losses.csv"), pd.read_csv(b / "paired_losses.csv")
        m = pa.merge(pb, on=["sample", "contrast"], suffixes=("_g2", "_g21"))

        def verdict(r, s):
            lo, hi = r[f"diff_lo_{s}"], r[f"diff_hi_{s}"]
            return "a_lower" if hi < 0 else ("b_lower" if lo > 0 else "unresolved")

        m["verdict_g2"] = m.apply(lambda r: verdict(r, "g2"), axis=1)
        m["verdict_g21"] = m.apply(lambda r: verdict(r, "g21"), axis=1)
        out["modes"][mode] = {
            "max_abs_change_mean_rel_qlike": float(d.abs().max()),
            "model_with_max_change": str(d.abs().idxmax()),
            "mean_rel_qlike_change": {k: float(v) for k, v in d.items()},
            "max_abs_change_paired_diff": float((m["diff_g21"] - m["diff_g2"]).abs().max()),
            "contrasts_with_changed_verdict": m.loc[
                m["verdict_g2"] != m["verdict_g21"], ["sample", "contrast"]
            ].to_dict("records"),
            "sign_changes": int((np.sign(m["diff_g2"]) != np.sign(m["diff_g21"])).sum()),
            "inputs_sha256": {
                str(p.relative_to(ROOT)): sha256_file(p)
                for p in (a / "paired_losses.csv", b / "paired_losses.csv")
            },
        }
    (ROOT / "results" / "g21_vs_g2.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: {kk: v[kk] for kk in list(v)[:2]} for k, v in out["modes"].items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
