"""PDF evidence for an exploratory AVM backtest."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from html import escape
from typing import Any

import reportlab  # type: ignore[import-untyped]
from reportlab.graphics.shapes import Circle, Drawing, Line, String  # type: ignore[import-untyped]
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from engine.validation.backtest import BacktestResult, BacktestSummary


FONT_DIRECTORY = (
    __import__("pathlib").Path(reportlab.__file__).resolve().parent / "fonts"
)
pdfmetrics.registerFont(TTFont("AVMBacktestBody", FONT_DIRECTORY / "Vera.ttf"))
pdfmetrics.registerFont(TTFont("AVMBacktestBold", FONT_DIRECTORY / "VeraBd.ttf"))

NAVY = colors.HexColor("#123B66")
BLUE = colors.HexColor("#1E6F9F")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_GRAY = colors.HexColor("#F4F6F8")
RED = colors.HexColor("#A61B1B")
GREEN = colors.HexColor("#26734D")


def build_backtest_report_pdf(
    *,
    summary: BacktestSummary,
    results: list[BacktestResult],
    metadata: dict[str, Any],
    segment_rows: list[dict[str, Any]],
) -> bytes:
    """Build a standalone PDF that never claims formal approval."""

    classification = str(metadata.get("classification", "INTERNAL_HOLDOUT_EXPLORATORY"))
    warning = str(
        metadata.get(
            "warning",
            "HOLDOUT INTERNO - SEM INDEPENDENCIA EXTERNA - SEM VALIDADE CONTRATUAL",
        )
    )
    introductory_notice = str(
        metadata.get(
            "introductory_notice",
            "Este documento mede a capacidade de generalizacao em uma parcela "
            "separada deterministicamente antes do ajuste. Os valores de "
            "referencia continuam sendo precos pedidos do mesmo portal. Portanto, "
            "o resultado nao homologa o modelo, nao substitui valor de mercado "
            "validado e nao dispensa a aprovacao do Responsavel Tecnico.",
        )
    )
    limitations = metadata.get(
        "limitations",
        (
            "A validacao usa holdout interno da mesma fonte e nao e "
            "independente externamente.",
            "O valor de referencia e preco pedido, sem tratamento do fator "
            "oferta ou confirmacao do valor de mercado pelo RT.",
            "A concentracao geografica e de fonte limita a representatividade.",
            "A cobertura do IC80 observada nao define, por si, um limiar de aceite.",
            "A politica formal precisa declarar amostra minima, tolerancias, "
            "estratos e tratamento de perdas antes da execucao externa.",
            "A base externa deve permanecer congelada, possuir evidencias e "
            "hashes e nao pode participar do treino ou da selecao de variaveis.",
            "A aprovacao final depende de parecer, identificacao e assinatura "
            "do Responsavel Tecnico e dos ritos exigidos pela contratacao.",
        ),
    )
    subject = str(
        metadata.get(
            "subject",
            "Validacao interna por holdout, sem validade contratual",
        )
    )
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title="Backtest exploratorio AVM",
        author="AVM Imoveis API",
        subject=subject,
    )
    styles = _styles()
    story: list[Any] = [
        Paragraph("BACKTEST EXPLORATORIO DO MODELO AVM", styles["Title"]),
        Paragraph(escape(warning), styles["Warning"]),
        Paragraph(escape(introductory_notice), styles["Lead"]),
        Spacer(1, 4 * mm),
        _heading("1. Identificacao e rastreabilidade", styles),
        _key_value_table(
            [
                ("Classificacao", classification),
                ("Cidade / tipologia", str(metadata["scope"])),
                ("Variavel de referencia", "asking_price_brl (preco pedido)"),
                (
                    "Fonte",
                    str(metadata.get("source", "VivaReal - exportacoes reconciliadas")),
                ),
                ("Registros de treino", str(metadata["training_count"])),
                ("Registros de validacao", str(metadata["validation_count"])),
                ("Semente da divisao", str(metadata["split_seed"])),
                (
                    "Sobreposicao treino-validacao",
                    str(metadata.get("overlap_count", "0")),
                ),
                ("SHA-256 da base auditada", str(metadata["source_audit_sha256"])),
                ("SHA-256 do treino", str(metadata["training_sha256"])),
                ("SHA-256 da validacao", str(metadata["validation_sha256"])),
                ("Homologacao formal", "NAO"),
            ],
            styles,
        ),
        PageBreak(),
        _heading("2. Indicadores globais", styles),
        _key_value_table(
            [
                ("Observacoes conclusivas", str(summary.conclusive_count)),
                (
                    "Aprovadas somente no criterio exploratorio",
                    str(summary.approved_exploratory_count),
                ),
                (
                    "Reprovadas somente no criterio exploratorio",
                    str(summary.rejected_exploratory_count),
                ),
                ("Inconclusivas", str(summary.inconclusive_count)),
                ("MAE", _money(summary.mean_absolute_error_brl)),
                ("RMSE", _money(summary.root_mean_squared_error_brl)),
                (
                    "Mediana do erro percentual absoluto",
                    _percent(summary.median_absolute_percentage_error),
                ),
                (
                    "Vies percentual medio",
                    _percent(summary.mean_signed_percentage_error),
                ),
                (
                    "Cobertura empirica do IC80",
                    _percent(summary.ic80_empirical_coverage),
                ),
                (
                    "Taxa de aprovacao exploratoria",
                    _percent(summary.exploratory_approval_rate),
                ),
            ],
            styles,
        ),
        Paragraph(
            "Criterio exploratorio por linha: imovel dentro do dominio de treino, "
            "amplitude do IC80 da estimativa media de ate 50% e valor de referencia "
            "contido no IC80. Esses criterios nao sao uma politica de aceite "
            "contratual.",
            styles["Note"],
        ),
        Spacer(1, 5 * mm),
        _heading("3. Valor de referencia versus estimativa", styles),
        _scatter(results),
        PageBreak(),
        _heading("4. Desempenho por segmento", styles),
        _segment_table(segment_rows, styles),
        Spacer(1, 6 * mm),
        _heading("5. Maiores erros percentuais absolutos", styles),
        _worst_results_table(results, styles),
        PageBreak(),
        _heading("6. Limitacoes e requisitos pendentes", styles),
        *[Paragraph(f"- {escape(str(item))}", styles["Body"]) for item in limitations],
        Spacer(1, 6 * mm),
        _heading("7. Conclusao", styles),
        Paragraph(
            "O pipeline de backtest, os calculos, a tabela por imovel e a "
            "rastreabilidade estao prontos para testes. Este resultado e somente "
            "exploratorio. Para homologacao estatistica, deve ser importada uma "
            "nova base independente e aplicada uma politica previamente aprovada "
            "pelo RT, sem retreinar o modelo com os dados de validacao.",
            styles["Alert"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("FIM DO RELATORIO EXPLORATORIO", styles["End"]),
    ]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "BTTitle",
            parent=base["Title"],
            fontName="AVMBacktestBold",
            fontSize=18,
            leading=22,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "Warning": ParagraphStyle(
            "BTWarning",
            parent=base["BodyText"],
            fontName="AVMBacktestBold",
            fontSize=9,
            leading=12,
            textColor=RED,
            alignment=TA_CENTER,
            backColor=colors.HexColor("#FCECEC"),
            borderPadding=7,
            spaceAfter=8,
        ),
        "Lead": ParagraphStyle(
            "BTLead",
            parent=base["BodyText"],
            fontName="AVMBacktestBody",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#34495E"),
        ),
        "Heading": ParagraphStyle(
            "BTHeading",
            parent=base["Heading2"],
            fontName="AVMBacktestBold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "BTBody",
            parent=base["BodyText"],
            fontName="AVMBacktestBody",
            fontSize=8.4,
            leading=12,
            spaceAfter=3,
        ),
        "Cell": ParagraphStyle(
            "BTCell",
            parent=base["BodyText"],
            fontName="AVMBacktestBody",
            fontSize=7.1,
            leading=9,
        ),
        "CellHeader": ParagraphStyle(
            "BTCellHeader",
            parent=base["BodyText"],
            fontName="AVMBacktestBold",
            fontSize=7,
            leading=9,
            textColor=colors.white,
        ),
        "Bold": ParagraphStyle(
            "BTBold",
            parent=base["BodyText"],
            fontName="AVMBacktestBold",
            fontSize=7.2,
            leading=9,
        ),
        "Note": ParagraphStyle(
            "BTNote",
            parent=base["BodyText"],
            fontName="AVMBacktestBody",
            fontSize=7.6,
            leading=10,
            backColor=LIGHT_BLUE,
            borderPadding=6,
            spaceBefore=4,
        ),
        "Alert": ParagraphStyle(
            "BTAlert",
            parent=base["BodyText"],
            fontName="AVMBacktestBold",
            fontSize=8.3,
            leading=12,
            textColor=RED,
            backColor=colors.HexColor("#FCECEC"),
            borderPadding=7,
        ),
        "End": ParagraphStyle(
            "BTEnd",
            parent=base["BodyText"],
            fontName="AVMBacktestBold",
            fontSize=9,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
    }


def _heading(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(escape(text), styles["Heading"])


def _p(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)), style)


def _table(rows: list[list[Any]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BCC7D1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _key_value_table(
    rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]
) -> Table:
    data = [[_p("Campo", styles["CellHeader"]), _p("Valor", styles["CellHeader"])]]
    data.extend(
        [_p(label, styles["Bold"]), _p(value, styles["Cell"])] for label, value in rows
    )
    return _table(data, [58 * mm, 120 * mm])


def _segment_table(
    rows: list[dict[str, Any]], styles: dict[str, ParagraphStyle]
) -> Table:
    data = [
        [
            _p(value, styles["CellHeader"])
            for value in (
                "Segmento",
                "N",
                "MAE",
                "MdAPE",
                "Cobertura IC80",
                "Aprov. expl.",
            )
        ]
    ]
    for row in rows:
        data.append(
            [
                _p(row["segment"], styles["Cell"]),
                _p(row["count"], styles["Cell"]),
                _p(_money(row["mae_brl"]), styles["Cell"]),
                _p(_percent(row["median_ape"]), styles["Cell"]),
                _p(_percent(row["ic80_coverage"]), styles["Cell"]),
                _p(_percent(row["approval_rate"]), styles["Cell"]),
            ]
        )
    return _table(data, [55 * mm, 14 * mm, 29 * mm, 26 * mm, 28 * mm, 26 * mm])


def _worst_results_table(
    results: list[BacktestResult], styles: dict[str, ParagraphStyle]
) -> Table:
    conclusive = [row for row in results if row.absolute_percentage_error is not None]

    def absolute_percentage_error(row: BacktestResult) -> float:
        assert row.absolute_percentage_error is not None
        return row.absolute_percentage_error

    worst = sorted(conclusive, key=absolute_percentage_error, reverse=True)[:10]
    data = [
        [
            _p(value, styles["CellHeader"])
            for value in ("ID", "Referencia", "Estimativa", "Erro abs. %", "Status")
        ]
    ]
    for row in worst:
        data.append(
            [
                _p(row.validation_id, styles["Cell"]),
                _p(_money(row.reference_value_brl), styles["Cell"]),
                _p(_money(row.estimated_value_brl), styles["Cell"]),
                _p(_percent(row.absolute_percentage_error), styles["Cell"]),
                _p(_status_label(row.status.value), styles["Cell"]),
            ]
        )
    return _table(data, [51 * mm, 34 * mm, 34 * mm, 24 * mm, 35 * mm])


def _status_label(status: str) -> str:
    return {
        "APPROVED_EXPLORATORY": "APROVADA (EXPL.)",
        "REJECTED_EXPLORATORY": "REPROVADA (EXPL.)",
        "INCONCLUSIVE_INVALID_INPUT": "INCONCLUSIVA",
    }.get(status, status)


def _scatter(results: list[BacktestResult]) -> Drawing:
    pairs = [
        (row.reference_value_brl, float(row.estimated_value_brl))
        for row in results
        if row.estimated_value_brl is not None
    ]
    width, height = 500.0, 240.0
    left, bottom, right, top = 58.0, 38.0, 485.0, 220.0
    drawing = Drawing(width, height)
    drawing.add(Line(left, bottom, left, top, strokeColor=NAVY))
    drawing.add(Line(left, bottom, right, bottom, strokeColor=NAVY))
    if not pairs:
        return drawing
    values = [value for pair in pairs for value in pair]
    low, high = min(values), max(values)
    if high == low:
        high += 1

    def scale_x(value: float) -> float:
        return left + (value - low) / (high - low) * (right - left)

    def scale_y(value: float) -> float:
        return bottom + (value - low) / (high - low) * (top - bottom)

    drawing.add(
        Line(
            scale_x(low),
            scale_y(low),
            scale_x(high),
            scale_y(high),
            strokeColor=RED,
            strokeWidth=0.8,
        )
    )
    for reference, estimate in pairs:
        drawing.add(
            Circle(
                scale_x(reference),
                scale_y(estimate),
                2.0,
                fillColor=BLUE,
                strokeColor=None,
            )
        )
    drawing.add(
        String(
            (left + right) / 2,
            10,
            "Valor de referencia (R$)",
            fontName="AVMBacktestBody",
            fontSize=7,
            textAnchor="middle",
        )
    )
    drawing.add(
        String(
            3,
            (bottom + top) / 2,
            "Estimativa (R$)",
            fontName="AVMBacktestBody",
            fontSize=7,
        )
    )
    drawing.add(String(left, 25, f"{low:,.0f}", fontName="AVMBacktestBody", fontSize=6))
    drawing.add(
        String(
            right,
            25,
            f"{high:,.0f}",
            fontName="AVMBacktestBody",
            fontSize=6,
            textAnchor="end",
        )
    )
    return drawing


def _money(value: float | None) -> str:
    return "NAO CALCULADO" if value is None else f"R$ {value:,.2f}"


def _percent(value: float | None) -> str:
    return "NAO CALCULADO" if value is None else f"{value * 100:.2f}%"


def _footer(canvas: Canvas, document: SimpleDocTemplate) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(NAVY)
    canvas.line(15 * mm, height - 10 * mm, width - 15 * mm, height - 10 * mm)
    canvas.setFont("AVMBacktestBody", 6.5)
    canvas.drawString(
        15 * mm,
        8 * mm,
        datetime.now(timezone.utc).strftime("Gerado em %Y-%m-%d %H:%M UTC"),
    )
    canvas.drawRightString(
        width - 15 * mm, 8 * mm, f"Exploratorio - Pagina {document.page}"
    )
    canvas.restoreState()
