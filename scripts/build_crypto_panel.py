"""Download (checksum-verified) Binance public spot 5-minute klines and build the crypto RV
panels: data/crypto/ (Generation 2) and data/crypto_g21/ (quarticity corrected on missing-bar
days). Public inputs only; needs no supplied stock file and no calendar recovery."""

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rvf.crypto import PANELS, build  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", nargs="+", choices=list(PANELS), default=list(PANELS))
    a = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "configs" / "g2_crypto_transfer.yaml").read_text())
    mans = build(ROOT, cfg, tuple(a.panels))
    print(json.dumps({p: m["qc"] for p, m in mans.items()}, indent=1))
