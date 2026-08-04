"""
Module d'exportation de rapports pour TOP-JURIDIQUE.

Fournit des fonctions pour exporter les rapports d'analyse
au format Markdown et PDF (via reportlab).
"""

from __future__ import annotations

import io
from typing import Any


# ══════════════════════════════════════════════════════════════════════════════
# Export Markdown
# ══════════════════════════════════════════════════════════════════════════════

def export_to_markdown(report_dict: dict[str, Any]) -> str:
    """
    Convertit un rapport structuré en texte Markdown formaté.

    Args:
        report_dict: Dictionnaire du rapport tel que généré par ReportBuilder.

    Returns:
        Chaîne Markdown complète prête à l'écriture.
    """
    lignes: list[str] = []

    # ── En-tête ─────────────────────────────────────────────────────────────
    lignes.append("# Rapport d'Analyse Juridique — TOP-JURIDIQUE\n")
    lignes.append(f"**Rapport ID :** `{report_dict.get('rapport_id', 'N/A')}`  ")
    lignes.append(f"**Date d'analyse :** {report_dict.get('date_analyse', 'N/A')}\n")
    lignes.append("---\n")

    # ── Documents analysés ──────────────────────────────────────────────────
    docs = report_dict.get("documents_analyses", [])
    if docs:
        lignes.append("## 1. Documents Analysés\n")
        for doc in docs:
            if isinstance(doc, dict):
                nom = doc.get("nom", "Inconnu")
                type_doc = doc.get("type", "Non spécifié")
                statut = doc.get("statut", "analyse")
                lignes.append(f"- **{nom}** — Type: {type_doc} — Statut: {statut}")
            else:
                lignes.append(f"- **{doc}**")
        lignes.append("")

    docs_manquants = report_dict.get("documents_manquants", [])
    if docs_manquants:
        lignes.append("### Documents Manquants\n")
        for dm in docs_manquants:
            lignes.append(f"- ⚠️ {dm}")
        lignes.append("")

    docs_illisible = report_dict.get("documents_illisibles", [])
    if docs_illisible:
        lignes.append("### Documents Illisibles\n")
        for di in docs_illisible:
            lignes.append(f"- ❌ {di}")
        lignes.append("")

    # ── Informations principales ────────────────────────────────────────────
    infos = report_dict.get("informations_principales", {})
    if infos:
        lignes.append("## 2. Informations Principales\n")
        for cle, valeur in infos.items():
            if isinstance(valeur, list):
                lignes.append(f"**{cle.replace('_', ' ').title()} :**")
                for item in valeur:
                    lignes.append(f"  - {item}")
            else:
                lignes.append(f"**{cle.replace('_', ' ').title()} :** {valeur}")
        lignes.append("")

    # ── Incohérences ───────────────────────────────────────────────────────
    incoherences = report_dict.get("incoherences", [])
    if incoherences:
        lignes.append("## 3. Incohérences Détectées\n")
        for i, inc in enumerate(incoherences, 1):
            lignes.append(f"### Incohérence {i}\n")
            lignes.append(f"- **Description :** {inc.get('description', 'N/A')}")
            lignes.append(f"- **Document 1 :** {inc.get('document_1', 'N/A')}")
            lignes.append(f"- **Document 2 :** {inc.get('document_2', 'N/A')}")
            lignes.append(f"- **Champ concerné :** {inc.get('champ', 'N/A')}")
            lignes.append("")

    # ── Anomalies juridiques ────────────────────────────────────────────────
    anomalies = report_dict.get("anomalies_juridiques", [])
    if anomalies:
        lignes.append("## 4. Anomalies Juridiques\n")
        for i, anom in enumerate(anomalies, 1):
            priorite = anom.get("priorite", "non spécifié")
            emoji_priorite = {"bloquant": "🔴", "important": "🟠", "alerte": "🟡"}.get(
                priorite, "⚪"
            )
            lignes.append(f"### Anomalie {i} {emoji_priorite} [{priorite.upper()}]\n")
            lignes.append(f"**Explication :** {anom.get('explication', 'N/A')}\n")
            lignes.append(f"- **Nature du contrôle :** {anom.get('nature_controle', 'N/A')}")
            lignes.append(f"- **Conséquence :** {anom.get('consequence', 'N/A')}")
            lignes.append(f"- **Source juridique :** {anom.get('source_juridique', 'N/A')}")

            statut = anom.get("source_statut", "")
            labels = {
                "verifiee": "Vérifiée dans Légifrance (PISTE)",
                "introuvable": "Introuvable dans Légifrance",
                "erreur": "Erreur de vérification (service indisponible)",
                "non_configure": "Vérification non configurée (mode lien)",
                "fictive": "Référence fictive à remplacer",
                "liee": "Liée à Légifrance (mode lien)",
            }
            if statut in labels:
                lignes.append(f"- **Vérification source :** {labels[statut]}")
            texte_officiel = anom.get("texte_officiel", "")
            if statut == "verifiee" and texte_officiel:
                lignes.append(f"- **Extrait texte officiel :** {texte_officiel}…")
            lignes.append(f"- **Correction recommandée :** {anom.get('correction_recommandee', 'N/A')}")

            docs_verif = anom.get("documents_a_verifier", [])
            if docs_verif:
                lignes.append("- **Documents à vérifier :**")
                for dv in docs_verif:
                    lignes.append(f"  - {dv}")

            validation = anom.get("validation_requise", "non")
            if validation == "oui":
                lignes.append("- **⚠️ Validation humaine requise**")
            lignes.append("")

    # ── Clauses à risque ────────────────────────────────────────────────────
    clauses_risque = report_dict.get("clauses_a_risque", [])
    if clauses_risque:
        lignes.append("## 5. Clauses à Risque\n")
        for cr in clauses_risque:
            lignes.append(f"- **{cr.get('clause', 'N/A')}** — Risque : {cr.get('risque', 'N/A')}")
        lignes.append("")

    # ── Clauses manquantes ──────────────────────────────────────────────────
    clauses_manq = report_dict.get("clauses_manquantes", [])
    if clauses_manq:
        lignes.append("## 6. Clauses Manquantes\n")
        for cm in clauses_manq:
            lignes.append(f"- **{cm.get('clause', 'N/A')}** — Justification : {cm.get('justification', 'N/A')}")
        lignes.append("")

    # ── Améliorations proposées ─────────────────────────────────────────────
    ameliorations = report_dict.get("ameliorations_proposees", [])
    if ameliorations:
        lignes.append("## 7. Améliorations Proposées\n")
        for i, amel in enumerate(ameliorations, 1):
            lignes.append(f"{i}. **{amel.get('titre', 'Amélioration')}**")
            lignes.append(f"   - {amel.get('description', 'N/A')}")
        lignes.append("")

    # ── Niveau de risque global ─────────────────────────────────────────────
    risque = report_dict.get("niveau_risque_global", "non_evalue")
    emoji_risque = {
        "faible": "🟢", "modere": "🟡", "eleve": "🟠", "critique": "🔴"
    }.get(risque, "⚪")
    lignes.append(f"## 8. Niveau de Risque Global : {emoji_risque} {risque.upper()}\n")

    # ── Recommandations finales ─────────────────────────────────────────────
    recomms = report_dict.get("recommandations_finales", [])
    if recomms:
        lignes.append("## 9. Recommandations Finales\n")
        for i, rec in enumerate(recomms, 1):
            lignes.append(f"{i}. **{rec.get('titre', 'Recommandation')}**")
            lignes.append(f"   - {rec.get('description', 'N/A')}")
            if rec.get("priorite"):
                lignes.append(f"   - Priorité : {rec['priorite']}")
        lignes.append("")

    # ── Points de validation humaine ────────────────────────────────────────
    validations = report_dict.get("points_validation_humaine", [])
    if validations:
        lignes.append("## 10. Points de Validation Humaine\n")
        for i, val in enumerate(validations, 1):
            lignes.append(f"### Point {i}")
            lignes.append(f"- **Objet :** {val.get('objet', 'N/A')}")
            lignes.append(f"- **Question :** {val.get('question', 'N/A')}")
            lignes.append(f"- **Impact :** {val.get('impact', 'N/A')}")
            lignes.append("")

    # ── Pied de page ────────────────────────────────────────────────────────
    lignes.append("---")
    lignes.append("*Rapport généré automatiquement par TOP-JURIDIQUE — Copilote IA Juridique*")
    lignes.append("*Ce document nécessite une relecture par un professionnel du droit.*")

    return "\n".join(lignes)


