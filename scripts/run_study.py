"""Run the realized-variance study. `--mode final` is reserved for the final evaluation."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rvf.study import run  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["dev", "final"], default="dev")
    ap.add_argument(
        "--i-understand-this-is-the-final-evaluation", action="store_true", dest="confirm_final"
    )
    a = ap.parse_args()
    if a.mode == "final" and not a.confirm_final:
        sys.exit("final evaluation needs --i-understand-this-is-the-final-evaluation")
    rec = run(ROOT, a.mode)
    print(rec["evaluation_rows"], round(rec["runtime_seconds"], 1), "s")
