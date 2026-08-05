import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#123B5D")
BLUE = colors.HexColor("#1976A3")
PALE_BLUE = colors.HexColor("#EAF3F7")
GREEN = colors.HexColor("#DDF4E5")
AMBER = colors.HexColor("#FFF3CD")
RED = colors.HexColor("#FCE8E6")
GRAY = colors.HexColor("#5F6B75")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def money(value: Any) -> str:
    number = float(value)
    rendered = f"{number:,.2f}"
    return "R$ " + rendered.replace(",", "X").replace(".", ",").replace("X", ".")


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def build_pdf(result: dict[str, Any], output: Path) -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleAVM",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=8 * mm,
    )
    heading = ParagraphStyle(
        "HeadingAVM",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=NAVY,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    )
    body = ParagraphStyle(
        "BodyAVM",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#263238"),
        spaceAfter=2 * mm,
    )
    small = ParagraphStyle(
        "SmallAVM",
        parent=body,
        fontSize=7.5,
        leading=10,
        textColor=GRAY,
    )
    table_header = ParagraphStyle(
        "TableHeaderAVM",
        parent=body,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        spaceAfter=0,
    )
    status = ParagraphStyle(
        "StatusAVM",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        alignment=TA_CENTER,
    )

    def page_footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D6DEE3"))
        canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        canvas.drawString(
            18 * mm, 9 * mm, "AVM - Homologacao sombra RJ - Uso nao contratual"
        )
        canvas.drawRightString(192 * mm, 9 * mm, f"Pagina {doc.page}")
        canvas.restoreState()

    def table(rows: list[list[Any]], widths: list[float]) -> Table:
        normalized = []
        for row_index, row in enumerate(rows):
            row_style = table_header if row_index == 0 else body
            normalized.append(
                [
                    cell
                    if isinstance(cell, Paragraph)
                    else paragraph(str(cell), row_style)
                    for cell in row
                ]
            )
        item = Table(normalized, colWidths=widths, repeatRows=1, hAlign="LEFT")
        item.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C5CC")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return item

    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="Dossie de Homologacao Sombra AVM - Rio de Janeiro",
        author="Plataforma AVM",
    )
    story: list[Any] = []
    story.append(paragraph("DOSSIÊ DE HOMOLOGAÇÃO SOMBRA AVM", title))
    story.append(paragraph("Rio de Janeiro/RJ - IBGE 3304557 - Apartamento", status))
    story.append(Spacer(1, 5 * mm))

    banner = Table(
        [[paragraph("TESTÁVEL EM HOMOLOGAÇÃO SOMBRA", status)]],
        colWidths=[174 * mm],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GREEN),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#239B56")),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(banner)
    story.append(Spacer(1, 4 * mm))
    story.append(
        paragraph(
            "Conclusão executiva: a integração RJ foi validada de ponta a ponta, "
            "incluindo autenticação, registro do modelo controlado, cálculo, "
            "relatórios, "
            "hashes e bloqueio de entrega. O modelo estatístico real permanece NÃO "
            "HOMOLOGADO e NÃO AUTORIZADO PARA PRODUÇÃO.",
            body,
        )
    )

    story.append(paragraph("1. Resultado do teste ponta a ponta", heading))
    story.append(
        table(
            [
                ["Controle", "Resultado"],
                ["Ambiente", f"{result['environment']} / {result['execution_mode']}"],
                ["Município", f"Rio de Janeiro/RJ - IBGE {result['city_ibge_code']}"],
                ["Ordem", result["external_order_id"]],
                ["Modelo sombra", result["model_id"]],
                ["Valor calculado", money(result["estimated_value"])],
                ["Autenticação cliente/admin", "APROVADA"],
                ["PDF e CSV", "GERADOS E VERIFICADOS"],
                ["Entrega contratual", "BLOQUEADA, conforme esperado"],
            ],
            [58 * mm, 116 * mm],
        )
    )

    story.append(paragraph("2. Separação obrigatória dos modelos", heading))
    story.append(
        table(
            [
                ["Componente", "Base", "Uso permitido", "Situação"],
                [
                    "Candidato real RJ",
                    "422 anúncios VivaReal, preço pedido",
                    "Pesquisa e diagnóstico",
                    "BLOQUEADO",
                ],
                [
                    "Modelo sombra RJ",
                    "48 observações sintéticas controladas",
                    "Teste de infraestrutura",
                    "EXECUTADO",
                ],
                [
                    "Validação independente",
                    "12 anúncios exploratórios",
                    "Backtest exploratório",
                    "INSUFICIENTE",
                ],
            ],
            [36 * mm, 51 * mm, 47 * mm, 40 * mm],
        )
    )
    story.append(
        paragraph(
            "A massa sintética não substitui evidência de mercado, não participa do "
            "treinamento real e não pode ser promovida para produção. Sua finalidade é "
            "demonstrar que o software executa o fluxo técnico com segurança.",
            small,
        )
    )

    story.append(PageBreak())
    story.append(paragraph("3. Diagnóstico estatístico do candidato real", heading))
    story.append(
        table(
            [
                ["Indicador", "Resultado", "Leitura"],
                ["Amostra de pesquisa", "422", "Preço pedido; fonte única"],
                ["R²", "0,65024", "Ajuste exploratório parcial"],
                ["R² ajustado", "0,64689", "Próximo do R²"],
                ["Shapiro-Wilk (p)", "4,26 x 10^-19", "Normalidade rejeitada"],
                ["Breusch-Pagan (p)", "3,14 x 10^-6", "Heterocedasticidade indicada"],
                ["Cook máximo", "2,92", "Influência crítica"],
                ["Validade contratual", "NÃO", "Bloqueio ativo"],
            ],
            [52 * mm, 38 * mm, 84 * mm],
        )
    )

    story.append(paragraph("4. Backtest independente exploratório", heading))
    story.append(
        table(
            [
                ["Indicador", "Resultado", "Situação"],
                ["Observações", "12", "Amostra pequena"],
                ["MAE", "R$ 379.224,08", "Elevado"],
                ["MdAPE", "33,89%", "Elevado"],
                ["Cobertura empírica IC80", "8,33%", "Inadequada"],
                ["Aprovação exploratória", "1 de 12 (8,33%)", "Reprovada"],
                ["Fora do domínio geográfico", "9 de 12", "Extrapolação"],
            ],
            [65 * mm, 55 * mm, 54 * mm],
        )
    )

    warning = Table(
        [
            [
                paragraph(
                    "DECISÃO: o candidato real RJ não deve precificar avaliações "
                    "contratuais. A reprovação é um resultado válido da homologação, "
                    "não uma falha oculta.",
                    status,
                )
            ]
        ],
        colWidths=[174 * mm],
    )
    warning.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RED),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#B42318")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(warning)

    story.append(PageBreak())
    story.append(paragraph("5. Matriz de prontidão", heading))
    story.append(
        table(
            [
                ["Gate", "Resultado", "Estado"],
                ["API, banco e migrações", "Saudáveis", "APROVADO"],
                [
                    "Autenticação e segregação",
                    "Cliente e duas chaves admin",
                    "APROVADO",
                ],
                ["Cockpit / ordem RJ", "Fluxo executável", "APROVADO"],
                ["PDF, CSV e SHA-256", "Gerados e verificáveis", "APROVADO"],
                ["Bloqueio de entrega sombra", "HTTP 409", "APROVADO"],
                [
                    "Qualidade do modelo real",
                    "Diagnósticos e backtest insuficientes",
                    "REPROVADO",
                ],
                ["Representatividade", "3/360 da nova coleta", "PENDENTE"],
                [
                    "Validação independente formal",
                    "Política e amostra não aprovadas",
                    "PENDENTE",
                ],
                ["Parecer e assinatura do RT", "Não arquivados", "PENDENTE"],
            ],
            [64 * mm, 73 * mm, 37 * mm],
        )
    )

    story.append(paragraph("6. Próximas ações para homologação formal", heading))
    actions = [
        (
            "Concluir a coleta real representativa: 357 observações pendentes, "
            "com fontes diversificadas e evidências individualizadas."
        ),
        (
            "Obter variável dependente compatível com valor de mercado utilizável; "
            "preço pedido isolado não basta."
        ),
        (
            "Sanear duplicidades, coordenadas, precisão, temporalidade e domínio "
            "geográfico."
        ),
        (
            "Retreinar sem qualquer observação da base independente e repetir "
            "diagnósticos estatísticos."
        ),
        "Executar backtest independente sob política de aceite previamente aprovada.",
        "Submeter plano, resultados, ressalvas e artefatos ao Responsável Técnico.",
        (
            "Promover somente após todos os gates automáticos e documentais estarem "
            "aprovados."
        ),
    ]
    for index, action in enumerate(actions, 1):
        story.append(paragraph(f"{index}. {action}", body))

    story.append(paragraph("7. Rastreabilidade do teste RJ", heading))
    story.append(
        table(
            [
                ["Artefato", "SHA-256"],
                ["Modelo congelado", result["artifact_sha256"]],
                ["Relatório do modelo", result["model_report_pdf_sha256"]],
                ["Relatório da avaliação", result["pdf_sha256"]],
                ["Relatório CSV", result["csv_sha256"]],
            ],
            [58 * mm, 116 * mm],
        )
    )
    story.append(
        paragraph(
            "Este documento é uma evidência técnica de homologação sombra. "
            "Não é laudo, "
            "parecer do RT, ART/RRT, certificação digital ou autorização de produção.",
            small,
        )
    )

    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)


def build_manifest(directory: Path, manifest_path: Path) -> None:
    entries = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file() or path == manifest_path:
            continue
        entries.append(
            {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "HOMOLOGATION_SHADOW_NON_CONTRACTUAL",
        "files": entries,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera o dossiê e manifesto da homologação sombra do RJ."
    )
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    if result.get("scenario") != "rj" or result.get("approved") is not True:
        raise RuntimeError("A evidência informada não é um teste RJ aprovado.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pdf = args.output_dir / "DOSSIÊ-HOMOLOGACAO-SOMBRA-RJ.pdf"
    build_pdf(result, pdf)
    build_manifest(args.output_dir, args.output_dir / "SHA256-MANIFEST-RJ.json")
    print(f"Dossiê criado: {pdf.resolve()}")
    print(f"SHA-256: {sha256(pdf)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
