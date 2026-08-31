from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a SupplyTwin disruption scenario")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(json.loads(args.scenario.read_text()))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "supply-chain-decision.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"receipt_sha256": report["receipt_sha256"], "selected_action": report["selected_action"]["name"] if report["selected_action"] else None}, indent=2))


if __name__ == "__main__":
    main()