# ══════════════════════════════════════════════════════════════════════════════
# Export PDF
# ══════════════════════════════════════════════════════════════════════════════

def export_to_pdf(report_dict: dict[str, Any]) -> bytes:
    """
    Génère un PDF du rapport d'analyse via reportlab.

    Args:
        report_dict: Dictionnaire du rapport.

    Returns:
        Contenu binaire du PDF.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            HRFlowable,
        )
    except ImportError:
        raise ImportError(
            "Package 'reportlab' requis pour l'export PDF. "
            "Exécutez: pip install reportlab"
        )

    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    _register_custom_styles(styles)

    elements: list[Any] = []

    # ── En-tête ─────────────────────────────────────────────────────────────
    elements.append(Paragraph("Rapport d'Analyse Juridique", styles["Title"]))
    elements.append(Paragraph("TOP-JURIDIQUE — Copilote IA Juridique", styles["Subtitle"]))
    elements.append(Spacer(1, 0.5 * cm))

    # Métadonnées
    meta_data = [
        ["Rapport ID", str(report_dict.get("rapport_id", "N/A"))],
        ["Date", str(report_dict.get("date_analyse", "N/A"))],
        ["Risque global", str(report_dict.get("niveau_risque_global", "N/A"))],
    ]
    meta_table = Table(meta_data, colWidths=[5 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 1 * cm))

    # ── Documents analysés ──────────────────────────────────────────────────
    docs = report_dict.get("documents_analyses", [])
    if docs:
        elements.append(Paragraph("Documents Analysés", styles["SectionTitle"]))
        for doc in docs:
            if isinstance(doc, dict):
                elements.append(
                    Paragraph(
                        f"• <b>{doc.get('nom', 'N/A')}</b> — "
                        f"Type: {doc.get('type', 'N/A')} — "
                        f"Statut: {doc.get('statut', 'N/A')}",
                        styles["BodyText"],
                    )
                )
            else:
                elements.append(
                    Paragraph(f"• <b>{doc}</b>", styles["BodyText"])
                )
        elements.append(Spacer(1, 0.5 * cm))

    # ── Informations principales ────────────────────────────────────────────
    infos = report_dict.get("informations_principales", {})
    if infos:
        elements.append(Paragraph("Informations Principales", styles["SectionTitle"]))
        for cle, valeur in infos.items():
            if isinstance(valeur, list):
                valeur_str = "<br/>".join(f"• {v}" for v in valeur)
            else:
                valeur_str = str(valeur)
            elements.append(
                Paragraph(
                    f"<b>{cle.replace('_', ' ').title()} :</b> {valeur_str}",
                    styles["BodyText"],
                )
            )
        elements.append(Spacer(1, 0.5 * cm))

    # ── Incohérences ───────────────────────────────────────────────────────
    incoherences = report_dict.get("incoherences", [])
    if incoherences:
        elements.append(Paragraph("Incohérences Détectées", styles["SectionTitle"]))
        for i, inc in enumerate(incoherences, 1):
            elements.append(
                Paragraph(
                    f"<b>Incohérence {i} :</b> {inc.get('description', 'N/A')}",
                    styles["BodyText"],
                )
            )
            elements.append(
                Paragraph(
                    f"Documents : {inc.get('document_1', 'N/A')} ↔ "
                    f"{inc.get('document_2', 'N/A')} — Champ : {inc.get('champ', 'N/A')}",
                    styles["BodyTextSmall"],
                )
            )
        elements.append(Spacer(1, 0.5 * cm))

    # ── Anomalies juridiques ────────────────────────────────────────────────
    anomalies = report_dict.get("anomalies_juridiques", [])
    if anomalies:
        elements.append(Paragraph("Anomalies Juridiques", styles["SectionTitle"]))
        for i, anom in enumerate(anomalies, 1):
            priorite = anom.get("priorite", "N/A")
            elements.append(
                Paragraph(
                    f"<b>Anomalie {i} [{priorite.upper()}]</b>",
                    styles["SubSectionTitle"],
                )
            )
            elements.append(
                Paragraph(anom.get("explication", "N/A"), styles["BodyText"])
            )

            detail_data = [
                ["Nature du contrôle", anom.get("nature_controle", "N/A")],
                ["Conséquence", anom.get("consequence", "N/A")],
                ["Source juridique", anom.get("source_juridique", "N/A")],
            ]
            statut_labels = {
                "verifiee": "Vérifiée dans Légifrance (PISTE)",
                "introuvable": "Introuvable dans Légifrance",
                "erreur": "Erreur de vérification (service indisponible)",
                "non_configure": "Vérification non configurée (mode lien)",
                "fictive": "Référence fictive à remplacer",
                "liee": "Liée à Légifrance (mode lien)",
            }
            statut = anom.get("source_statut", "")
            if statut in statut_labels:
                detail_data.append(["Vérification source", statut_labels[statut]])
            detail_data.append(["Correction", anom.get("correction_recommandee", "N/A")])
            detail_table = Table(detail_data, colWidths=[4.5 * cm, 12.5 * cm])
            detail_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(detail_table)
            elements.append(Spacer(1, 0.3 * cm))

    # ── Recommandations finales ─────────────────────────────────────────────
    recomms = report_dict.get("recommandations_finales", [])
    if recomms:
        elements.append(Paragraph("Recommandations Finales", styles["SectionTitle"]))
        for i, rec in enumerate(recomms, 1):
            elements.append(
                Paragraph(
                    f"<b>{i}. {rec.get('titre', 'Recommandation')}</b><br/>"
                    f"{rec.get('description', 'N/A')}",
                    styles["BodyText"],
                )
            )
        elements.append(Spacer(1, 0.5 * cm))

    # ── Points de validation ────────────────────────────────────────────────
    validations = report_dict.get("points_validation_humaine", [])
    if validations:
        elements.append(Paragraph("Points de Validation Humaine", styles["SectionTitle"]))
        for i, val in enumerate(validations, 1):
            elements.append(
                Paragraph(
                    f"<b>Point {i} :</b> {val.get('objet', 'N/A')}<br/>"
                    f"Question : {val.get('question', 'N/A')}<br/>"
                    f"Impact : {val.get('impact', 'N/A')}",
                    styles["BodyText"],
                )
            )
        elements.append(Spacer(1, 0.5 * cm))

    # ── Pied de page ────────────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", color=colors.grey))
    elements.append(
        Paragraph(
            "<i>Rapport généré automatiquement par TOP-JURIDIQUE. "
            "Ce document nécessite une relecture par un professionnel du droit.</i>",
            styles["BodyTextSmall"],
        )
    )

    # Génération du PDF
    pdf_doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def _register_custom_styles(styles: Any) -> None:
    """Enregistre les styles personnalisés pour le PDF."""
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors

    styles.add(
        ParagraphStyle(
            name="Subtitle",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.Color(0.4, 0.4, 0.4),
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.Color(0.1, 0.3, 0.6),
            spaceBefore=16,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubSectionTitle",
            parent=styles["Heading3"],
            fontSize=12,
            textColor=colors.Color(0.2, 0.4, 0.7),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTextSmall",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.Color(0.3, 0.3, 0.3),
            alignment=TA_LEFT,
            spaceAfter=4,
        )
    )
