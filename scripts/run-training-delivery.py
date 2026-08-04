from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.training_delivery import write_training_delivery


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audita a coleta de treinamento e gera um pacote reproduzivel."
    )
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    result = write_training_delivery(
        model_root=arguments.model_root,
        output_dir=arguments.output_dir,
    )
    audit = result["audit"]
    print("PACOTE DE TREINAMENTO GERADO")
    print(f"OBS planejadas: {audit['planned_observations']}")
    print(f"OBS coletadas: {audit['collected_observations']}")
    print(f"OBS pendentes: {audit['pending_observations']}")
    print(f"Evidencias validas: {audit['valid_evidence_count']}")
    print(f"Smoke test exploratorio: {audit['research_pipeline_smoke_ready']}")
    print(f"Dataset pronto para treino: {audit['training_dataset_ready']}")
    print(f"PDF: {result['report_pdf']}")
    print(f"ZIP: {result['zip_path']}")
    print(f"SHA-256 do ZIP: {result['zip_sha256']}")
    print("Bloqueios:")
    print(json.dumps(audit["blockers"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
