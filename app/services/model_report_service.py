from __future__ import annotations

import io
import json
from html import escape
from pathlib import Path
from typing import Any

import numpy as np
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
from scipy.stats import probplot  # type: ignore[import-untyped]

from app.core.config import APP_VERSION
from app.domain.statistical_dataset_model import StatisticalDatasetModel
from app.domain.statistical_model_version_model import StatisticalModelVersionModel


FONT_DIRECTORY = Path(reportlab.__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("AVMModelBody", FONT_DIRECTORY / "Vera.ttf"))
pdfmetrics.registerFont(TTFont("AVMModelBold", FONT_DIRECTORY / "VeraBd.ttf"))

NAVY = colors.HexColor("#123B66")
BLUE = colors.HexColor("#1E5A88")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_GRAY = colors.HexColor("#F5F7F9")
MID_GRAY = colors.HexColor("#B8C5D1")
RED = colors.HexColor("#A61B1B")


def build_statistical_model_report_pdf(
    *,
    model: StatisticalModelVersionModel,
    dataset: StatisticalDatasetModel,
) -> bytes:
    is_asking_price_research = dataset.dependent_variable == "asking_price_brl"
    use_scope = (
        "TREINO EXPLORATÓRIO COM PREÇO PEDIDO - NÃO APROVÁVEL"
        if is_asking_price_research
        else "MINUTA DE HOMOLOGAÇÃO SOMBRA - SEM VALIDADE CONTRATUAL"
    )
    introductory_notice = (
        "A variável dependente é o preço pedido do anúncio. Este ajuste serve "
        "somente para pesquisa, diagnóstico do pipeline e revisão de qualidade; "
        "não estima valor de mercado utilizável e não pode ser aprovado para "
        "inferência AVM."
        if is_asking_price_research
        else (
            "Documento técnico reproduzível para revisão. Não representa aceite "
            "da CAIXA, laudo de avaliação, assinatura de Responsável Técnico ou "
            "conclusão do Fluxo Pareado."
        )
    )
    training = json.loads(dataset.training_payload_json)
    diagnostics = json.loads(model.diagnostics_json)
    features: list[str] = json.loads(model.feature_names_json)
    coefficients = np.asarray(json.loads(model.coefficients_json), dtype=float)
    observations = np.asarray(training["observations"], dtype=float)
    values = np.asarray(training["values"], dtype=float)
    design = np.column_stack((np.ones(len(observations)), observations))
    fitted = design @ coefficients
    residuals = values - fitted
    expected_signs: dict[str, int] = json.loads(model.expected_signs_json)
    feature_ranges: dict[str, list[float]] = json.loads(dataset.feature_ranges_json)
    p_values = diagnostics["coefficient_p_values"]
    vifs = diagnostics["variance_inflation_factors"]

    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title=f"Minuta do Relatório do Modelo {model.model_version}",
        author="AVM Imóveis API",
        subject=(
            "Treino exploratório com preço pedido, sem uso em inferência"
            if is_asking_price_research
            else "Evidência técnica de modelo em homologação sombra"
        ),
    )
    styles = _styles()
    story: list[Any] = [
        Paragraph("RELATÓRIO DO MODELO AVM", styles["Title"]),
        Paragraph(use_scope, styles["Warning"]),
        Paragraph(introductory_notice, styles["Lead"]),
        Spacer(1, 4 * mm),
        _heading("1. Identificação, escopo e vigência", styles),
        _key_value_table(
            [
                ("ID do modelo", model.model_id),
                ("Cidade - código IBGE", model.city_ibge_code),
                ("Tipologia", model.property_type),
                ("Método", model.method),
                ("Versão do modelo", model.model_version),
                ("Versão do algoritmo", model.algorithm_version),
                ("Versão da API", APP_VERSION),
                ("Vigência inicial", model.valid_from.isoformat()),
                (
                    "Vigência final",
                    model.valid_until.isoformat() if model.valid_until else "Aberta",
                ),
                ("Estado", model.status),
                ("Validade contratual", "NÃO"),
            ],
            styles,
        ),
        Spacer(1, 4 * mm),
        _heading("2. Dataset e variável dependente", styles),
        _key_value_table(
            [
                ("ID do dataset", dataset.dataset_id),
                ("Versão", dataset.dataset_version),
                ("Data de referência", dataset.reference_date.isoformat()),
                ("Observações efetivamente usadas", str(dataset.observation_count)),
                ("Variáveis explicativas", str(dataset.variable_count)),
                ("Variável dependente", dataset.dependent_variable),
                ("Unidade", dataset.dependent_variable_unit),
                ("Transformação", dataset.dependent_variable_transformation),
                ("Referência da fonte", dataset.source_reference),
                ("SHA-256 do dataset", dataset.dataset_sha256),
                ("SHA-256 da matriz", dataset.training_matrix_sha256),
                ("SHA-256 do artefato", model.artifact_sha256),
            ],
            styles,
        ),
        Paragraph(
            "O hash do dataset é calculado pelo servidor sobre matriz, valores, "
            "escopo e semântica. A fonte externa declarada ainda precisa ser "
            "verificada e aprovada pelo Responsável Técnico.",
            styles["Note"],
        ),
        PageBreak(),
        _heading("3. Variáveis, domínio e coeficientes", styles),
        _coefficient_table(
            features=features,
            coefficients=coefficients,
            p_values=p_values,
            expected_signs=expected_signs,
            feature_ranges=feature_ranges,
            vifs=vifs,
            styles=styles,
        ),
        Spacer(1, 5 * mm),
        _heading("4. Estatística descritiva da matriz", styles),
        _descriptive_table(features, observations, styles),
        Spacer(1, 5 * mm),
        _heading("5. Diagnósticos automáticos", styles),
        _diagnostics_table(diagnostics, styles),
        Paragraph(
            "Os diagnósticos automáticos não calculam a pontuação integral do grau "
            "de fundamentação. O grau de precisão é avaliado separadamente para "
            "cada imóvel pelo intervalo de confiança de 80%.",
            styles["Note"],
        ),
        PageBreak(),
        _heading("6. Observado versus estimado", styles),
        _scatter_plot(
            x=values,
            y=fitted,
            x_label="Valor observado (R$)",
            y_label="Valor estimado (R$)",
            diagonal=True,
        ),
        Spacer(1, 5 * mm),
        _heading("7. Resíduos versus valores ajustados", styles),
        _scatter_plot(
            x=fitted,
            y=residuals,
            x_label="Valor ajustado (R$)",
            y_label="Resíduo (R$)",
            horizontal_zero=True,
        ),
        PageBreak(),
        _heading("8. Gráfico de probabilidade normal dos resíduos", styles),
        _qq_plot(residuals),
        Spacer(1, 5 * mm),
        _heading("9. Itens NBR automatizados", styles),
        _nbr_table(diagnostics, styles),
        Paragraph(
            "Não foi atribuído grau global de fundamentação. A classificação final "
            "exige os demais itens pontuados, análise de coerência/elasticidade, "
            "conteúdo completo do laudo e aprovação profissional.",
            styles["Alert"],
        ),
        Spacer(1, 5 * mm),
        _heading("10. Treino, revisão e segregação de funções", styles),
        _key_value_table(
            [
                ("Treinado por", model.trained_by),
                ("Treinado em", _datetime_text(model.trained_at)),
                ("Revisado por", model.approved_by or "NÃO REVISADO"),
                ("Referência da revisão", model.approval_reference or "AUSENTE"),
                ("Revisado em", _datetime_text(model.approved_at)),
                ("RT responsável pelo modelo", "NÃO CADASTRADO"),
                ("CREA/CAU", "NÃO CADASTRADO"),
                ("Assinatura eletrônica", "AUSENTE"),
            ],
            styles,
        ),
        PageBreak(),
        _heading("11. Limites de uso e pendências de homologação", styles),
        *_bullet_list(
            [
                "Extrapolação além do mínimo/máximo observado é bloqueada.",
                (
                    "A inferência aceita apenas valor total de mercado em BRL, "
                    "sem transformação."
                ),
                (
                    "Modelos treinados com asking_price_brl permanecem em pesquisa, "
                    "não podem ser aprovados e são bloqueados na inferência."
                ),
                (
                    "A amplitude do IC80 é recalculada para cada imóvel; acima "
                    "de 50% a OS é recusada."
                ),
                (
                    "Faltam validação em dados reais, plano de variáveis aprovado "
                    "e análise espacial quando aplicável."
                ),
                (
                    "Faltam Relatório do Modelo definitivo, parecer/assinatura "
                    "dos RTs e ART/RRT."
                ),
                (
                    "Faltam integração oficial, parâmetros CAIXA e Fluxo Pareado "
                    "de 30 dias."
                ),
                "Este artefato não pode ser promovido localmente ao modo contratual.",
            ],
            styles,
        ),
        Spacer(1, 5 * mm),
        _heading("12. Conclusão da minuta", styles),
        Paragraph(
            (
                "O artefato é um treino exploratório rastreável e permanece "
                "obrigatoriamente como CANDIDATE, sem uso em avaliações."
                if is_asking_price_research
                else (
                    "O artefato é tecnicamente rastreável para testes controlados. "
                    "A condição CONTRATUAL permanece bloqueada; os elementos externos "
                    "e profissionais listados acima são condições obrigatórias para "
                    "a homologação formal."
                )
            ),
            styles["Body"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("FIM DA MINUTA TÉCNICA", styles["End"]),
    ]
    document.build(
        story,
        onFirstPage=_page_decoration(model.model_id),
        onLaterPages=_page_decoration(model.model_id),
    )
    return output.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "ModelTitle",
            parent=sample["Title"],
            fontName="AVMModelBold",
            fontSize=19,
            leading=23,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=5,
        ),
        "Warning": ParagraphStyle(
            "ModelWarning",
            parent=sample["BodyText"],
            fontName="AVMModelBold",
            fontSize=9,
            leading=12,
            textColor=RED,
            alignment=TA_CENTER,
            backColor=colors.HexColor("#FCECEC"),
            borderPadding=7,
            spaceAfter=8,
        ),
        "Lead": ParagraphStyle(
            "ModelLead",
            parent=sample["BodyText"],
            fontName="AVMModelBody",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#34495E"),
        ),
        "Heading": ParagraphStyle(
            "ModelHeading",
            parent=sample["Heading2"],
            fontName="AVMModelBold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=4,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "ModelBody",
            parent=sample["BodyText"],
            fontName="AVMModelBody",
            fontSize=8.5,
            leading=12,
        ),
        "Bullet": ParagraphStyle(
            "ModelBullet",
            parent=sample["BodyText"],
            fontName="AVMModelBody",
            fontSize=8.5,
            leading=12,
            leftIndent=10,
            bulletIndent=0,
            spaceAfter=4,
        ),
        "Bold": ParagraphStyle(
            "ModelBold",
            parent=sample["BodyText"],
            fontName="AVMModelBold",
            fontSize=8,
            leading=10,
        ),
        "Cell": ParagraphStyle(
            "ModelCell",
            parent=sample["BodyText"],
            fontName="AVMModelBody",
            fontSize=7.2,
            leading=9,
        ),
        "CellHeader": ParagraphStyle(
            "ModelCellHeader",
            parent=sample["BodyText"],
            fontName="AVMModelBold",
            fontSize=7.2,
            leading=9,
            textColor=colors.white,
        ),
        "Note": ParagraphStyle(
            "ModelNote",
            parent=sample["BodyText"],
            fontName="AVMModelBody",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#4F5B66"),
            backColor=LIGHT_BLUE,
            borderPadding=6,
            spaceBefore=4,
        ),
        "Alert": ParagraphStyle(
            "ModelAlert",
            parent=sample["BodyText"],
            fontName="AVMModelBold",
            fontSize=8,
            leading=11,
            textColor=RED,
            backColor=colors.HexColor("#FCECEC"),
            borderPadding=6,
            spaceBefore=4,
        ),
        "End": ParagraphStyle(
            "ModelEnd",
            parent=sample["BodyText"],
            fontName="AVMModelBold",
            fontSize=9,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
    }


def _heading(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(escape(text), styles["Heading"])


def _paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)), style)


