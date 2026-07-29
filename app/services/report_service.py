from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from datetime import timezone
from pathlib import Path

import reportlab  # type: ignore[import-untyped]
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import (  # type: ignore[import-untyped]
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.order import OrderResponse
from app.schemas.valuation import ValuationResponse


FONT_DIRECTORY = Path(reportlab.__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("AVMBody", FONT_DIRECTORY / "Vera.ttf"))
pdfmetrics.registerFont(TTFont("AVMBold", FONT_DIRECTORY / "VeraBd.ttf"))


def _rows(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> list[tuple[str, str]]:
    return [
        ("Ordem externa", _clean_text(order.external_order_id)),
        ("Ordem interna", order.internal_order_id),
        ("Código IBGE", order.property.city_ibge_code),
        (
            "Município/UF",
            _clean_text(f"{order.property.city}/{order.property.state}"),
        ),
        ("Tipologia", order.property.property_type.value),
        ("Método", valuation.method.value),
        ("Versão do modelo", valuation.model_version),
        ("Valor estimado (R$)", f"{valuation.estimated_value:.2f}"),
        ("Limite inferior (R$)", f"{valuation.minimum_value:.2f}"),
        ("Limite superior (R$)", f"{valuation.maximum_value:.2f}"),
        ("Valor unitário (R$/m²)", f"{valuation.price_per_m2:.2f}"),
        ("Área de referência (m²)", f"{valuation.reference_area_m2:.2f}"),
        ("Índice de confiança", f"{valuation.confidence_score:.4f}"),
        (
            "Calculado em",
            valuation.calculated_at.astimezone(timezone.utc).isoformat(),
        ),
    ]


def build_valuation_csv(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("campo", "valor"))
    writer.writerows(_rows(order, valuation))
    for key, value in sorted(valuation.factors.items()):
        writer.writerow((f"fator.{key}", value))
    for index, reason in enumerate(valuation.confidence_reasons, start=1):
        writer.writerow((f"confianca.motivo.{index}", _clean_text(reason)))
    return output.getvalue().encode("utf-8-sig")


def build_valuation_pdf(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> bytes:
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Relatório de Precificação {order.external_order_id}",
        author="AVM Imóveis API",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AVMTitle",
        parent=styles["Title"],
        fontName="AVMBold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#123B66"),
        spaceAfter=8 * mm,
    )
    note_style = ParagraphStyle(
        "AVMNote",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#444444"),
        spaceBefore=5 * mm,
    )
    styles["BodyText"].fontName = "AVMBody"
    styles["Heading2"].fontName = "AVMBold"

    story = [
        Paragraph("RELATÓRIO DE PRECIFICAÇÃO DE IMÓVEL", title_style),
        Paragraph(
            "Resultado eletrônico rastreável gerado pela plataforma AVM.",
            styles["BodyText"],
        ),
        Spacer(1, 5 * mm),
    ]
    data = [["Campo", "Valor"], *[list(row) for row in _rows(order, valuation)]]
    table = Table(data, colWidths=(58 * mm, 106 * mm), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B66")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "AVMBold"),
                ("FONTNAME", (0, 1), (0, -1), "AVMBold"),
                ("FONTNAME", (1, 1), (-1, -1), "AVMBody"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C5D1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7F9FB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)

    if valuation.factors:
        story.extend(
            [
                Spacer(1, 6 * mm),
                Paragraph("Memória de cálculo - fatores", styles["Heading2"]),
                Paragraph(
                    _mapping_as_text(valuation.factors),
                    styles["BodyText"],
                ),
            ]
        )
    if valuation.confidence_reasons:
        story.extend(
            [
                Spacer(1, 4 * mm),
                Paragraph("Fundamentos do índice de confiança", styles["Heading2"]),
                Paragraph(
                    "<br/>".join(
                        f"{index}. {_clean_text(reason)}"
                        for index, reason in enumerate(
                            valuation.confidence_reasons, start=1
                        )
                    ),
                    styles["BodyText"],
                ),
            ]
        )

    story.append(
        Paragraph(
            "A emissão deste arquivo não constitui homologação do modelo, "
            "assinatura do Responsável Técnico, ART/RRT ou certificação digital. "
            "O modo RULE_BASED_V1 é demonstrativo e deve permanecer bloqueado "
            "em produção contratual.",
            note_style,
        )
    )
    document.build(story)
    return output.getvalue()


def _mapping_as_text(values: Mapping[str, str]) -> str:
    return "<br/>".join(
        f"<b>{_clean_text(key)}:</b> {_clean_text(value)}"
        for key, value in sorted(values.items())
    )


def _clean_text(value: str) -> str:
    if "Ã" not in value and "Â" not in value:
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
