"""Service d'export - generation de rapports (Markdown, JSON, PDF, conversation)."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from report_generator.report_export import export_to_markdown

NAVY = colors.HexColor("#16213E")
NAVY_LIGHT = colors.HexColor("#243A63")
GOLD = colors.HexColor("#B8956A")
GOLD_LIGHT = colors.HexColor("#E7D5B8")
MUTED = colors.HexColor("#5D6B82")
BORDER = colors.HexColor("#E1E6EE")
LIGHT_BG = colors.HexColor("#F4F6FB")
GOLD_BG = colors.HexColor("#FBF7EF")
DANGER = colors.HexColor("#C0392B")
WARNING = colors.HexColor("#C77D2E")
SUCCESS = colors.HexColor("#1E7A46")

_FONT_DIRS = [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/msttcorefonts", "/usr/share/fonts/truetype/dejavu"]


def _register_fonts() -> str | None:
    """Enregistre une police TrueType supportant le francais. Retourne None si aucune."""
    candidates = [
        ("Arial", "arial.ttf", "arialbd.ttf"),
        ("Arial", "Arial.ttf", "Arial Bold.ttf"),
        ("DejaVuSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ]
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for base, reg, bold in candidates:
        for d in _FONT_DIRS:
            reg_path = os.path.join(d, reg)
            bold_path = os.path.join(d, bold)
            if os.path.exists(reg_path):
                pdfmetrics.registerFont(TTFont(base, reg_path))
                try:
                    pdfmetrics.registerFont(TTFont(f"{base}-Bold", bold_path))
                except Exception:
                    try:
                        pdfmetrics.registerFont(TTFont(f"{base}-Bold", reg_path))
                    except Exception:
                        pass
                return base
    return None


def _export_report_as_pdf(report: dict[str, Any]) -> bytes:
    """Genere le rapport d'analyse en PDF (A4)."""
    import io

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="TOP-JURIDIQUE - Rapport d'analyse",
        author="TOP-JURIDIQUE",
    )

    base = _register_fonts()
    if base:
        font_regular = base
        font_bold = f"{base}-Bold"
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_regular = "STSong-Light"
        font_bold = "STSong-Light"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="BrandLine", fontName=font_bold, fontSize=9, leading=12,
        textColor=GOLD, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="ReportTitle", fontName=font_bold, fontSize=19, leading=24,
        textColor=NAVY, spaceBefore=2, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="ReportMeta", fontName=font_regular, fontSize=9, leading=13,
        textColor=MUTED, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle", fontName=font_bold, fontSize=12.5, leading=16,
        textColor=NAVY, spaceBefore=12, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="Body", fontName=font_regular, fontSize=9.5, leading=14,
        textColor=colors.HexColor("#1C2333"), alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name="Small", fontName=font_regular, fontSize=8.5, leading=12,
        textColor=MUTED,
    ))
    styles.add(ParagraphStyle(
        name="Footnote", fontName=font_regular, fontSize=8, leading=11,
        textColor=MUTED,
    ))

    def h(text: str) -> str:
        return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    story: list[Any] = []

    def header_band():
        story.append(Paragraph("⚖️ &nbsp;TOP-JURIDIQUE", styles["BrandLine"]))
        story.append(HRFlowable(width="100%", thickness=1.6, color=GOLD, spaceAfter=10))

    def section(title: str):
        story.append(Paragraph(h(title), styles["SectionTitle"]))

    header_band()

    story.append(Paragraph("Rapport d'analyse juridique", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Réalisé le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — Copilote IA Juridique",
        styles["ReportMeta"],
    ))
    story.append(Spacer(1, 4))

    # -- Documents analysés
    section("1. Documents analysés")
    docs = report.get("documents_analyses", [])
    if docs:
        rows = [[Paragraph("<b>Document</b>", styles["Small"]),
                 Paragraph("<b>Type détecté</b>", styles["Small"]),
                 Paragraph("<b>Statut</b>", styles["Small"])]]
        for d in docs:
            rows.append([
                Paragraph(h(d.get("nom", "")), styles["Small"]),
                Paragraph(h(d.get("type", "")), styles["Small"]),
                Paragraph(h(d.get("statut", "")), styles["Small"]),
            ])
        table = Table(rows, colWidths=[95 * mm, 50 * mm, 27 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("Aucun document analysé.", styles["Small"]))

    # -- Niveau de risque
    section("2. Niveau de risque global")
    risque = report.get("niveau_risque_global", "non_evalue")
    risk_color = {"eleve": DANGER, "modere": WARNING, "faible": SUCCESS}.get(risque, MUTED)
    risk_label = {"eleve": "Élevé", "modere": "Modéré", "faible": "Faible"}.get(risque, "Non évalué")
    risk_box = Table(
        [[Paragraph(f"<b>{risk_label.upper()}</b>", styles["ReportMeta"])]],
        colWidths=[50 * mm],
    )
    risk_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_color),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(risk_box)
    story.append(Spacer(1, 6))

    infos = report.get("informations_principales", {})
    if infos.get("regles_controle_appliquees") is False:
        story.append(Paragraph(
            "<i>Note :</i> aucun document de type pacte d'associés ou statuts n'a été détecté. "
            "Les règles de contrôle spécifiques aux sociétés ne sont donc pas appliquées : aucune "
            "anomalie de pacte/statuts n'est rapportée.",
            styles["Body"],
        ))

    synthese = report.get("synthese_intelligente")
    if synthese:
        section("Synthèse intelligente (IA)")
        story.append(Paragraph(_conv_md_to_pdf_html(synthese), styles["Body"]))
        story.append(Spacer(1, 6))

    # -- Anomalies juridiques
    anomalies = report.get("anomalies_juridiques", [])
    section(f"3. Anomalies juridiques ({len(anomalies)})")
    if not anomalies:
        story.append(Paragraph("Aucune anomalie détectée.", styles["Body"]))
    for i, a in enumerate(anomalies, 1):
        priorite = a.get("priorite", "alerte")
        p_hex = {"bloquant": "#C0392B", "important": "#C77D2E"}.get(priorite, "#5D6B82")
        p_label = {"bloquant": "Bloquant", "important": "Important", "alerte": "Alerte"}.get(priorite, "Alerte")
        story.append(Paragraph(
            f"{i}. <b>{h(a.get('nature_controle', 'Anomalie'))}</b> "
            f"<font color='{p_hex}'><b>[{p_label}]</b></font>",
            styles["Body"],
        ))
        if a.get("explication"):
            story.append(Paragraph(h(a["explication"]), styles["Body"]))
        details = []
        if a.get("source_juridique"):
            details.append(f"<b>Source juridique :</b> {h(a['source_juridique'])}")
        if a.get("correction_recommandee"):
            details.append(f"<b>Correction recommandée :</b> {h(a['correction_recommandee'])}")
        docs_verif = a.get("documents_a_verifier", [])
        if docs_verif:
            details.append(f"<b>Documents à vérifier :</b> {h(', '.join(docs_verif))}")
        if details:
            story.append(Paragraph("<br/>".join(details), styles["Small"]))
        story.append(Spacer(1, 5))

    # -- Incohérences
    incoherences = report.get("incoherences", [])
    section(f"4. Incohérences entre documents ({len(incoherences)})")
    if not incoherences:
        story.append(Paragraph("Aucune incohérence détectée.", styles["Body"]))
    for inc in incoherences:
        story.append(Paragraph(
            f"• <b>{h(inc.get('type', ''))}</b> ({h(inc.get('severite', ''))}) : {h(inc.get('description', ''))}",
            styles["Body"],
        ))

    # -- Entités extraites
    entites = infos.get("entites_extraites", {})
    if entites:
        section("5. Entités extraites")
        for doc_name, doc_entites in entites.items():
            story.append(Paragraph(f"<b>{h(doc_name)}</b>", styles["Body"]))
            lines = []
            dates = doc_entites.get("dates", [])
            if dates:
                lines.append(f"Dates : {h(', '.join(dict.fromkeys(d['valeur'] for d in dates)))}")
            parties = doc_entites.get("parties", [])
            if parties:
                lines.append(f"Organisations : {h(', '.join(dict.fromkeys(p.get('nom', '') for p in parties)))}")
            montants = doc_entites.get("montants", [])
            if montants:
                lines.append(f"Montants : {h(', '.join(dict.fromkeys(m.get('valeur', '') for m in montants)))}")
            if lines:
                for line in lines:
                    story.append(Paragraph(f"– {line}", styles["Small"]))
            story.append(Spacer(1, 4))

    # -- Pied de page
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        "Ce rapport a été généré automatiquement par TOP-JURIDIQUE. Il ne constitue pas un avis "
        "juridique : une validation par un professionnel du droit reste nécessaire.",
        styles["Footnote"],
    ))

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont(font_regular, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, "TOP-JURIDIQUE — Copilote IA Juridique")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {_doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def export_report_as_markdown(report: dict[str, Any]) -> bytes:
    """Exporte le rapport en Markdown."""
    from services.analysis_service import format_report_markdown
    md = format_report_markdown(report)
    return md.encode("utf-8")


def export_report_as_json(report: dict[str, Any]) -> bytes:
    """Exporte le rapport en JSON."""
    return json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")


def export_report_as_pdf(report: dict[str, Any]) -> bytes:
    """Exporte le rapport en PDF professionnel."""
    return _export_report_as_pdf(report)


def export_conversation_as_text(conversation: list[dict]) -> bytes:
    """Exporte la conversation en texte."""
    lines = []
    lines.append("=" * 60)
    lines.append("TOP-JURIDIQUE - Historique de conversation")
    lines.append(f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append("=" * 60 + "\n")
    for entry in conversation:
        lines.append(f"Question : {entry.get('question', '')}")
        lines.append(f"Reponse : {entry.get('answer', '')}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def _conv_md_to_pdf_html(text: str) -> str:
    """Convertit le markdown du chat vers du HTML compatible reportlab."""
    text = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = []
    for raw in text.split("\n"):
        line = raw
        if line.strip() == "---":
            continue
        if line.startswith("&gt; "):
            line = line[5:]
        elif line.startswith("&gt;"):
            line = line[4:]
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", line)
        line = line.strip()
        if line:
            lines.append(line)
    return "<br/>".join(lines)


def export_conversation_as_pdf(conversation: list[dict]) -> bytes:
    """Exporte la conversation en PDF professionnel (A4)."""
    import io

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="TOP-JURIDIQUE - Historique de conversation",
        author="TOP-JURIDIQUE",
    )

    base = _register_fonts()
    if base:
        font_regular = base
        font_bold = f"{base}-Bold"
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_regular = "STSong-Light"
        font_bold = "STSong-Light"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ChatBrandLine", fontName=font_bold, fontSize=9, leading=12,
        textColor=GOLD, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="ChatTitle", fontName=font_bold, fontSize=19, leading=24,
        textColor=NAVY, spaceBefore=2, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="ChatMeta", fontName=font_regular, fontSize=9, leading=13,
        textColor=MUTED, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="ChatLabel", fontName=font_bold, fontSize=10.5, leading=14,
        textColor=NAVY, spaceBefore=8, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="ChatBody", fontName=font_regular, fontSize=9.5, leading=14,
        textColor=colors.HexColor("#1C2333"), alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name="ChatFoot", fontName=font_regular, fontSize=8, leading=11,
        textColor=MUTED,
    ))

    story: list[Any] = []
    story.append(Paragraph("⚖️ &nbsp;TOP-JURIDIQUE", styles["ChatBrandLine"]))
    story.append(HRFlowable(width="100%", thickness=1.6, color=GOLD, spaceAfter=10))
    story.append(Paragraph("Historique de conversation", styles["ChatTitle"]))
    story.append(Paragraph(
        f"Réalisé le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — Copilote IA Juridique",
        styles["ChatMeta"],
    ))
    story.append(Spacer(1, 6))

    if not conversation:
        story.append(Paragraph("Aucune question posée.", styles["ChatBody"]))

    for i, entry in enumerate(conversation, 1):
        ts = entry.get("timestamp", "")
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        story.append(Paragraph(
            f"{i}. <font color='#B8956A'>QUESTION</font>"
            f"&nbsp;<font color='#5D6B82' size=7>{ts}</font>",
            styles["ChatLabel"],
        ))
        if question.strip():
            story.append(Paragraph(_conv_md_to_pdf_html(question), styles["ChatBody"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"<font color='#B8956A'>RÉPONSE — COPILOTE JURIDIQUE</font>"
            f"&nbsp;<font color='#5D6B82' size=7>{ts}</font>",
            styles["ChatLabel"],
        ))
        if answer.strip():
            story.append(Paragraph(_conv_md_to_pdf_html(answer), styles["ChatBody"]))
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        "Conversation générée automatiquement par TOP-JURIDIQUE. Elle ne constitue pas un avis "
        "juridique : une validation par un professionnel du droit reste nécessaire.",
        styles["ChatFoot"],
    ))

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont(font_regular, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, "TOP-JURIDIQUE — Copilote IA Juridique")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {_doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