def _table(data: list[list[Any]], widths: list[float]) -> Table:
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, MID_GRAY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
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
    data = [
        [
            _paragraph("Campo", styles["CellHeader"]),
            _paragraph("Valor", styles["CellHeader"]),
        ],
        *[
            [
                _paragraph(label, styles["Bold"]),
                _paragraph(value, styles["Cell"]),
            ]
            for label, value in rows
        ],
    ]
    return _table(data, [56 * mm, 122 * mm])


def _coefficient_table(
    *,
    features: list[str],
    coefficients: np.ndarray[Any, Any],
    p_values: list[float],
    expected_signs: dict[str, int],
    feature_ranges: dict[str, list[float]],
    vifs: dict[str, float],
    styles: dict[str, ParagraphStyle],
) -> Table:
    headers = ["Variável", "Coeficiente", "p-valor", "Sinal", "Domínio", "VIF"]
    rows: list[list[Any]] = [
        [_paragraph(value, styles["CellHeader"]) for value in headers]
    ]
    rows.append(
        [
            _paragraph("Intercepto", styles["Cell"]),
            _paragraph(f"{coefficients[0]:.8g}", styles["Cell"]),
            _paragraph(f"{p_values[0]:.6g}", styles["Cell"]),
            _paragraph("-", styles["Cell"]),
            _paragraph("-", styles["Cell"]),
            _paragraph("-", styles["Cell"]),
        ]
    )
    for index, name in enumerate(features, start=1):
        bounds = feature_ranges[name]
        rows.append(
            [
                _paragraph(name, styles["Cell"]),
                _paragraph(f"{coefficients[index]:.8g}", styles["Cell"]),
                _paragraph(f"{p_values[index]:.6g}", styles["Cell"]),
                _paragraph(f"{expected_signs[name]:+d}", styles["Cell"]),
                _paragraph(f"[{bounds[0]:g}; {bounds[1]:g}]", styles["Cell"]),
                _paragraph(f"{float(vifs[name]):.4f}", styles["Cell"]),
            ]
        )
    return _table(rows, [43 * mm, 31 * mm, 24 * mm, 16 * mm, 39 * mm, 25 * mm])


