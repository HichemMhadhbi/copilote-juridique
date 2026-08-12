"""
Module d'exportation de rapports pour TOP-JURIDIQUE.

Fournit des fonctions pour exporter les rapports d'analyse
au format Markdown et PDF (via reportlab).
"""

from __future__ import annotations

import io
import re
from typing import Any


# ══════════════════════════════════════════════════════════════════════════════
# Libellés métier partagés (affichage humain au lieu des codes techniques)
# ══════════════════════════════════════════════════════════════════════════════

TYPE_LABELS_HUMAIN = {
    "pacte d'associes": "Pacte d'associés",
    "statuts de societe": "Statuts de société",
    "proces-verbal d'assemblee": "Procès-verbal d'assemblée",
    "modification statutaire": "Modification statutaire",
    "non_classe": "Document non reconnu",
}

INCOH_TYPE_HUMAIN = {
    "montant": "Incohérence de montant",
    "date": "Incohérence de date",
    "partie": "Incohérence de parties",
    "clause": "Incohérence de clause",
    "mise_a_jour_24_mois": "Mise à jour des statuts",
    "duree_societe": "Durée de la société",
    "titres_capital": "Répartition du capital",
    "objet_social": "Objet social",
}

SEVERITE_HUMAIN = {
    "eleve": "sévérité élevée",
    "moyen": "sévérité moyenne",
    "faible": "sévérité faible",
    "bloquant": "bloquant",
    "important": "important",
    "alerte": "alerte",
}

NATURE_CONTROLE_HUMAIN = {
    "clause_manquante": "Clause manquante",
    "clause_incomplete": "Clause incomplète",
    "conformité": "Conformité",
    "proportionnalité": "Proportionnalité",
    "contradiction": "Contradiction",
    "vérification": "Vérification",
    "incohérence": "Incohérence",
    "risque_futur": "Risque contractuel à prévenir",
}

STATUT_LECTURE_HUMAIN = {
    "natif": "Texte lisible",
    "ocr": "Scan numérisé (texte reconstitué)",
    "ocr_indisponible": "Scan sans texte (à vérifier)",
    "erreur": "Erreur de lecture",
}

CONTROLE_FONDEMENT = {
    "clause_manquante": "Présence d'une clause obligatoire ou recommandée",
    "clause_incomplete": "Complétude de la clause (champs à renseigner)",
    "conformité": "Conformité aux règles du droit des sociétés",
    "proportionnalité": "Proportionnalité de la clause",
    "contradiction": "Cohérence entre les documents du dossier",
    "incohérence": "Terminologie conforme à la forme sociale",
    "vérification": "Mention obligatoire / formalité",
    "risque_futur": "Risque contractuel à prévenir",
}


