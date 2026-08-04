"""Composants reutilisables - interface professionnelle TOP-JURIDIQUE."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

RISK_META = {
    "eleve": ("Élevé", "tj-badge eleve"),
    "modere": ("Modéré", "tj-badge moderate"),
    "faible": ("Faible", "tj-badge faible"),
    "critique": ("Critique", "tj-badge eleve"),
    "non_evalue": ("Non évalué", "tj-badge non-evalue"),
}


def _esc(value: Any) -> str:
    return html.escape(str(value or ""))


def render_hero_header():
    st.html(
        f"""
        <div class="tj-hero">
            <div class="tj-brand"><span class="tj-logo">⚖️</span> TOP-JURIDIQUE</div>
            <h1>Copilote IA Juridique</h1>
            <p>Analyse intelligente de vos documents juridiques : extraction des informations clés,
            contrôle réglementaire et rapport professionnel.</p>
        </div>
        """
    )


def render_sidebar_header():
    st.sidebar.html(
        """
        <div class="tj-sidebar-brand">
            <div class="tj-brand"><span class="tj-logo">⚖️</span> TOP-JURIDIQUE</div>
            <h2>Espace de travail</h2>
            <p>Analyse de documents juridiques</p>
        </div>
        """
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

    rules_applied = (
        report.get("informations_principales", {}).get("regles_controle_appliquees") is True
    )

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
                <div class="kpi-sub">Règles de contrôle</div>
            </div>
            """
        )
    with c3:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Incohérences</div>
                <div class="kpi-value">{len(incoherences)}</div>
                <div class="kpi-sub">Entre documents</div>
            </div>
            """
        )
    with c4:
        st.html(
            f"""
            <div class="tj-kpi">
                <div class="kpi-label">Documents</div>
                <div class="kpi-value">{len(docs)}</div>
                <div class="kpi-sub">{'Contrôle actif' if rules_applied else 'Lecture seule'}</div>
            </div>
            """
        )
    st.write("")


def render_documents_table(documents: list[dict[str, Any]], statuses: dict[str, str] | None = None):
    if not documents:
        return
    STATUS_LABELS = {
        "natif": "Texte natif",
        "ocr": "OCR appliqué",
        "ocr_indisponible": "OCR indisponible",
        "erreur": "Erreur de lecture",
    }
    rows = []
    for d in documents:
        nom = d.get("nom", "")
        row = {
            "Document": _esc(nom),
            "Type détecté": _esc(d.get("type", "")),
            "Statut": _esc(d.get("statut", "")),
        }
        if statuses:
            st_label = STATUS_LABELS.get(statuses.get(nom, ""), statuses.get(nom, ""))
            row["Lecture"] = _esc(st_label)
        rows.append(row)
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def render_entities_panel(entites_extraites: dict[str, Any]):
    """Affiche proprement les entites extraites (dates, organisations, montants...).

    Les entites sont extraites automatiquement du texte : il s'agit des dates
    de lois ou d'actes cites, des organisations mentionnees, etc. Pour un
    document de type manuel/cours, ces elements sont informatifs et ne
    constituent pas des parties contractantes.
    """
    if not entites_extraites:
        st.html('<div class="tj-empty">Aucune entité extraite.</div>')
        return

    for doc_name, doc_entites in entites_extraites.items():
        with st.container(border=True):
            st.markdown(f"**{_esc(doc_name)}**")

            dates = doc_entites.get("dates", [])
            if dates:
                dates_unique = list(dict.fromkeys(d["valeur"] for d in dates))
                pills = "".join(f'<span class="tj-pill gold">📅 {_esc(d)}</span>' for d in dates_unique)
                st.html(
                    f'<div class="tj-entity-block"><div class="tj-entity-label">'
                    f'<span class="tj-entity-icon">📅</span> Dates</div>'
                    f'<div class="tj-entity-pills">{pills}</div></div>'
                )

            parties = doc_entites.get("parties", [])
            if parties:
                noms = list(dict.fromkeys(p.get("nom", "") for p in parties))
                pills = "".join(f'<span class="tj-pill">🏢 {_esc(n)}</span>' for n in noms)
                st.html(
                    f'<div class="tj-entity-block"><div class="tj-entity-label">'
                    f'<span class="tj-entity-icon">🏢</span> Organisations</div>'
                    f'<div class="tj-entity-pills">{pills}</div></div>'
                )

            montants = doc_entites.get("montants", [])
            if montants:
                vals = list(dict.fromkeys(m.get("valeur", "") for m in montants))
                pills = "".join(f'<span class="tj-pill">💰 {_esc(v)}</span>' for v in vals)
                st.html(
                    f'<div class="tj-entity-block"><div class="tj-entity-label">'
                    f'<span class="tj-entity-icon">💰</span> Montants</div>'
                    f'<div class="tj-entity-pills">{pills}</div></div>'
                )

            st.caption(
                "Ces entités sont extraites automatiquement du texte (dates de lois ou d'actes cités, "
                "organisations mentionnées...). Pour un manuel ou un cours, elles sont informatives : "
                "il ne s'agit pas de parties contractantes."
            )


def render_anomalie_card(index: int, anomalie: dict[str, Any]):
    priorite = anomalie.get("priorite", "alerte")
    label = {
        "bloquant": ("Bloquant", "tj-badge eleve"),
        "important": ("Important", "tj-badge moderate"),
        "alerte": ("Alerte", "tj-badge non-evalue"),
    }.get(priorite, ("Alerte", "tj-badge non-evalue"))
    badge = f'<span class="tj-badge {label[1]}">{label[0]}</span>'

    explication = anomalie.get("explication", "")
    nature = anomalie.get("nature_controle", "")
    source = anomalie.get("source_juridique", "")
    correction = anomalie.get("correction_recommandee", "")
    docs_a_verifier = anomalie.get("documents_a_verifier", [])

    lines = [f'<div class="tj-card"><div style="display:flex;justify-content:space-between;align-items:center;gap:0.5rem;">'
             f'<strong>Anomalie {index} — {_esc(nature)}</strong> {badge}</div>']
    if explication:
        lines.append(f"<p style='margin:0.5rem 0 0 0;'>{_esc(explication)}</p>")
    details = []
    if source:
        details.append(f"<b>Source :</b> {_esc(source)}")
        statut = anomalie.get("source_statut", "")
        labels = {
            "verifiee": "✅ vérifiée dans Légifrance (PISTE)",
            "introuvable": "⚠️ introuvable dans Légifrance",
            "erreur": "⚠️ erreur de vérification (service indisponible)",
            "non_configure": "ℹ️ vérification non configurée (mode lien)",
            "fictive": "⚠️ référence fictive à remplacer",
            "liee": "ℹ️ liée à Légifrance (mode lien)",
        }
        if statut in labels:
            details.append(f"<b>Vérification :</b> {labels[statut]}")
        texte_officiel = anomalie.get("texte_officiel", "")
        if statut == "verifiee" and texte_officiel:
            details.append(f"<b>Texte officiel :</b> «{_esc(texte_officiel)}…»")
    if correction:
        details.append(f"<b>Correction recommandée :</b> {_esc(correction)}")
    if docs_a_verifier:
        details.append(f"<b>Documents :</b> {_esc(', '.join(docs_a_verifier))}")
    if details:
        lines.append(f'<p style="margin:0.5rem 0 0 0;color:#5D6B82;font-size:0.88rem;">{"<br>".join(details)}</p>')
    lines.append("</div>")
    st.html("".join(lines))


def render_incoherence_card(index: int, incoherence: dict[str, Any]):
    type_inc = incoherence.get("type", "")
    severite = incoherence.get("severite", "")
    description = incoherence.get("description", "")
    champ = incoherence.get("champ", "")
    docs = incoherence.get("documents", [])
    if not docs and incoherence.get("document_1") and incoherence.get("document_2"):
        docs = [incoherence["document_1"], incoherence["document_2"]]

    sev_label = {
        "eleve": ("Élevée", "tj-badge eleve"),
        "moyen": ("Moyenne", "tj-badge moderate"),
        "faible": ("Faible", "tj-badge faible"),
    }.get(severite, ("—", "tj-badge non-evalue"))
    badge = f'<span class="tj-badge {sev_label[1]}">{sev_label[0]}</span>'

    parts = [f'<div class="tj-card"><strong>Incohérence {index} — {_esc(type_inc)}</strong> {badge}']
    if description:
        parts.append(f"<p style='margin:0.5rem 0 0 0;'>{_esc(description)}</p>")
    meta = []
    if champ:
        meta.append(f"<b>Champ :</b> {_esc(champ)}")
    if docs:
        meta.append(f"<b>Documents :</b> {_esc(' / '.join(docs))}")
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