def _descriptive_table(
    features: list[str],
    observations: np.ndarray[Any, Any],
    styles: dict[str, ParagraphStyle],
) -> Table:
    rows: list[list[Any]] = [
        [
            _paragraph(value, styles["CellHeader"])
            for value in ("Variável", "Mínimo", "Média", "Desvio-padrão", "Máximo")
        ]
    ]
    for index, name in enumerate(features):
        column = observations[:, index]
        rows.append(
            [
                _paragraph(name, styles["Cell"]),
                _paragraph(f"{np.min(column):.6g}", styles["Cell"]),
                _paragraph(f"{np.mean(column):.6g}", styles["Cell"]),
                _paragraph(f"{np.std(column, ddof=1):.6g}", styles["Cell"]),
                _paragraph(f"{np.max(column):.6g}", styles["Cell"]),
            ]
        )
    return _table(rows, [50 * mm, 32 * mm, 32 * mm, 32 * mm, 32 * mm])


def _diagnostics_table(
    diagnostics: dict[str, Any], styles: dict[str, ParagraphStyle]
) -> Table:
    rows = [
        ("R²", diagnostics["r_squared"]),
        ("R² ajustado", diagnostics["adjusted_r_squared"]),
        ("Erro-padrão residual", diagnostics["residual_standard_error"]),
        ("F global", diagnostics["f_statistic"]),
        ("p-valor do modelo", diagnostics["model_p_value"]),
        ("Maior p-valor de regressor", diagnostics["maximum_regressor_p_value"]),
        ("PRESS", diagnostics["press"]),
        ("RMSE LOOCV", diagnostics["loocv_rmse"]),
        ("Maior VIF", diagnostics["maximum_vif"]),
        (
            f"Normalidade ({diagnostics['normality_test']}) - p",
            diagnostics["normality_p_value"],
        ),
        ("Breusch-Pagan - p", diagnostics["breusch_pagan_p_value"]),
        ("Durbin-Watson", diagnostics["durbin_watson"]),
        (
            "Maior resíduo padronizado absoluto",
            diagnostics["maximum_standardized_residual"],
        ),
        ("Maior distância de Cook", diagnostics["maximum_cooks_distance"]),
    ]
    return _key_value_table(
        [(label, f"{float(value):.8g}") for label, value in rows], styles
    )


