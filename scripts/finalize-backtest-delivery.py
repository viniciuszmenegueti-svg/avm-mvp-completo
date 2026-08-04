"""Create a SHA-256 delivery manifest after PDF and XLSX generation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
FILES = (
    REPOSITORY / ".audit/backtests/vivareal-rj/SHA256-MANIFEST.json",
    REPOSITORY / ".audit/backtests/vivareal-rj/backtest-model-artifact.json",
    REPOSITORY / ".audit/backtests/vivareal-rj/backtest-results.csv",
    REPOSITORY / ".audit/backtests/vivareal-rj/backtest-summary.json",
    REPOSITORY / ".audit/backtests/vivareal-rj/validation-holdout.csv",
    REPOSITORY / "output/pdf/RELATORIO-BACKTEST-EXPLORATORIO-VIVAREAL-RJ.pdf",
    REPOSITORY / "outputs/backtest-vivareal-rj/BACKTEST-EXPLORATORIO-VIVAREAL-RJ.xlsx",
    REPOSITORY
    / "outputs/backtest-vivareal-rj/TEMPLATE-BASE-VALIDACAO-INDEPENDENTE.xlsx",
)
OUTPUT = REPOSITORY / "outputs/backtest-vivareal-rj/SHA256-DELIVERY-MANIFEST.json"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    missing = [path for path in FILES if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing delivery artifacts: " + ", ".join(map(str, missing))
        )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "EXPLORATORY_DELIVERY",
        "formal_homologation": False,
        "files": [
            {
                "path": str(path.relative_to(REPOSITORY)),
                "size_bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
            for path in FILES
        ],
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Delivery manifest: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
