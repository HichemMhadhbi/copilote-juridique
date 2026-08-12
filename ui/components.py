"""Composants reutilisables - interface professionnelle TOP-JURIDIQUE."""

from __future__ import annotations

import base64
import html
import os
from pathlib import Path
from typing import Any

import streamlit as st

from report_generator.report_export import (
    TYPE_LABELS_HUMAIN,
    INCOH_TYPE_HUMAIN,
    SEVERITE_HUMAIN,
    NATURE_CONTROLE_HUMAIN,
    CONTROLE_FONDEMENT,
    points_cles_document,
)

RISK_META = {
    "eleve": ("Élevé", "tj-badge eleve"),
    "modere": ("Modéré", "tj-badge moderate"),
    "faible": ("Faible", "tj-badge faible"),
    "critique": ("Critique", "tj-badge eleve"),
    "non_evalue": ("Non évalué", "tj-badge non-evalue"),
}

_ICON_POINTS_CLES = {
    "Société": "🏢",
    "Associés et parties": "👥",
    "Montants": "💰",
    "Dates": "📅",
    "Articles cités": "📄",
}


def _esc(value: Any) -> str:
    return html.escape(str(value or ""))


def render_hero_header():
    logo_tag = "<div class=\"tj-hero-icon\">⚖️</div>"

    st.html(
        f"""
        <div class="tj-hero">
            <div class="tj-hero-top">
                <div class="tj-brand">{logo_tag}<span class="tj-brand-text">TOP-JURIDIQUE</span></div>
            </div>
            <h1>Tableau de bord formaliste</h1>
            <p>Analyse intelligente de vos documents juridiques : extraction des informations clés, contrôle réglementaire et rapport professionnel.</p>
        </div>
        """
    )