def _nbr_table(diagnostics: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    grades = diagnostics["grades"]
    rows = [
        ("Tamanho da amostra N/(k+1)", grades.get("sample") or "NÃO ATINGIDO"),
        (
            "Significância individual dos regressores",
            grades.get("significance") or "NÃO ATINGIDO",
        ),
        (
            "Significância global - teste F",
            grades.get("model_significance") or "NÃO ATINGIDO",
        ),
        (
            "Gate mínimo dos itens automatizados",
            grades.get("automatic_fundamentation_gate") or "NÃO ATINGIDO",
        ),
        (
            "Precisão no alvo diagnóstico do treino",
            grades.get("precision") or "SEM GRAU",
        ),
        ("Grau global de fundamentação", "NÃO CALCULADO"),
    ]
    return _key_value_table(rows, styles)


def _scatter_plot(
    *,
    x: np.ndarray[Any, Any],
    y: np.ndarray[Any, Any],
    x_label: str,
    y_label: str,
    diagonal: bool = False,
    horizontal_zero: bool = False,
) -> Drawing:
    width, height = 500.0, 210.0
    left, bottom, right, top = 58.0, 30.0, 485.0, 195.0
    drawing = Drawing(width, height)
    drawing.add(Line(left, bottom, left, top, strokeColor=NAVY, strokeWidth=0.8))
    drawing.add(Line(left, bottom, right, bottom, strokeColor=NAVY, strokeWidth=0.8))
    drawing.add(
        String(
            (left + right) / 2,
            8,
            x_label,
            fontName="AVMModelBody",
            fontSize=7,
            textAnchor="middle",
        )
    )
    drawing.add(
        String(4, (bottom + top) / 2, y_label, fontName="AVMModelBody", fontSize=7)
    )
    x_min, x_max = float(np.min(x)), float(np.max(x))
    y_min, y_max = float(np.min(y)), float(np.max(y))
    if np.isclose(x_min, x_max):
        x_max = x_min + 1.0
    if np.isclose(y_min, y_max):
        y_max = y_min + 1.0

    def sx(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * (right - left)

    def sy(value: float) -> float:
        return bottom + (value - y_min) / (y_max - y_min) * (top - bottom)

    if diagonal:
        common_min = max(x_min, y_min)
        common_max = min(x_max, y_max)
        if common_min <= common_max:
            drawing.add(
                Line(
                    sx(common_min),
                    sy(common_min),
                    sx(common_max),
                    sy(common_max),
                    strokeColor=RED,
                    strokeWidth=0.8,
                )
            )
    if horizontal_zero and y_min <= 0 <= y_max:
        drawing.add(
            Line(left, sy(0.0), right, sy(0.0), strokeColor=RED, strokeWidth=0.8)
        )
    for x_value, y_value in zip(x, y, strict=True):
        drawing.add(
            Circle(
                sx(float(x_value)),
                sy(float(y_value)),
                1.6,
                fillColor=BLUE,
                strokeColor=None,
            )
        )
    drawing.add(
        String(
            left,
            18,
            _format_axis_value(x_min),
            fontName="AVMModelBody",
            fontSize=6,
        )
    )
    drawing.add(
        String(
            right,
            18,
            _format_axis_value(x_max),
            fontName="AVMModelBody",
            fontSize=6,
            textAnchor="end",
        )
    )
    drawing.add(
        String(
            6,
            bottom,
            _format_axis_value(y_min),
            fontName="AVMModelBody",
            fontSize=6,
        )
    )
    drawing.add(
        String(
            6,
            top - 2,
            _format_axis_value(y_max),
            fontName="AVMModelBody",
            fontSize=6,
        )
    )
    return drawing


def _format_axis_value(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.3g} mi"
    if absolute >= 1_000:
        return f"{value / 1_000:.3g} mil"
    return f"{value:.4g}"


def _qq_plot(residuals: np.ndarray[Any, Any]) -> Drawing:
    theoretical, ordered = probplot(residuals, dist="norm", fit=False)
    return _scatter_plot(
        x=np.asarray(theoretical, dtype=float),
        y=np.asarray(ordered, dtype=float),
        x_label="Quantil teórico normal",
        y_label="Resíduo ordenado",
    )


def _bullet_list(items: list[str], styles: dict[str, ParagraphStyle]) -> list[Any]:
    flowables: list[Any] = []
    for item in items:
        flowables.append(
            Paragraph(
                escape(item),
                styles["Bullet"],
                bulletText="•",
            )
        )
    return flowables


def _datetime_text(value: object | None) -> str:
    if value is None:
        return "AUSENTE"
    return str(value)


def _page_decoration(model_id: str) -> Any:
    def decorate(canvas: Canvas, document: SimpleDocTemplate) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(NAVY)
        canvas.line(16 * mm, height - 10 * mm, width - 16 * mm, height - 10 * mm)
        canvas.setFont("AVMModelBody", 6.5)
        canvas.setFillColor(colors.HexColor("#3B4652"))
        canvas.drawString(16 * mm, 8 * mm, f"Modelo: {model_id}")
        canvas.drawRightString(
            width - 16 * mm,
            8 * mm,
            f"Minuta sem validade contratual • Página {document.page}",
        )
        canvas.restoreState()

    return decorate
