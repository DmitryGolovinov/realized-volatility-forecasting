"""Run the crypto protocol transfer. `--mode final` scores the reserved 2024-01..2026-08 rows
(exposed on 2026-09-24; any later final run is a disclosed recomputation, not a new test)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rvf.transfer import run_crypto  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["dev", "final"], default="dev")
    ap.add_argument(
        "--panel",
        choices=["crypto", "crypto_g21"],
        default="crypto",
        help="crypto: Generation-2 panel; crypto_g21: quarticity corrected on missing-bar days",
    )
    ap.add_argument(
        "--i-understand-this-is-the-final-evaluation", action="store_true", dest="confirm_final"
    )
    a = ap.parse_args()
    if a.mode == "final" and not a.confirm_final:
        sys.exit("final evaluation needs --i-understand-this-is-the-final-evaluation")
    rec = run_crypto(ROOT, a.mode, a.panel)
    print(rec["evaluation"], round(rec["runtime_seconds"], 1), "s")
