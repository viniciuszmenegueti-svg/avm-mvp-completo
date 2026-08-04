from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Mapping, Sequence
from datetime import timezone
from decimal import Decimal
from html import escape
from pathlib import Path
from typing import Any

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
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.order import OrderResponse
from app.schemas.property import PropertyType
from app.schemas.valuation import ValuationResponse


FONT_DIRECTORY = Path(reportlab.__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("AVMBody", FONT_DIRECTORY / "Vera.ttf"))
pdfmetrics.registerFont(TTFont("AVMBold", FONT_DIRECTORY / "VeraBd.ttf"))

NAVY = colors.HexColor("#123B66")
BLUE = colors.HexColor("#1E5A88")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_GRAY = colors.HexColor("#F5F7F9")
MID_GRAY = colors.HexColor("#B8C5D1")
DARK_GRAY = colors.HexColor("#3B4652")
RED = colors.HexColor("#A61B1B")
AMBER = colors.HexColor("#8A5A00")
GREEN = colors.HexColor("#176B3A")

_PROPERTY_TYPE_LABELS = {
    PropertyType.APARTMENT: "Apartamento",
    PropertyType.HOUSE: "Casa",
    PropertyType.LAND: "Terreno",
}

_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


class _TrustedNumericCsvText(str):
    """Numeric output already typed and calculated before CSV serialization."""