def points_cles_document(doc_entites: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """Résume les entités extraites d'un document en points clés métier."""
    formes_societe = re.compile(r"\b(?:SARL|SASU?|SA|SCI|EURL|SNC|SCA|SCS)\b")

    def _dedupe(valeurs: list[str]) -> list[str]:
        return list(dict.fromkeys(v for v in valeurs if v))

    organisations = [p.get("nom", "") for p in doc_entites.get("parties", [])]
    personnes = [
        f"{p.get('civilite', '').strip()} {p.get('nom', '')}".strip()
        for p in doc_entites.get("personnes", [])
    ]
    societes = [n for n in organisations if formes_societe.search(n.upper())]
    autres_orgs = [n for n in organisations if not formes_societe.search(n.upper())]
    parties = personnes + autres_orgs
    montants = [m.get("valeur", "") for m in doc_entites.get("montants", [])]
    dates = [d.get("valeur", "") for d in doc_entites.get("dates", [])]
    articles = [a.get("reference", "") for a in doc_entites.get("articles", [])]
    return [
        ("Société", _dedupe(societes)[:2]),
        ("Associés et parties", _dedupe(parties)[:8]),
        ("Montants", [f"{v} €" for v in _dedupe(montants)][:6]),
        ("Dates", _dedupe(dates)[:6]),
        ("Articles cités", _dedupe(articles)[:8]),
    ]


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
                type_doc = doc.get("type", "")
                type_label = TYPE_LABELS_HUMAIN.get(type_doc, type_doc or "Non reconnu")
                lignes.append(f"- **{nom}** — {type_label}")
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
            type_label = INCOH_TYPE_HUMAIN.get(inc.get("type", ""), inc.get("type", "") or "Incohérence")
            lignes.append(f"### Incohérence {i} — {type_label}\n")
            lignes.append(f"- **Description :** {inc.get('description', 'N/A')}")
            if inc.get("valeur_pacte") or inc.get("valeur_statuts"):
                lignes.append(f"- **Pacte :** {inc.get('valeur_pacte', 'N/A')}")
                lignes.append(f"- **Statuts :** {inc.get('valeur_statuts', 'N/A')}")
            fichiers = inc.get("documents") or []
            if len(fichiers) == 1:
                lignes.append(f"- **Fichier concerné :** {fichiers[0]}")
            elif len(fichiers) >= 2:
                lignes.append(f"- **Fichiers concernés :** {fichiers[0]} et {fichiers[1]}")
            else:
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
            nature_label = NATURE_CONTROLE_HUMAIN.get(
                anom.get("nature_controle", ""), anom.get("nature_controle", "Anomalie")
            )
            lignes.append(f"### Anomalie {i} {emoji_priorite} [{priorite.upper()}]\n")
            lignes.append(f"**Explication :** {anom.get('explication', 'N/A')}\n")
            lignes.append(f"- **Nature du contrôle :** {nature_label}")
            lignes.append(f"- **Conséquence :** {anom.get('consequence', 'N/A')}")
            lignes.append(f"- **Source juridique :** {anom.get('source_juridique', 'N/A')}")

            statut = anom.get("source_statut", "")
            labels = {
                "verifiee": "Texte retrouvé dans Légifrance",
                "introuvable": "Texte introuvable dans Légifrance",
                "erreur": "Vérification impossible pour le moment",
                "non_configure": "Lien vers Légifrance fourni",
                "fictive": "Référence à remplacer",
                "liee": "Liée à Légifrance",
                "source_non_legale": "Source non réglementaire (pas une référence d'article)",
            }
            if statut in labels:
                lignes.append(f"- **Vérification source :** {labels[statut]}")
            url = anom.get("legifrance_url", "")
            if url and statut in ("verifiee", "liee"):
                lignes.append(f"- **Lien Légifrance :** [Voir le texte sur Légifrance]({url})")
            texte_officiel = anom.get("texte_officiel", "")
            texte_complet = anom.get("texte_officiel_complet", "")
            if statut == "verifiee" and texte_officiel:
                tronque = bool(texte_complet) and len(texte_complet) > len(texte_officiel)
                libelle = "Extrait texte officiel" if tronque else "Texte officiel (article complet)"
                lignes.append(f"- **{libelle} :** {texte_officiel}{'…' if tronque else ''}")
            texte_complet = anom.get("texte_officiel_complet", "")
            if statut == "verifiee" and texte_complet and len(texte_complet) > len(texte_officiel or ""):
                lignes.append(f"- **Texte officiel complet :** {texte_complet}")
            contexte = anom.get("contexte", "")
            if contexte:
                lignes.append(f"- **Contexte dans le document :** {contexte}")
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
                ["Nature du contrôle", NATURE_CONTROLE_HUMAIN.get(
                    anom.get("nature_controle", ""), anom.get("nature_controle", "Anomalie")
                )],
                ["Conséquence", anom.get("consequence", "N/A")],
                ["Source juridique", anom.get("source_juridique", "N/A")],
            ]
            statut_labels = {
                "verifiee": "Texte retrouvé dans Légifrance",
                "introuvable": "Texte introuvable dans Légifrance",
                "erreur": "Vérification impossible pour le moment",
                "non_configure": "Lien vers Légifrance fourni",
                "fictive": "Référence à remplacer",
                "liee": "Liée à Légifrance",
                "source_non_legale": "Source non réglementaire (pas une référence d'article)",
            }
            statut = anom.get("source_statut", "")
            if statut in statut_labels:
                detail_data.append(["Vérification source", statut_labels[statut]])
            url = anom.get("legifrance_url", "")
            if url and statut in ("verifiee", "liee"):
                detail_data.append([
                    "Lien Légifrance",
                    f'<link href="{url}" color="blue">Voir le texte sur Légifrance</link>',
                ])
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
