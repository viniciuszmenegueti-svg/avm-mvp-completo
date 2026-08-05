"""Audit and package a market-training collection without inventing evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import reportlab  # type: ignore[import-untyped]
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4, landscape  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


FONT_DIRECTORY = Path(reportlab.__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("AVMTrainingBody", FONT_DIRECTORY / "Vera.ttf"))
pdfmetrics.registerFont(TTFont("AVMTrainingBold", FONT_DIRECTORY / "VeraBd.ttf"))
NAVY = colors.HexColor("#174A70")
BLUE = colors.HexColor("#2477A9")
LIGHT_BLUE = colors.HexColor("#EAF3F8")
LIGHT_GRAY = colors.HexColor("#F3F5F7")
RED = colors.HexColor("#9B2C2C")
MID_GRAY = colors.HexColor("#C4CFD7")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing CSV header.")
        return list(reader)


def _verify_evidence_manifest(directory: Path) -> tuple[bool, list[str]]:
    manifest_path = directory / "SHA256-MANIFEST.csv"
    if not manifest_path.is_file():
        return False, ["EVIDENCE_MANIFEST_MISSING"]
    reasons: list[str] = []
    manifest = read_csv(manifest_path)
    if not manifest:
        reasons.append("EVIDENCE_MANIFEST_EMPTY")
    for row in manifest:
        file_path = directory / row.get("arquivo", "")
        if not file_path.is_file():
            reasons.append(f"MANIFEST_FILE_MISSING:{file_path.name}")
            continue
        if str(file_path.stat().st_size) != row.get("tamanho_bytes", ""):
            reasons.append(f"MANIFEST_SIZE_MISMATCH:{file_path.name}")
        if sha256(file_path) != row.get("sha256", "").upper():
            reasons.append(f"MANIFEST_HASH_MISMATCH:{file_path.name}")
    return not reasons, reasons


def audit_training_collection(model_root: Path) -> dict[str, Any]:
    root = model_root.resolve()
    plan_dir = root / "04-plano-nova-coleta"
    collection_dir = root / "05-coleta-treinamento"
    queue_path = collection_dir / "FILA-COLETA-360-OBS.json"
    queue_manifest_path = collection_dir / "FILA-COLETA-360-OBS.sha256.json"
    master_path = collection_dir / "REGISTRO-MESTRE-COLETA.csv"
    plan_path = plan_dir / "PLANO-COLETA-TREINAMENTO-RJ.csv"
    required = (queue_path, queue_manifest_path, master_path, plan_path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue_manifest = json.loads(queue_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(queue, list) or not queue:
        raise ValueError("The observation queue must be a non-empty list.")
    queue_ids = [str(row.get("observation_id", "")) for row in queue]
    if not all(queue_ids) or len(queue_ids) != len(set(queue_ids)):
        raise ValueError("The observation queue contains empty or duplicate IDs.")
    if queue_manifest.get("sha256", "").upper() != sha256(queue_path):
        raise ValueError("The observation queue hash does not match its manifest.")
    if int(queue_manifest.get("row_count", -1)) != len(queue):
        raise ValueError("The observation queue row count does not match its manifest.")

    master = read_csv(master_path)
    master_ids = [row.get("observation_id", "") for row in master]
    if len(master_ids) != len(set(master_ids)):
        raise ValueError("The master collection register contains duplicate IDs.")
    unknown = sorted(set(master_ids) - set(queue_ids))
    if unknown:
        raise ValueError(f"Master observations are absent from the queue: {unknown}")
    master_by_id = {row["observation_id"]: row for row in master}
    plan = read_csv(plan_path)

    observations: list[dict[str, Any]] = []
    valid_evidence_count = 0
    completeness_pending_count = 0
    location_pending_count = 0
    source_counts: Counter[str] = Counter()
    for queued in queue:
        observation_id = str(queued["observation_id"])
        record = master_by_id.get(observation_id)
        reasons: list[str] = []
        evidence_valid = False
        evidence_pdf = ""
        if record is None:
            reasons.append("NOT_COLLECTED")
        else:
            source_counts[record.get("source_portal", "UNKNOWN") or "UNKNOWN"] += 1
            relative = record.get("evidence_file", "")
            evidence_path = collection_dir / relative
            evidence_pdf = str(evidence_path)
            manifest_valid, manifest_reasons = _verify_evidence_manifest(
                evidence_path.parent
            )
            reasons.extend(manifest_reasons)
            if (
                not evidence_path.is_file()
                or evidence_path.read_bytes()[:5] != b"%PDF-"
            ):
                reasons.append("EVIDENCE_PDF_INVALID")
            elif sha256(evidence_path) != record.get("evidence_sha256", "").upper():
                reasons.append("EVIDENCE_PDF_HASH_MISMATCH")
            else:
                evidence_valid = manifest_valid
            if evidence_valid:
                valid_evidence_count += 1
            if record.get("collection_status") != "READY_FOR_REVIEW":
                reasons.append("DATA_COMPLETENESS_PENDING")
                completeness_pending_count += 1
            location_fields = (
                record.get("latitude", ""),
                record.get("longitude", ""),
                record.get("location_accuracy_meters", ""),
            )
            if not all(value.strip() for value in location_fields):
                reasons.append("LOCATION_VALIDATION_PENDING")
                location_pending_count += 1
        observations.append(
            {
                "observation_id": observation_id,
                "collection_cell_id": queued.get("collection_cell_id", ""),
                "preferred_portal": queued.get("preferred_portal", ""),
                "registered_portal": record.get("source_portal", "") if record else "",
                "status": record.get("collection_status", "NOT_COLLECTED")
                if record
                else "NOT_COLLECTED",
                "evidence_valid": evidence_valid,
                "evidence_pdf": evidence_pdf,
                "reason_codes": "|".join(dict.fromkeys(reasons)),
            }
        )

    collected_by_cell = Counter(row.get("collection_cell_id", "") for row in master)
    cells: list[dict[str, Any]] = []
    completed_cells = 0
    for row in plan:
        target = int(row["meta_bruta"])
        collected = collected_by_cell[row["celula_id"]]
        completed = collected >= target
        completed_cells += int(completed)
        cells.append(
            {
                "cell_id": row["celula_id"],
                "region": row["regiao"],
                "neighborhood": row["bairro"],
                "area_band": row["faixa_area"],
                "target": target,
                "collected": collected,
                "pending": max(0, target - collected),
                "complete": completed,
            }
        )

    planned_count = len(queue)
    collected_count = len(master)
    blockers: list[str] = []
    if collected_count != planned_count:
        blockers.append("PLANNED_OBSERVATIONS_INCOMPLETE")
    if completed_cells != len(cells):
        blockers.append("COLLECTION_CELLS_INCOMPLETE")
    if valid_evidence_count != collected_count:
        blockers.append("EVIDENCE_INTEGRITY_FAILURE")
    if completeness_pending_count:
        blockers.append("DATA_COMPLETENESS_PENDING")
    if location_pending_count:
        blockers.append("LOCATION_VALIDATION_PENDING")
    blockers.extend(
        [
            "RT_VARIABLE_POLICY_PENDING",
            "RT_OFFER_ADJUSTMENT_PENDING",
            "INDEPENDENT_VALIDATION_PENDING",
            "FORMAL_HOMOLOGATION_PENDING",
        ]
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_root": str(root),
        "classification": "TRAINING_PIPELINE_READINESS",
        "formal_homologation": False,
        "planned_observations": planned_count,
        "collected_observations": collected_count,
        "pending_observations": planned_count - collected_count,
        "valid_evidence_count": valid_evidence_count,
        "cell_count": len(cells),
        "completed_cell_count": completed_cells,
        "data_completeness_pending_count": completeness_pending_count,
        "location_pending_count": location_pending_count,
        "source_counts": dict(sorted(source_counts.items())),
        "research_pipeline_smoke_ready": (
            collected_count >= 3 and valid_evidence_count == collected_count
        ),
        "training_dataset_ready": not blockers,
        "blockers": blockers,
        "observations": observations,
        "cells": cells,
        "integrity_tests": {
            "queue_hash": "PASS",
            "queue_unique_ids": "PASS",
            "master_unique_ids": "PASS",
            "evidence_manifests_checked": collected_count,
            "evidence_manifests_valid": valid_evidence_count,
        },
    }


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "TrainingTitle",
            parent=sample["Title"],
            fontName="AVMTrainingBold",
            fontSize=18,
            leading=22,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "Heading": ParagraphStyle(
            "TrainingHeading",
            parent=sample["Heading2"],
            fontName="AVMTrainingBold",
            fontSize=11,
            leading=14,
            textColor=NAVY,
            spaceBefore=4,
            spaceAfter=5,
        ),
        "Body": ParagraphStyle(
            "TrainingBody",
            parent=sample["BodyText"],
            fontName="AVMTrainingBody",
            fontSize=8,
            leading=11,
        ),
        "Warning": ParagraphStyle(
            "TrainingWarning",
            parent=sample["BodyText"],
            fontName="AVMTrainingBold",
            fontSize=9,
            leading=12,
            textColor=RED,
            backColor=colors.HexColor("#FCE8E6"),
            borderPadding=7,
        ),
        "Cell": ParagraphStyle(
            "TrainingCell",
            parent=sample["BodyText"],
            fontName="AVMTrainingBody",
            fontSize=5.8,
            leading=6.8,
        ),
        "Header": ParagraphStyle(
            "TrainingHeader",
            parent=sample["BodyText"],
            fontName="AVMTrainingBold",
            fontSize=5.8,
            leading=6.8,
            textColor=colors.white,
        ),
    }


def _table(rows: list[list[Any]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.3, MID_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def build_training_readiness_pdf(audit: dict[str, Any], output: Path) -> None:
    styles = _styles()
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output),
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm,
        title="Relatorio de prontidao do treinamento AVM",
        author="Plataforma AVM",
    )

    def p(value: object, style: str = "Cell") -> Paragraph:
        return Paragraph(str(value), styles[style])

    summary_rows = [
        [p("Indicador", "Header"), p("Resultado", "Header")],
        [p("OBS planejadas"), p(audit["planned_observations"])],
        [p("OBS coletadas"), p(audit["collected_observations"])],
        [p("OBS pendentes"), p(audit["pending_observations"])],
        [p("Evidencias validas"), p(audit["valid_evidence_count"])],
        [
            p("Celulas completas"),
            p(f"{audit['completed_cell_count']}/{audit['cell_count']}"),
        ],
        [
            p("Smoke test exploratorio"),
            p("APROVADO" if audit["research_pipeline_smoke_ready"] else "BLOQUEADO"),
        ],
        [
            p("Dataset pronto para treino"),
            p("SIM" if audit["training_dataset_ready"] else "NAO"),
        ],
        [p("Homologacao formal"), p("NAO")],
    ]
    blockers = "<br/>".join(f"- {item}" for item in audit["blockers"])
    story: list[Any] = [
        p("RELATORIO DE PRONTIDAO DO TREINAMENTO AVM", "Title"),
        Spacer(1, 3 * mm),
        Paragraph(
            "Resultado: o pipeline esta tecnicamente testado, mas o "
            "treinamento definitivo permanece bloqueado. Observacoes sem "
            "anuncio real ou evidencia nao foram preenchidas artificialmente.",
            styles["Warning"],
        ),
        Spacer(1, 4 * mm),
        p("1. Resumo executivo", "Heading"),
        _table(summary_rows, [75 * mm, 75 * mm]),
        Spacer(1, 4 * mm),
        p("2. Bloqueios vigentes", "Heading"),
        Paragraph(blockers, styles["Body"]),
        Spacer(1, 4 * mm),
        p("3. Testes de integridade", "Heading"),
        _table(
            [
                [p("Teste", "Header"), p("Resultado", "Header")],
                *[
                    [p(key), p(value)]
                    for key, value in audit["integrity_tests"].items()
                ],
            ],
            [95 * mm, 55 * mm],
        ),
        PageBreak(),
        p("4. Situacao por celula", "Heading"),
    ]
    cell_rows = [
        [
            p(value, "Header")
            for value in (
                "Celula",
                "Regiao",
                "Bairro",
                "Faixa",
                "Meta",
                "Coletadas",
                "Pendentes",
                "Completa",
            )
        ]
    ]
    for row in audit["cells"]:
        cell_rows.append(
            [
                p(row["cell_id"]),
                p(row["region"]),
                p(row["neighborhood"]),
                p(row["area_band"]),
                p(row["target"]),
                p(row["collected"]),
                p(row["pending"]),
                p("SIM" if row["complete"] else "NAO"),
            ]
        )
    story.extend(
        [
            _table(
                cell_rows,
                [
                    27 * mm,
                    25 * mm,
                    39 * mm,
                    38 * mm,
                    18 * mm,
                    22 * mm,
                    22 * mm,
                    20 * mm,
                ],
            ),
            PageBreak(),
            p("5. Observacoes ja coletadas", "Heading"),
        ]
    )
    collected_rows = [
        [
            p(value, "Header")
            for value in (
                "OBS",
                "Celula",
                "Portal",
                "Status",
                "PDF valido",
                "Pendencias",
            )
        ]
    ]
    for row in audit["observations"]:
        if row["status"] == "NOT_COLLECTED":
            continue
        collected_rows.append(
            [
                p(row["observation_id"]),
                p(row["collection_cell_id"]),
                p(row["registered_portal"]),
                p(row["status"]),
                p("SIM" if row["evidence_valid"] else "NAO"),
                p(row["reason_codes"]),
            ]
        )
    story.extend(
        [
            _table(
                collected_rows, [42 * mm, 27 * mm, 25 * mm, 43 * mm, 22 * mm, 82 * mm]
            ),
            Spacer(1, 5 * mm),
            p("6. Conclusao", "Heading"),
            Paragraph(
                "Os PDFs coletados e seus manifestos sao validos para pesquisa "
                "exploratoria. O sistema deve continuar recusando treino "
                "definitivo, homologacao e uso contratual ate que todas as "
                "celulas estejam completas, a localizacao seja comprovada, a "
                "politica de variaveis e o tratamento de ofertas sejam "
                "aprovados pelo RT e a validacao independente seja concluida.",
                styles["Body"],
            ),
        ]
    )
    document.build(story)


def write_training_delivery(*, model_root: Path, output_dir: Path) -> dict[str, Any]:
    audit = audit_training_collection(model_root)
    output = output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence_output = output / "evidencias-coletadas"
    evidence_output.mkdir(exist_ok=True)

    audit_json = output / "training-readiness.json"
    audit_json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    observation_csv = output / "observation-audit.csv"
    with observation_csv.open("w", encoding="utf-8-sig", newline="") as target:
        fields = [
            "observation_id",
            "collection_cell_id",
            "preferred_portal",
            "registered_portal",
            "status",
            "evidence_valid",
            "evidence_pdf",
            "reason_codes",
        ]
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit["observations"])
    cell_csv = output / "cell-status.csv"
    with cell_csv.open("w", encoding="utf-8-sig", newline="") as target:
        fields = [
            "cell_id",
            "region",
            "neighborhood",
            "area_band",
            "target",
            "collected",
            "pending",
            "complete",
        ]
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit["cells"])

    for row in audit["observations"]:
        if row["evidence_valid"]:
            source = Path(row["evidence_pdf"])
            shutil.copy2(
                source,
                evidence_output / f"{row['observation_id']}-evidencia.pdf",
            )

    report_pdf = output / "RELATORIO-PRONTIDAO-TREINAMENTO-AVM.pdf"
    build_training_readiness_pdf(audit, report_pdf)
    readme = output / "LEIA-ME.txt"
    readme.write_text(
        "PACOTE DE TREINAMENTO AVM\n"
        "=========================\n\n"
        "Classificacao: pipeline de treinamento exploratorio.\n"
        "Treinamento definitivo: BLOQUEADO.\n"
        "Homologacao formal: NAO.\n\n"
        "Este pacote preserva as evidencias reais existentes e documenta todas as\n"
        "pendencias. Nao contem observacoes, precos ou PDFs inventados.\n",
        encoding="utf-8",
    )

    manifest_files = sorted(
        path
        for path in output.rglob("*")
        if path.is_file()
        and path.name not in {"SHA256-MANIFEST.json"}
        and path.suffix.lower() != ".zip"
        and not path.name.endswith(".zip.sha256.txt")
    )
    manifest = {
        "generated_at": audit["generated_at"],
        "formal_homologation": False,
        "files": [
            {
                "path": path.relative_to(output).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in manifest_files
        ],
    }
    manifest_path = output / "SHA256-MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    zip_path = output.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output))
    zip_hash = sha256(zip_path)
    sidecar = zip_path.with_suffix(zip_path.suffix + ".sha256.txt")
    sidecar.write_text(f"{zip_hash}  {zip_path.name}\n", encoding="ascii")
    return {
        "audit": audit,
        "output_dir": str(output),
        "report_pdf": str(report_pdf),
        "zip_path": str(zip_path),
        "zip_sha256": zip_hash,
        "manifest_path": str(manifest_path),
    }