def _identification_rows(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> list[tuple[str, str]]:
    return [
        ("Ordem de Serviço externa", _clean_text(order.external_order_id)),
        ("Ordem interna", order.internal_order_id),
        ("Identificador da avaliação", valuation.valuation_id),
        ("Status da ordem", order.status.value),
        ("Recebida em (UTC)", _format_datetime(order.received_at)),
        ("Calculada em (UTC)", _format_datetime(valuation.calculated_at)),
        ("Código de verificação dos dados", _verification_code(order, valuation)),
    ]


def _property_rows(order: OrderResponse) -> list[tuple[str, str]]:
    property_data = order.property
    address = f"{property_data.street}, {property_data.number}"
    if property_data.complement:
        address += f" — {property_data.complement}"
    return [
        ("Tipologia", _PROPERTY_TYPE_LABELS[property_data.property_type]),
        ("Endereço", _clean_text(address)),
        ("Bairro", _clean_text(property_data.neighborhood)),
        (
            "Município/UF",
            _clean_text(f"{property_data.city}/{property_data.state}"),
        ),
        ("CEP", property_data.postal_code),
        ("Código IBGE", property_data.city_ibge_code),
        ("Área privativa", _format_area(property_data.private_area_m2)),
        ("Área construída", _format_area(property_data.built_area_m2)),
        ("Área do terreno", _format_area(property_data.land_area_m2)),
        ("Quartos", _format_optional(property_data.bedrooms)),
        ("Banheiros", _format_optional(property_data.bathrooms)),
        ("Vagas de estacionamento", _format_optional(property_data.parking_spaces)),
    ]


def _valuation_rows(valuation: ValuationResponse) -> list[tuple[str, str]]:
    rows = [
        ("Valor estimado", _format_currency(valuation.estimated_value)),
        ("Limite inferior", _format_currency(valuation.minimum_value)),
        ("Limite superior", _format_currency(valuation.maximum_value)),
        ("Valor unitário", f"{_format_currency(valuation.price_per_m2)}/m²"),
        ("Área de referência", _format_area(valuation.reference_area_m2)),
        ("Índice de confiança", _format_decimal(valuation.confidence_score, 4)),
        ("Método", valuation.method.value),
        ("Versão do modelo", _clean_text(valuation.model_version)),
        ("Modo de execução", _clean_text(valuation.execution_mode)),
        (
            "Validade contratual",
            "SIM" if valuation.contractual_validity else "NÃO — HOMOLOGAÇÃO/TESTE",
        ),
    ]
    if valuation.statistical_model_id:
        rows.append(("ID do modelo estatístico", valuation.statistical_model_id))
    if valuation.model_artifact_sha256:
        rows.append(("SHA-256 do artefato", valuation.model_artifact_sha256))
    if valuation.dataset_sha256:
        rows.append(("SHA-256 do dataset", valuation.dataset_sha256))
    return rows


def _location_rows(order: OrderResponse) -> list[tuple[str, str]]:
    location = order.location_confirmation
    property_data = order.property
    address = (
        f"{property_data.street}, {property_data.number}, "
        f"{property_data.neighborhood}, {property_data.city}/{property_data.state}, "
        f"CEP {property_data.postal_code}"
    )
    is_test_evidence = location.confirmation_method == "HOMOLOGATION_TEST"
    if location.has_auditable_contract_coordinates and is_test_evidence:
        status = "ATENDE AO LIMITE DECLARADO - EVIDÊNCIA DE TESTE"
    elif location.has_auditable_contract_coordinates:
        status = "ATENDE AO LIMITE CONTRATUAL DECLARADO"
    else:
        status = "NÃO COMPROVADO"
    return [
        ("Endereço de referência", _clean_text(address)),
        ("Latitude", _format_coordinate(location.latitude)),
        ("Longitude", _format_coordinate(location.longitude)),
        ("Imprecisão declarada", _format_accuracy(location.accuracy_meters)),
        (
            "Limite contratual",
            (
                f"≤ {location.MAXIMUM_CONTRACT_ACCURACY_METERS:.0f} m "
                "(Anexo V do edital)"
            ),
        ),
        (
            "Método de confirmação",
            _format_optional(location.confirmation_method),
        ),
        (
            "Referência da evidência/fonte",
            _format_optional(location.evidence_reference),
        ),
        ("Verificado por", _format_optional(location.verified_by)),
        ("Situação", status),
    ]


def _location_compliance(order: OrderResponse) -> tuple[str, str, str]:
    location = order.location_confirmation
    requirement = "Coordenadas e precisão máxima de 50 m"
    if location.has_auditable_contract_coordinates:
        is_test_evidence = location.confirmation_method == "HOMOLOGATION_TEST"
        return (
            requirement,
            "PARCIAL" if is_test_evidence else "ATENDIDO",
            (
                f"Latitude {location.latitude:.6f}, longitude "
                f"{location.longitude:.6f}, imprecisão declarada de "
                f"{location.accuracy_meters:.2f} m, com método e evidência"
                + (
                    " exclusivamente sintéticos para homologação."
                    if is_test_evidence
                    else "."
                )
            ),
        )
    return (
        requirement,
        "NÃO VERIFICÁVEL",
        (
            "Faltam coordenadas, precisão de até 50 m, método, fonte/evidência "
            "ou identificação do verificador."
        ),
    )


def _model_compliance(valuation: ValuationResponse) -> tuple[str, str, str]:
    requirement = "Modelo aprovado e Fluxo Pareado concluído"
    if valuation.execution_mode == "HOMOLOGATION_SHADOW":
        return (
            requirement,
            "PARCIAL",
            (
                "Modelo OLS persistido e congelado para homologação técnica, com "
                "identificadores e SHA-256 do artefato e do dataset. A aprovação "
                "contratual, o Relatório do Modelo assinado e o Fluxo Pareado "
                "continuam pendentes."
            ),
        )
    if valuation.execution_mode == "CONTRACTUAL":
        return (
            requirement,
            "NÃO VERIFICÁVEL",
            (
                "O modo foi declarado como contratual, mas este relatório isolado "
                "não comprova a aceitação do Relatório do Modelo e do Fluxo Pareado."
            ),
        )
    return (
        requirement,
        "PENDENTE",
        "RULE_BASED_V1 não é modelo homologado para operação contratual.",
    )


def _compliance_rows(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> list[tuple[str, str, str]]:
    if valuation.execution_mode == "HOMOLOGATION_SHADOW":
        methodology_evidence = (
            "Modelo OLS congelado, coeficientes, contribuições, intervalo, "
            "versão e hashes estão registrados; a validação do RT permanece pendente."
        )
    else:
        methodology_evidence = (
            "Fatores e fundamentos estão registrados; o modelo atual é demonstrativo."
        )
    rows = [
        (
            "Valor e características do imóvel no relatório",
            "ATENDIDO",
            "Este documento apresenta o resultado e os campos usados pelo motor.",
        ),
        (
            "Exportação imediata em PDF e CSV pela API",
            "ATENDIDO",
            "Rotas dedicadas disponíveis para a ordem concluída.",
        ),
        (
            "Critérios, premissas e procedimentos verificáveis",
            "PARCIAL",
            methodology_evidence,
        ),
        (
            "RT de modelagem, mercado e emissão com registro profissional",
            "PENDENTE",
            "Identidades, vínculos e CREA/CAU não integram o cadastro atual.",
        ),
        (
            "Assinatura eletrônica do Responsável Técnico",
            "PENDENTE",
            "Não há certificado ICP-Brasil ou instrumento equivalente configurado.",
        ),
        _model_compliance(valuation),
        (
            "Matrícula e evidências documentais vinculadas",
            "NÃO VERIFICÁVEL",
            "O relatório não recebe referência persistida do documento da matrícula.",
        ),
    ]
    rows.insert(6, _location_compliance(order))
    return rows


def _rows(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> list[tuple[str, str]]:
    """Return the stable flat representation used by the CSV export."""
    rows: list[tuple[str, str]] = []
    for prefix, section in (
        ("identificacao", _identification_rows(order, valuation)),
        ("imovel", _property_rows(order)),
        ("geolocalizacao", _location_rows(order)),
        ("resultado", _valuation_rows(valuation)),
    ):
        rows.extend((f"{prefix}.{label}", value) for label, value in section)
    return rows


def build_valuation_csv(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    _write_csv_row(writer, ("campo", "valor"))
    for row in _rows(order, valuation):
        _write_csv_row(writer, row)
    for key, value in sorted(valuation.factors.items()):
        _write_csv_row(
            writer,
            (f"fator.{key}", _trusted_numeric_engine_value(value)),
        )
    for index, reason in enumerate(valuation.confidence_reasons, start=1):
        _write_csv_row(
            writer,
            (f"confianca.motivo.{index}", _clean_text(reason)),
        )
    for requirement, status, evidence in _compliance_rows(order, valuation):
        _write_csv_row(writer, (f"conformidade.{requirement}.status", status))
        _write_csv_row(writer, (f"conformidade.{requirement}.evidencia", evidence))
    return output.getvalue().encode("utf-8-sig")


def _write_csv_row(writer: Any, row: Sequence[object]) -> None:
    writer.writerow(tuple(_neutralize_csv_formula(cell) for cell in row))


def _neutralize_csv_formula(value: object) -> str:
    """Keep exported text inert when opened by spreadsheet applications."""
    if isinstance(value, _TrustedNumericCsvText):
        return str(value)

    text = _clean_text(str(value))
    first_significant = text.lstrip(" \t\r\n\v\f\u00a0\ufeff")
    has_control_prefix = bool(text) and (ord(text[0]) < 32 or ord(text[0]) == 127)
    if has_control_prefix or first_significant.startswith(_CSV_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def _trusted_numeric_engine_value(value: str) -> str:
    """Preserve genuine numeric motor output, including negative coefficients."""
    cleaned = _clean_text(value)
    try:
        number = Decimal(cleaned)
    except ArithmeticError:
        return cleaned
    if not number.is_finite():
        return cleaned
    return _TrustedNumericCsvText(cleaned)


def build_valuation_pdf(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> bytes:
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Relatório de teste AVM — {order.external_order_id}",
        author="AVM Imóveis API",
        subject="Relatório eletrônico demonstrativo de precificação imobiliária",
        creator="AVM Imóveis API",
        keywords=(
            "AVM, precificação imobiliária, relatório de teste, "
            "rastreabilidade, conformidade"
        ),
    )
    styles = _styles()
    if valuation.execution_mode == "HOMOLOGATION_SHADOW":
        limits_caption = (
            "Os limites apresentados são o intervalo calculado pela versão OLS "
            "congelada para homologação e não constituem campo de arbítrio "
            "aprovado por Responsável Técnico."
        )
        methodology_traceability = (
            "A versão, o dataset, os coeficientes, as contribuições, o intervalo "
            "e os hashes de integridade foram persistidos para reprodução do teste."
        )
        model_limitation = (
            "Não representa modelo estatístico aprovado para uso contratual nem "
            "Fluxo Pareado aceito."
        )
    else:
        limits_caption = (
            "Os limites apresentados são saídas do motor demonstrativo e não "
            "constituem campo de arbítrio aprovado por Responsável Técnico."
        )
        methodology_traceability = (
            "A rastreabilidade disponível nesta versão está limitada aos fatores "
            "e fundamentos devolvidos pelo próprio motor."
        )
        model_limitation = (
            "Não representa modelo estatístico aprovado nem Fluxo Pareado aceito."
        )
    story: list[Any] = [
        Paragraph("RELATÓRIO DE PRECIFICAÇÃO DE IMÓVEL", styles["AVMTitle"]),
        Paragraph(
            (
                "HOMOLOGAÇÃO SOMBRA — SEM VALIDADE CONTRATUAL"
                if valuation.execution_mode == "HOMOLOGATION_SHADOW"
                else "DOCUMENTO DE TESTE — NÃO VÁLIDO COMO LAUDO OFICIAL"
            ),
            styles["AVMWarning"],
        ),
        Paragraph(
            "Resultado eletrônico controlado gerado pela plataforma AVM. "
            "Os estados de conformidade deste documento fazem parte da evidência "
            "e não substituem validação ou assinatura profissional.",
            styles["AVMLead"],
        ),
        Spacer(1, 4 * mm),
        _section("1. Controle e rastreabilidade", styles),
        _key_value_table(_identification_rows(order, valuation), styles),
        Spacer(1, 5 * mm),
        _section("2. Identificação e características do imóvel", styles),
        _key_value_table(_property_rows(order), styles),
        Spacer(1, 5 * mm),
        _section("3. Resultado da precificação", styles),
        _result_table(_valuation_rows(valuation), styles),
        Spacer(1, 4 * mm),
        Paragraph(
            limits_caption,
            styles["AVMCaption"],
        ),
        _section("4. Metodologia, premissas e memória de cálculo", styles),
        Paragraph(
            "O cálculo foi produzido pelo método "
            f"<b>{escape(valuation.method.value)}</b>, versão "
            f"<b>{escape(_clean_text(valuation.model_version))}</b>. "
            f"{methodology_traceability}",
            styles["AVMBody"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("Fatores aplicados", styles["AVMSubheading"]),
        _mapping_table(valuation.factors, styles),
        Spacer(1, 5 * mm),
        Paragraph("Fundamentos do índice de confiança", styles["AVMSubheading"]),
        _numbered_reasons(valuation.confidence_reasons, styles),
        Spacer(1, 6 * mm),
        _section("5. Responsabilidade técnica e assinatura", styles),
        _status_table(
            [
                ("RT pelo modelo de precificação", "NÃO INFORMADO"),
                ("RT pela análise de mercado", "NÃO INFORMADO"),
                ("RT pela inserção de dados e emissão", "NÃO INFORMADO"),
                ("Registro CREA/CAU", "NÃO INFORMADO"),
                ("ART/RRT relacionada", "NÃO INFORMADA"),
                ("Assinatura eletrônica", "AUSENTE"),
            ],
            styles,
        ),
        Paragraph(
            "A ausência desses elementos impede o uso deste arquivo como laudo "
            "oficial, documento de crédito ou entrega contratual à CAIXA.",
            styles["AVMAlert"],
        ),
        _section("6. Geolocalização e conformidade", styles),
        Paragraph("6.1 Geolocalização declarada", styles["AVMSubheading"]),
        _key_value_table(_location_rows(order), styles),
        Spacer(1, 4 * mm),
        Paragraph(
            "As coordenadas devem resultar de fonte auditável e reproduzível. "
            "O relatório registra o endereço, a fonte, o método e a imprecisão "
            "declarados; ele não inventa coordenadas quando esses dados faltam.",
            styles["AVMCaption"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("6.2 Matriz de atendimento", styles["AVMSubheading"]),
        _compliance_table(_compliance_rows(order, valuation), styles),
        Spacer(1, 6 * mm),
        KeepTogether(
            [
                _section("7. Limitações e condições de uso", styles),
                _bullet_list(
                    [
                        "Uso restrito a desenvolvimento, testes e homologação técnica.",
                        model_limitation,
                        "Não contém assinatura eletrônica, ART/RRT ou certificação "
                        "digital.",
                        "A geolocalização reproduz a evidência declarada na OS e exige "
                        "validação da fonte pelo processo de homologação.",
                        "Não deve subsidiar crédito, garantia, contratação ou decisão "
                        "patrimonial.",
                        "O layout definitivo depende da especificação de integração "
                        "da CAIXA.",
                    ],
                    styles,
                ),
            ],
        ),
        Spacer(1, 6 * mm),
        Paragraph(
            "Referências de controle: Edital CR 012/2026 e Termo de Referência "
            "(saídas por API, rastreabilidade, identificação dos responsáveis e "
            "relatório do modelo); RF-006 e RN-004 da documentação de requisitos. "
            "A validação normativa definitiva cabe aos Responsáveis Técnicos "
            "e à CAIXA.",
            styles["AVMNote"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            "FIM DO DOCUMENTO DE TESTE",
            styles["AVMEnd"],
        ),
    ]
    document.build(
        story,
        onFirstPage=_page_decoration(order.external_order_id),
        onLaterPages=_page_decoration(order.external_order_id),
    )
    return output.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "AVMTitle": ParagraphStyle(
            "AVMTitle",
            parent=base["Title"],
            fontName="AVMBold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=NAVY,
            spaceAfter=3 * mm,
        ),
        "AVMWarning": ParagraphStyle(
            "AVMWarning",
            parent=base["BodyText"],
            fontName="AVMBold",
            fontSize=9.5,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.white,
            backColor=RED,
            borderPadding=6,
            spaceAfter=4 * mm,
        ),
        "AVMLead": ParagraphStyle(
            "AVMLead",
            parent=base["BodyText"],
            fontName="AVMBody",
            fontSize=9.2,
            leading=13,
            textColor=DARK_GRAY,
        ),
        "AVMSection": ParagraphStyle(
            "AVMSection",
            parent=base["Heading2"],
            fontName="AVMBold",
            fontSize=11.5,
            leading=15,
            textColor=NAVY,
            spaceAfter=3 * mm,
            keepWithNext=True,
        ),
        "AVMSubheading": ParagraphStyle(
            "AVMSubheading",
            parent=base["Heading3"],
            fontName="AVMBold",
            fontSize=9.5,
            leading=12,
            textColor=BLUE,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "AVMBody": ParagraphStyle(
            "AVMBody",
            parent=base["BodyText"],
            fontName="AVMBody",
            fontSize=8.5,
            leading=12,
            textColor=DARK_GRAY,
        ),
        "AVMCell": ParagraphStyle(
            "AVMCell",
            parent=base["BodyText"],
            fontName="AVMBody",
            fontSize=7.6,
            leading=10,
            textColor=DARK_GRAY,
        ),
        "AVMCellBold": ParagraphStyle(
            "AVMCellBold",
            parent=base["BodyText"],
            fontName="AVMBold",
            fontSize=7.6,
            leading=10,
            textColor=DARK_GRAY,
        ),
        "AVMCellHeader": ParagraphStyle(
            "AVMCellHeader",
            parent=base["BodyText"],
            fontName="AVMBold",
            fontSize=7.6,
            leading=10,
            textColor=colors.white,
        ),
        "AVMCaption": ParagraphStyle(
            "AVMCaption",
            parent=base["BodyText"],
            fontName="AVMBody",
            fontSize=7.2,
            leading=10,
            textColor=DARK_GRAY,
        ),
        "AVMAlert": ParagraphStyle(
            "AVMAlert",
            parent=base["BodyText"],
            fontName="AVMBold",
            fontSize=8,
            leading=11,
            textColor=RED,
            backColor=colors.HexColor("#FCECEC"),
            borderColor=colors.HexColor("#E8B5B5"),
            borderWidth=0.5,
            borderPadding=6,
            spaceBefore=4 * mm,
        ),
        "AVMNote": ParagraphStyle(
            "AVMNote",
            parent=base["BodyText"],
            fontName="AVMBody",
            fontSize=7.2,
            leading=10,
            textColor=DARK_GRAY,
            backColor=LIGHT_GRAY,
            borderPadding=6,
        ),
        "AVMEnd": ParagraphStyle(
            "AVMEnd",
            parent=base["BodyText"],
            fontName="AVMBold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=NAVY,
        ),
    }


def _section(text: str, styles: Mapping[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(escape(text), styles["AVMSection"])


def _paragraph(
    value: object,
    style: ParagraphStyle,
    *,
    bold: bool = False,
) -> Paragraph:
    text = escape(_clean_text(str(value)))
    if bold:
        text = f"<b>{text}</b>"
    return Paragraph(text, style)


def _key_value_table(
    rows: Sequence[tuple[str, str]],
    styles: Mapping[str, ParagraphStyle],
) -> Table:
    data = [
        [
            _paragraph("Campo", styles["AVMCellHeader"]),
            _paragraph("Valor", styles["AVMCellHeader"]),
        ],
        *[
            [
                _paragraph(label, styles["AVMCellBold"]),
                _paragraph(value, styles["AVMCell"]),
            ]
            for label, value in rows
        ],
    ]
    table = Table(data, colWidths=(58 * mm, 112 * mm), repeatRows=1)
    table.setStyle(_base_table_style())
    return table


def _result_table(
    rows: Sequence[tuple[str, str]],
    styles: Mapping[str, ParagraphStyle],
) -> Table:
    table = _key_value_table(rows, styles)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 1), (-1, 4), colors.HexColor("#EDF7F1")),
                ("TEXTCOLOR", (1, 1), (1, 4), GREEN),
                ("FONTNAME", (1, 1), (1, 4), "AVMBold"),
            ]
        )
    )
    return table


def _mapping_table(
    values: Mapping[str, str],
    styles: Mapping[str, ParagraphStyle],
) -> Table | Paragraph:
    if not values:
        return Paragraph("Nenhum fator informado pelo motor.", styles["AVMBody"])
    rows = [(key, _clean_text(value)) for key, value in sorted(values.items())]
    return _key_value_table(rows, styles)


def _numbered_reasons(
    reasons: Sequence[str],
    styles: Mapping[str, ParagraphStyle],
) -> Paragraph:
    if not reasons:
        return Paragraph("Nenhum fundamento informado pelo motor.", styles["AVMBody"])
    content = "<br/>".join(
        f"{index}. {escape(_clean_text(reason))}"
        for index, reason in enumerate(reasons, start=1)
    )
    return Paragraph(content, styles["AVMBody"])


def _status_table(
    rows: Sequence[tuple[str, str]],
    styles: Mapping[str, ParagraphStyle],
) -> Table:
    data = [
        [
            _paragraph("Papel ou controle", styles["AVMCellHeader"]),
            _paragraph("Situação", styles["AVMCellHeader"]),
        ],
        *[
            [
                _paragraph(label, styles["AVMCell"]),
                _paragraph(status, styles["AVMCellBold"]),
            ]
            for label, status in rows
        ],
    ]
    table = Table(data, colWidths=(112 * mm, 58 * mm), repeatRows=1)
    table.setStyle(_base_table_style())
    table.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (1, 1), (1, -1), RED),
                ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#FCECEC")),
            ]
        )
    )
    return table


def _compliance_table(
    rows: Sequence[tuple[str, str, str]],
    styles: Mapping[str, ParagraphStyle],
) -> Table:
    data = [
        [
            _paragraph("Requisito", styles["AVMCellHeader"]),
            _paragraph("Situação", styles["AVMCellHeader"]),
            _paragraph("Evidência ou pendência", styles["AVMCellHeader"]),
        ],
        *[
            [
                _paragraph(requirement, styles["AVMCell"]),
                _paragraph(status, styles["AVMCellBold"]),
                _paragraph(evidence, styles["AVMCell"]),
            ]
            for requirement, status, evidence in rows
        ],
    ]
    table = Table(
        data,
        colWidths=(60 * mm, 30 * mm, 80 * mm),
        repeatRows=1,
    )
    table.setStyle(_base_table_style())
    for index, (_, status, _) in enumerate(rows, start=1):
        color = GREEN if status == "ATENDIDO" else AMBER
        background = (
            colors.HexColor("#EDF7F1")
            if status == "ATENDIDO"
            else colors.HexColor("#FFF7E3")
        )
        table.setStyle(
            TableStyle(
                [
                    ("TEXTCOLOR", (1, index), (1, index), color),
                    ("BACKGROUND", (1, index), (1, index), background),
                ]
            )
        )
    return table


def _base_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, MID_GRAY),
            ("BACKGROUND", (0, 1), (-1, -1), LIGHT_GRAY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _bullet_list(
    items: Sequence[str],
    styles: Mapping[str, ParagraphStyle],
) -> KeepTogether:
    paragraphs: list[Any] = []
    for item in items:
        paragraphs.extend(
            [
                Paragraph(f"• {escape(_clean_text(item))}", styles["AVMBody"]),
                Spacer(1, 1.5 * mm),
            ]
        )
    return KeepTogether(paragraphs)


def _page_decoration(external_order_id: str) -> Any:
    safe_order_id = _clean_text(external_order_id)

    def decorate(canvas: Canvas, document: SimpleDocTemplate) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(0.7)
        canvas.line(17 * mm, height - 11 * mm, width - 17 * mm, height - 11 * mm)
        canvas.setFont("AVMBody", 6.8)
        canvas.setFillColor(DARK_GRAY)
        canvas.drawString(17 * mm, 9 * mm, f"OS: {safe_order_id}")
        canvas.drawRightString(
            width - 17 * mm,
            9 * mm,
            f"Documento de teste • Página {document.page}",
        )
        canvas.restoreState()

    return decorate


def _verification_code(
    order: OrderResponse,
    valuation: ValuationResponse,
) -> str:
    payload = {
        "order": order.model_dump(mode="json"),
        "valuation": valuation.model_dump(mode="json"),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def _format_currency(value: Decimal) -> str:
    formatted = f"{value:,.2f}"
    localized = formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return _TrustedNumericCsvText(f"R$ {localized}")


def _format_decimal(value: Decimal, places: int) -> str:
    return _TrustedNumericCsvText(f"{value:.{places}f}".replace(".", ","))


def _format_area(value: object | None) -> str:
    if value is None:
        return "Não informado"
    decimal_value = Decimal(str(value))
    return _TrustedNumericCsvText(f"{_format_decimal(decimal_value, 2)} m²")


def _format_optional(value: object | None) -> str:
    return "Não informado" if value is None else str(value)


def _format_coordinate(value: float | None) -> str:
    if value is None:
        return "Não informado"
    return _TrustedNumericCsvText(f"{value:.6f}°")


def _format_accuracy(value: float | None) -> str:
    if value is None:
        return "Não informada"
    return _TrustedNumericCsvText(f"{value:.2f} m".replace(".", ","))


def _format_datetime(value: Any) -> str:
    return value.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")


def _clean_text(value: str) -> str:
    if "Ãƒ" not in value and "Ã‚" not in value:
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
