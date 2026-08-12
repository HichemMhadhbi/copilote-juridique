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

from report_generator.report_export import (
    export_to_markdown,
    TYPE_LABELS_HUMAIN,
    INCOH_TYPE_HUMAIN,
    SEVERITE_HUMAIN,
    STATUT_LECTURE_HUMAIN,
    NATURE_CONTROLE_HUMAIN,
    CONTROLE_FONDEMENT,
    points_cles_document,
)

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
    styles.add(ParagraphStyle(
        name="Warning", fontName=font_regular, fontSize=9, leading=13,
        textColor=colors.HexColor("#8A5A00"),
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

    # -- Synthèse exécutive (en tête du rapport)
    risque = report.get("niveau_risque_global", "non_evalue")
    risk_label = {"eleve": "Élevé", "modere": "Modéré", "faible": "Faible"}.get(risque, "Non évalué")
    anomalies_list = report.get("anomalies_juridiques", [])
    incoherences_list = report.get("incoherences", [])
    n_bloquants = sum(1 for a in anomalies_list if a.get("priorite") == "bloquant")
    n_importants = sum(1 for a in anomalies_list if a.get("priorite") == "important")
    section("Synthèse exécutive")
    summary_data = [
        ["Documents analysés", str(len(report.get("documents_analyses", [])))],
        ["Anomalies juridiques", str(len(anomalies_list))],
        ["  dont bloquantes", str(n_bloquants)],
        ["  dont importantes", str(n_importants)],
        ["Incohérences entre documents", str(len(incoherences_list))],
        ["Niveau de risque global", risk_label],
    ]
    summary_table = Table(summary_data, colWidths=[62 * mm, 62 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GOLD_BG),
        ("GRID", (0, 0), (-1, -1), 0.4, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    synthese = report.get("synthese_intelligente")
    if synthese:
        story.append(Spacer(1, 4))
        story.append(Paragraph(_conv_md_to_pdf_html(synthese), styles["Body"]))
    story.append(Spacer(1, 6))

    # -- Documents analysés
    infos = report.get("informations_principales", {})
    docs = report.get("documents_analyses", [])
    if docs:
        statuts_lecture = infos.get("statut_lecture", {})
        rows = [[Paragraph("<b>Document</b>", styles["Small"]),
                 Paragraph("<b>Type de document</b>", styles["Small"]),
                 Paragraph("<b>Lecture du fichier</b>", styles["Small"])]]
        for d in docs:
            nom = d.get("nom", "")
            type_label = TYPE_LABELS_HUMAIN.get(d.get("type", ""), d.get("type", "") or "Non reconnu")
            lecture = STATUT_LECTURE_HUMAIN.get(
                statuts_lecture.get(nom, ""), statuts_lecture.get(nom, "")
            ) or "—"
            rows.append([
                Paragraph(h(nom), styles["Small"]),
                Paragraph(h(type_label), styles["Small"]),
                Paragraph(h(lecture), styles["Small"]),
            ])
        table = Table(rows, colWidths=[78 * mm, 56 * mm, 40 * mm])
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

    # -- Anomalies juridiques
    anomalies = report.get("anomalies_juridiques", [])
    docs_by_name = {
        d.get("nom", ""): d.get("type", "") for d in report.get("documents_analyses", [])
    }
    section(f"3. Anomalies juridiques ({len(anomalies)})")
    if not anomalies:
        story.append(Paragraph("Aucune anomalie détectée.", styles["Body"]))
    for i, a in enumerate(anomalies, 1):
        priorite = a.get("priorite", "alerte")
        p_hex = {"bloquant": "#C0392B", "important": "#C77D2E"}.get(priorite, "#5D6B82")
        p_label = {"bloquant": "Bloquant", "important": "Important", "alerte": "Alerte"}.get(priorite, "Alerte")
        nature_label = NATURE_CONTROLE_HUMAIN.get(
            a.get("nature_controle", ""), a.get("nature_controle", "Anomalie")
        )
        story.append(Paragraph(
            f"{i}. <b>{h(nature_label)}</b> "
            f"<font color='{p_hex}'><b>[{p_label}]</b></font>",
            styles["Body"],
        ))
        if a.get("explication"):
            story.append(Paragraph(h(a["explication"]), styles["Body"]))
        if a.get("statut_validation") == "modifie":
            story.append(Paragraph(
                "<i>✏️ Texte corrigé par le juriste.</i>", styles["Small"],
            ))
        contexte = a.get("contexte", "")
        if contexte:
            story.append(Paragraph(
                f"<b>Dans le document :</b> {h(contexte)}", styles["Small"],
            ))
        details = []
        fondement = CONTROLE_FONDEMENT.get(a.get("nature_controle", ""))
        if fondement:
            details.append(f"<b>Contrôle :</b> {h(fondement)}")
        if a.get("source_juridique"):
            details.append(f"<b>Source juridique :</b> {h(a['source_juridique'])}")
        url = a.get("legifrance_url")
        if url and a.get("source_statut") in ("verifiee", "liee"):
            details.append(
                f"<b>Vérification :</b> <link href='{h(url)}' color='blue'>Voir le texte sur Légifrance</link>"
            )
        elif a.get("source_statut") == "introuvable":
            details.append("<b>Vérification :</b> référence introuvable dans Légifrance (à vérifier)")
        elif a.get("source_statut") == "source_non_legale":
            details.append("<b>Vérification :</b> source non réglementaire (modèle ou principes généraux, pas une référence d'article)")
        texte_officiel = a.get("texte_officiel", "")
        texte_complet = a.get("texte_officiel_complet", "")
        if a.get("source_statut") == "verifiee" and texte_officiel:
            tronque = bool(texte_complet) and len(texte_complet) > len(texte_officiel)
            libelle = "Texte officiel (extrait)" if tronque else "Texte officiel (article complet)"
            details.append(f"<b>{libelle} :</b> «{h(texte_officiel)}{'…' if tronque else ''}»")
        if a.get("correction_recommandee"):
            details.append(f"<b>Correction recommandée :</b> {h(a['correction_recommandee'])}")
        docs_verif = a.get("documents_a_verifier", [])
        if docs_verif:
            libelles = []
            for dv in docs_verif:
                type_doc = TYPE_LABELS_HUMAIN.get(docs_by_name.get(dv, ""), docs_by_name.get(dv, ""))
                libelles.append(f"{type_doc} ({dv})" if type_doc else dv)
            pluriel = "Document concerné" if len(libelles) == 1 else "Documents concernés"
            details.append(f"<b>{pluriel} :</b> {h(', '.join(libelles))}")
        if details:
            story.append(Paragraph("<br/>".join(details), styles["Small"]))
        story.append(Spacer(1, 5))

    # -- Incohérences
    incoherences = report.get("incoherences", [])
    section(f"4. Incohérences entre documents ({len(incoherences)})")
    comparaison_ecartee = report.get("comparaison_ecartee")
    if comparaison_ecartee:
        story.append(Paragraph(f"⚠️ {h(comparaison_ecartee)}", styles["Warning"]))
    if not incoherences:
        story.append(Paragraph("Aucune incohérence détectée.", styles["Body"]))
    for inc in incoherences:
        type_label = INCOH_TYPE_HUMAIN.get(inc.get("type", ""), inc.get("type", "") or "Incohérence")
        sev = inc.get("severite", "")
        sev_label = SEVERITE_HUMAIN.get(sev, sev)
        fichiers = inc.get("documents") or []
        if len(fichiers) == 1:
            loc = f" — Fichier concerné : {h(fichiers[0])}"
        elif len(fichiers) >= 2:
            loc = f" — Concerne les 2 fichiers : {h(fichiers[0])} et {h(fichiers[1])}"
        else:
            loc = ""
        story.append(Paragraph(
            f"• <b>{h(type_label)}</b> ({h(sev_label)}) : {h(inc.get('description', ''))}{loc}",
            styles["Body"],
        ))

    # -- Points clés des documents
    entites = infos.get("entites_extraites", {})
    if entites:
        section("5. Points clés des documents")
        for doc_name, doc_entites in entites.items():
            story.append(Paragraph(f"<b>{h(doc_name)}</b>", styles["Body"]))
            lignes = []
            for label, valeurs in points_cles_document(doc_entites):
                if valeurs:
                    lignes.append(f"{label} : {h(', '.join(valeurs))}")
            if lignes:
                for ligne in lignes:
                    story.append(Paragraph(f"– {ligne}", styles["Small"]))
            story.append(Spacer(1, 4))

    # -- Validation humaine
    validations = report.get("validations_appliquees", [])
    if validations:
        section("6. Validation humaine")
        statut_labels = {
            "approuve": "Approuvée",
            "rejete": "Rejetée",
            "modifie": "Modifiée",
        }
        for v in validations:
            label = statut_labels.get(v.get("statut"), v.get("statut", ""))
            lignes_val = [
                f"{v.get('numero', '')}. <b>{h(v.get('nature', 'Anomalie'))}</b> "
                f"<b>[{h(label)}]</b>"
            ]
            if v.get("commentaire_juriste"):
                lignes_val.append(f"<b>Commentaire du juriste :</b> {h(v['commentaire_juriste'])}")
            if v.get("motif_rejet"):
                lignes_val.append(f"<b>Motif du rejet :</b> {h(v['motif_rejet'])}")
            nc = v.get("nouveau_contenu") or {}
            if nc.get("explication"):
                lignes_val.append(f"<b>Texte corrigé :</b> {h(nc['explication'])}")
            if nc.get("correction_recommandee"):
                lignes_val.append(f"<b>Correction recommandée (modifiée) :</b> {h(nc['correction_recommandee'])}")
            story.append(Paragraph("<br/>".join(lignes_val), styles["Small"]))
            story.append(Spacer(1, 5))

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