def render_sidebar_header():
    logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "ImagesUtilisé", "Top-juridique-logo.png")
    )
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, width=170)
    else:
        st.sidebar.markdown(
            """
            <div class="tj-sidebar-logo-fallback">⚖️ TOP-JURIDIQUE</div>
            """,
            unsafe_allow_html=True,
        )

    st.sidebar.markdown(
        """
        <div class="tj-sidebar-card tj-sidebar-card-top">
            <div class="tj-sidebar-intro">
                <div class="tj-sidebar-intro-title">Espace de travail</div>
                <div class="tj-sidebar-intro-copy">Analyse de documents juridiques</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_banner(analyzed: bool, doc_count: int = 0):
    if analyzed:
        st.html(
            f"""
            <div class="tj-status ok">
                <span class="tj-status-dot"></span>
                <span><strong>Dossier prêt</strong> &mdash; {doc_count} document(s) analysé(s) avec succès.</span>
            </div>
            """
        )
    else:
        st.html(
            """
            <div class="tj-status wait">
                <span class="tj-status-dot"></span>
                <span><strong>En attente de documents</strong> &mdash; déposez vos fichiers dans le panneau
                de gauche puis lancez l'analyse.</span>
            </div>
            """
        )


def render_section_title(title: str, subtitle: str = ""):
    subtitle_html = f"<p>{_esc(subtitle)}</p>" if subtitle else ""
    st.html(
        f"""
        <div class="tj-section-title">
            <div class="tj-section-accent"></div>
            <div>
                <h2>{_esc(title)}</h2>
                {subtitle_html}
            </div>
        </div>
        """
    )


def render_risk_badge(risk: str) -> str:
    label, css = RISK_META.get(risk, RISK_META["non_evalue"])
    return f'<span class="tj-badge {css}">{_esc(label)}</span>'


def render_metric_cards(report: dict[str, Any]):
    risque = report.get("niveau_risque_global", "non_evalue")
    anomalies = report.get("anomalies_juridiques", [])
    incoherences = report.get("incoherences", [])
    docs = report.get("documents_analyses", [])

    label, css = RISK_META.get(risque, RISK_META["non_evalue"])
    risque_html = f'<span class="tj-badge {css}">{_esc(label)}</span>'

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Niveau de risque</div>
                <div class="kpi-value" style="font-size:1.15rem;padding-top:0.25rem;">{risque_html}</div>
                <div class="kpi-sub">Évaluation globale</div>
            </div>
            """
        )
    with c2:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Anomalies</div>
                <div class="kpi-value">{len(anomalies)}</div>
                <div class="kpi-sub">À corriger dans les documents</div>
            </div>
            """
        )
    with c3:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Incohérences</div>
                <div class="kpi-value">{len(incoherences)}</div>
                <div class="kpi-sub">Entre pacte et statuts</div>
            </div>
            """
        )
    with c4:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Documents</div>
                <div class="kpi-value">{len(docs)}</div>
                <div class="kpi-sub">Documents traités</div>
            </div>
            """
        )
    st.write("")


def render_documents_table(documents: list[dict[str, Any]], statuses: dict[str, str] | None = None):
    """Tableau des documents analysés (nom, type, statut, lecture).

    Conservée pour un éventuel réaffichage ; la vue principale n'affiche plus
    cette section (les documents apparaissent déjà dans la barre latérale).
    """
    if not documents:
        return
    STATUS_LABELS = {
        "natif": "Texte lisible",
        "ocr": "Scan numérisé (texte reconstitué)",
        "ocr_indisponible": "Scan sans texte (à vérifier)",
        "erreur": "Erreur de lecture",
    }
    rows = []
    for d in documents:
        nom = d.get("nom", "")
        type_raw = d.get("type", "")
        statut_raw = d.get("statut", "")
        row = {
            "Document": nom,
            "Type de document": TYPE_LABELS_HUMAIN.get(type_raw, type_raw or "Non reconnu"),
            "Statut": {"analyse": "Analysé"}.get(statut_raw, statut_raw or "Analysé"),
        }
        if statuses:
            st_label = STATUS_LABELS.get(statuses.get(nom, ""), statuses.get(nom, ""))
            row["Lecture du fichier"] = st_label
        rows.append(row)
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def render_entities_panel(entites_extraites: dict[str, Any]):
    """Affiche les points clés métier extraits de chaque document."""
    if not entites_extraites:
        st.html('<div class="tj-empty">Aucun point clé extrait.</div>')
        return

    for doc_name, doc_entites in entites_extraites.items():
        with st.container(border=True):
            st.markdown(f"**{_esc(doc_name)}**")
            points = points_cles_document(doc_entites)
            anything = False
            for label, valeurs in points:
                if not valeurs:
                    continue
                anything = True
                pills = "".join(
                    f'<span class="tj-pill">{_esc(v)}</span>' for v in valeurs
                )
                icon = _ICON_POINTS_CLES.get(label, "🔹")
                st.html(
                    f'<div class="tj-entity-block"><div class="tj-entity-label">'
                    f'<span class="tj-entity-icon">{icon}</span> {label}</div>'
                    f'<div class="tj-entity-pills">{pills}</div></div>'
                )
            if not anything:
                st.caption("Aucune information clé détectée dans ce document.")
            st.caption(
                "Informations clés extraites automatiquement des documents."
            )


def render_anomalie_card(index: int, anomalie: dict[str, Any], docs_by_name: dict[str, str] | None = None, statut_validation: str = ""):
    priorite = anomalie.get("priorite", "alerte")
    label = {
        "bloquant": ("Bloquant", "tj-badge eleve"),
        "important": ("Important", "tj-badge moderate"),
        "alerte": ("Alerte", "tj-badge non-evalue"),
    }.get(priorite, ("Alerte", "tj-badge non-evalue"))
    badge = f'<span class="tj-badge {label[1]}">{label[0]}</span>'

    explication = anomalie.get("explication", "")
    nature = anomalie.get("nature_controle", "")
    nature_label = NATURE_CONTROLE_HUMAIN.get(nature, nature or "Anomalie")
    source = anomalie.get("source_juridique", "")
    correction = anomalie.get("correction_recommandee", "")
    docs_a_verifier = anomalie.get("documents_a_verifier", [])
    contexte = anomalie.get("contexte", "")
    fondement = CONTROLE_FONDEMENT.get(nature, "")

    lines = [f'<div class="tj-card"><div style="display:flex;justify-content:space-between;align-items:center;gap:0.5rem;">'
             f'<strong>Anomalie {index} — {_esc(nature_label)}</strong> {badge}</div>']
    if statut_validation == "modifie":
        lines.append(
            f'<div style="margin:0.4rem 0 0 0;padding:0.35rem 0.6rem;background:#EAF6EE;'
            f'border-left:3px solid #1E7D4E;font-size:0.82rem;color:#1E7D4E;">'
            f'✏️ Contenu corrigé par le juriste (intégré au rapport)</div>'
        )
    if explication:
        lines.append(f"<p style='margin:0.5rem 0 0 0;'>{_esc(explication)}</p>")
    if contexte:
        lines.append(
            f'<div style="margin:0.6rem 0 0 0;padding:0.55rem 0.7rem;'
            f'border-left:3px solid #E7D5B8;background:#FBF7EF;'
            f'font-size:0.85rem;color:#5D6B82;line-height:1.45;">'
            f'<b>Dans le document :</b> {_esc(contexte)}</div>'
        )
    details = []
    if fondement:
        details.append(f"<b>Contrôle :</b> {_esc(fondement)}")
    if source:
        details.append(f"<b>Source :</b> {_esc(source)}")
        statut = anomalie.get("source_statut", "")
        labels = {
            "verifiee": "✅ texte retrouvé dans Légifrance",
            "introuvable": "⚠️ texte introuvable dans Légifrance",
            "erreur": "⚠️ vérification impossible pour le moment",
            "non_configure": "ℹ️ lien vers Légifrance fourni",
            "fictive": "⚠️ référence à remplacer",
            "liee": "ℹ️ liée à Légifrance",
            "source_non_legale": "ℹ️ source non réglementaire (pas une référence d'article)",
        }
        if statut in labels:
            details.append(f"<b>Vérification :</b> {labels[statut]}")
        texte_officiel = anomalie.get("texte_officiel", "")
        texte_complet = anomalie.get("texte_officiel_complet", "")
        if statut == "verifiee" and texte_officiel:
            tronque = bool(texte_complet) and len(texte_complet) > len(texte_officiel)
            libelle = "Texte officiel (extrait)" if tronque else "Texte officiel (article complet)"
            details.append(f"<b>{libelle} :</b> «{_esc(texte_officiel)}{'…' if tronque else ''}»")
    if correction:
        details.append(f"<b>Correction recommandée :</b> {_esc(correction)}")
    if docs_a_verifier:
        libelles = []
        for d in docs_a_verifier:
            type_doc = (docs_by_name or {}).get(d, "")
            libelles.append(f"{_esc(type_doc)} ({_esc(d)})" if type_doc else _esc(d))
        pluriel = "Document concerné" if len(libelles) == 1 else "Documents concernés"
        details.append(f"<b>{pluriel} :</b> {', '.join(libelles)}")
    if details:
        lines.append(f'<p style="margin:0.5rem 0 0 0;color:#5D6B82;font-size:0.88rem;">{"<br>".join(details)}</p>')
    lines.append("</div>")
    st.html("".join(lines))

    statut = anomalie.get("source_statut", "")
    texte_complet = anomalie.get("texte_officiel_complet", "")
    texte_officiel = anomalie.get("texte_officiel", "")
    if statut == "verifiee" and texte_complet and len(texte_complet) > len(texte_officiel or ""):
        with st.expander("📜 Lire l'article complet (Légifrance)"):
            st.markdown(texte_complet)


def render_incoherence_card(index: int, incoherence: dict[str, Any]):
    type_inc = incoherence.get("type", "")
    severite = incoherence.get("severite", "")
    description = incoherence.get("description", "")
    champ = incoherence.get("champ", "")
    docs = incoherence.get("documents", [])
    if not docs and incoherence.get("document_1") and incoherence.get("document_2"):
        docs = [incoherence["document_1"], incoherence["document_2"]]

    sev_badge = {
        "eleve": ("Élevée", "tj-badge eleve"),
        "moyen": ("Moyenne", "tj-badge moderate"),
        "modere": ("Modérée", "tj-badge moderate"),
        "faible": ("Faible", "tj-badge faible"),
        "bloquant": ("Bloquante", "tj-badge eleve"),
        "important": ("Importante", "tj-badge moderate"),
        "alerte": ("Alerte", "tj-badge non-evalue"),
    }
    sev_label = sev_badge.get(severite, ("—", "tj-badge non-evalue"))
    badge = f'<span class="tj-badge {sev_label[1]}">{sev_label[0]}</span>'

    titre = INCOH_TYPE_HUMAIN.get(type_inc, type_inc or "Incohérence")
    parts = [f'<div class="tj-card"><strong>Incohérence {index} — {_esc(titre)}</strong> {badge}']
    if description:
        parts.append(f"<p style='margin:0.5rem 0 0 0;'>{_esc(description)}</p>")
    meta = []
    valeur_pacte = incoherence.get("valeur_pacte", "")
    valeur_statuts = incoherence.get("valeur_statuts", "")
    if valeur_pacte or valeur_statuts:
        meta.append(f"<b>Pacte :</b> {_esc(valeur_pacte)}")
        meta.append(f"<b>Statuts :</b> {_esc(valeur_statuts)}")
    if champ:
        meta.append(f"<b>Champ :</b> {_esc(champ)}")
    if docs:
        if len(docs) == 1:
            meta.append(f"<b>Fichier concerné :</b> {_esc(docs[0])}")
        elif len(docs) >= 2:
            meta.append(
                f"<b>Fichiers concernés :</b> {_esc(' / '.join(docs))}"
            )
    if meta:
        parts.append(f'<p style="margin:0.5rem 0 0 0;color:#5D6B82;font-size:0.88rem;">{"<br>".join(meta)}</p>')
    parts.append("</div>")
    st.html("".join(parts))


def render_question_preview(question: str):
    st.html(
        f"""
        <div class="tj-card" style="background:#FBF7EF;border-color:#E7D5B8;">
            <div style="display:flex;align-items:flex-start;gap:0.6rem;">
                <span style="font-size:1.1rem;">📌</span>
                <div><strong>Question sélectionnée</strong>
                <div style="color:#3A4557;">{_esc(question)}</div></div>
            </div>
        </div>
        """
    )


def render_validation_summary(summary_data: dict[str, Any]):
    """Affiche les indicateurs de validation humaine (anomalies approuvees,
    rejetees, en attente, taux de validation)."""
    total = summary_data.get("total", 0)
    en_attente = summary_data.get("en_attente", 0)
    approuves = summary_data.get("approuves", 0)
    rejetes = summary_data.get("rejetes", 0)
    modifies = summary_data.get("modifies", 0)
    taux = summary_data.get("taux_validation", 0.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">En attente</div>
                <div class="kpi-value">{en_attente}</div>
                <div class="kpi-sub">À valider par le juriste</div>
            </div>
            """
        )
    with c2:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Approuvées</div>
                <div class="kpi-value" style="color:#1E7D4E;">{approuves}</div>
                <div class="kpi-sub">Validées</div>
            </div>
            """
        )
    with c3:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Rejetées</div>
                <div class="kpi-value" style="color:#C0392B;">{rejetes}</div>
                <div class="kpi-sub">Non retenues</div>
            </div>
            """
        )
    with c4:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Modifiées</div>
                <div class="kpi-value">{modifies}</div>
                <div class="kpi-sub">Corrigées</div>
            </div>
            """
        )
    st.html(
        f"""
        <div class="tj-status {'ok' if taux >= 100 and total else 'wait'}">
            <span class="tj-status-dot"></span>
            <span><strong>Avancement :</strong> {approuves}/{total} anomalie(s) approuvée(s) —
            taux de validation {taux:.0f}%. Chaque anomalie doit être validée par un juriste
            avant d'être intégrée au rapport final.</span>
        </div>
        """
    )
