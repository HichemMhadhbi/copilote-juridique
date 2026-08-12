"""
TOP-JURIDIQUE - Copilote IA Juridique
Point d'entree Streamlit.
Interface professionnelle : documents, analyse, chatbot.
"""

import streamlit as st

from typing import Any

from config_app import TYPICAL_QUESTIONS, SUPPORTED_FORMATS
from services.document_service import extract_all_documents_with_status
from services.analysis_service import analyze_documents
from services.chat_service import answer_question_from_report
from services import storage_service, validation_service
from services.export_service import (
    export_report_as_pdf,
    export_conversation_as_text,
    export_conversation_as_pdf,
)
from ui.components import (
    render_hero_header,
    render_sidebar_header,
    render_status_banner,
    render_section_title,
    render_metric_cards,
    render_entities_panel,
    render_anomalie_card,
    render_incoherence_card,
    render_question_preview,
    render_validation_summary,
    TYPE_LABELS_HUMAIN,
    NATURE_CONTROLE_HUMAIN,
)
from ui.chat_display import render_chat_history, _md_to_html
from ui.styles import inject_global_styles

VALIDATION_STATUT_LABELS = {
    "en_attente": "⏳ En attente",
    "approuve": "✅ Approuvée",
    "rejete": "❌ Rejetée",
    "modifie": "✏️ Modifiée",
}


def init_session_state():
    defaults = {
        "conversation_history": [],
        "documents": {},
        "report": None,
        "analyzed": False,
        "doc_names": [],
        "doc_statuses": {},
        "validation_state": {},
        "report_saved_to": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session():
    report = st.session_state.get("report")
    if report:
        validation_service.reset_saved_state(report.get("rapport_id", "session"))
    st.session_state.conversation_history = []
    st.session_state.documents = {}
    st.session_state.report = None
    st.session_state.analyzed = False
    st.session_state.doc_names = []
    st.session_state.doc_statuses = {}
    st.session_state.validation_state = {}
    st.session_state.report_saved_to = None
    st.session_state.pop("report_pdf", None)
    for key in ("file_uploader", "mode_pills", "question_type_pills", "typical_question", "saved_report_select"):
        st.session_state.pop(key, None)


def render_sidebar():
    render_sidebar_header()

    st.sidebar.markdown("### Documents")
    uploaded_files = st.sidebar.file_uploader(
        "Fichiers à analyser",
        accept_multiple_files=True,
        type=list(SUPPORTED_FORMATS.keys()),
        key="file_uploader",
        label_visibility="collapsed",
    )
    formats_str = ", ".join(SUPPORTED_FORMATS.keys())
    st.sidebar.caption(f"Formats acceptés : {formats_str}")

    if st.sidebar.button("Analyser le dossier", type="primary", use_container_width=True):
        if not uploaded_files:
            st.sidebar.error("Veuillez d'abord déposer vos fichiers.")
        else:
            try:
                with st.spinner("Extraction du texte..."):
                    documents, statuses = extract_all_documents_with_status(uploaded_files)
                    st.session_state.documents = documents
                    st.session_state.doc_statuses = statuses
                    st.session_state.doc_names = list(documents.keys())
                with st.spinner("Analyse juridique en cours..."):
                    report = analyze_documents(documents, statuses)
                    st.session_state.report = report
                    st.session_state.analyzed = True
                    st.session_state.conversation_history = []
                    report_id = report.get("rapport_id", "session")
                    st.session_state.validation_state = validation_service.merge_with_saved(
                        report_id, validation_service.register_report_findings(report)
                    )
                    try:
                        st.session_state["report_pdf"] = export_report_as_pdf(report)
                    except Exception:
                        st.session_state["report_pdf"] = None
                    try:
                        st.session_state.report_saved_to = storage_service.save_report(report)
                    except Exception:
                        st.session_state.report_saved_to = None
                    st.sidebar.success(f"{len(documents)} document(s) analysé(s)")
                    st.rerun()
            except Exception as e:
                st.sidebar.error(f"Erreur : {e}")

    if st.sidebar.button("Réinitialiser", use_container_width=True):
        reset_session()
        st.rerun()

    if st.session_state.analyzed:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Dossier analysé")
        types = (
            st.session_state.report.get("informations_principales", {})
            .get("types_documents", {})
        )
        for name, doc_type in types.items():
            label = TYPE_LABELS_HUMAIN.get(doc_type, doc_type or "Non reconnu")
            st.sidebar.markdown(f"• **{name}** — {label}")
        if st.session_state.get("report_saved_to"):
            st.sidebar.caption(f"💾 Rapport enregistré : {st.session_state.report_saved_to}")

    render_saved_reports_section()
    return uploaded_files


def render_saved_reports_section():
    """Liste des rapports sauvegardés sur disque (reprise de dossier)."""
    if not storage_service.reports_enabled():
        return
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Rapports enregistrés")
    reports = storage_service.list_reports()
    if not reports:
        st.sidebar.caption("Aucun rapport sauvegardé pour l'instant.")
        return
    labels = {}
    for r in reports:
        date = (r.get("date_analyse") or "")[:16]
        n = r.get("nombre_anomalies", 0)
        labels[f"{date} — {r.get('rapport_id', '')[:8]} ({r.get('nombre_documents', 0)} doc., {n} anomalie(s))"] = r.get("rapport_id")
    selected = st.sidebar.selectbox(
        "Rapport sauvegardé", list(labels.keys()), key="saved_report_select", label_visibility="collapsed"
    )
    if st.sidebar.button("Charger le rapport", use_container_width=True):
        rid = labels.get(selected)
        if rid:
            report = storage_service.load_report(rid)
            if report:
                st.session_state.report = report
                st.session_state.analyzed = True
                st.session_state.documents = {}
                st.session_state.doc_statuses = report.get("informations_principales", {}).get("statut_lecture", {})
                st.session_state.doc_names = [d.get("nom", "") for d in report.get("documents_analyses", [])]
                st.session_state.conversation_history = []
                st.session_state.validation_state = validation_service.merge_with_saved(
                    rid, validation_service.register_report_findings(report)
                )
                try:
                    st.session_state["report_pdf"] = export_report_as_pdf(report)
                except Exception:
                    st.session_state["report_pdf"] = None
                st.session_state.report_saved_to = next(
                    (r.get("chemin") for r in reports if r.get("rapport_id") == rid), None
                )
                st.sidebar.success("Rapport chargé.")
                st.rerun()


def require_analyzed() -> bool:
    if not st.session_state.analyzed or st.session_state.report is None:
        st.info(
            "Déposez vos documents dans le panneau de gauche puis cliquez sur "
            "**Analyser le dossier** pour générer le rapport."
        )
        return False
    return True


def render_analysis_mode():
    if not require_analyzed():
        return

    render_section_title("Analyse du dossier", "Contrôle juridique automatique de vos documents")

    report = st.session_state.report
    render_metric_cards(report)

    synthese = report.get("synthese_intelligente")
    if synthese:
        render_section_title("Synthèse de l'analyse", "Résumé clair et actionnable du dossier")
        report_id = report.get("rapport_id", "session")
        synth_key = f"synth_editee_{report_id}"
        if synth_key not in st.session_state:
            st.session_state[synth_key] = synthese
        with st.expander("✏️ Modifier la synthèse (optionnel)"):
            st.caption(
                "La synthèse est générée automatiquement à partir des documents "
                "analysés. Le juriste peut la corriger avant export."
            )
            edited = st.text_area("Texte de la synthèse", height=200, key=synth_key)
            if st.button("Enregistrer la synthèse", key=f"synth_save_{report_id}"):
                st.session_state[synth_key] = edited.strip() or synthese
                st.rerun()
        st.html(_md_to_html(st.session_state[synth_key]))

    docs_manquants = report.get("documents_manquants", [])
    if docs_manquants:
        st.warning(
            "**Documents manquants :** " + ", ".join(f"**{d}**" for d in docs_manquants)
            + "\n\nL'analyse comparative (pacte vs statuts) ne peut pas être complète "
            "sans ce document. À fournir pour une analyse exhaustive."
        )

    infos = report.get("informations_principales", {})
    qualites = infos.get("qualite_documents", {})
    _QUALITE_DETAIL_LABELS = {
        "illisible": "document illisible",
        "ocr_faible": "texte difficilement lisible — à vérifier",
        "page_manquante": "page manquante probable",
        "incomplet": "document peut-être incomplet",
    }
    problemes = []
    for nom, q in qualites.items():
        detail = q.get("detail", "")
        if detail == "lecture correcte":
            continue
        human = "; ".join(
            _QUALITE_DETAIL_LABELS.get(part.strip(), part.strip())
            for part in detail.split(";")
        )
        problemes.append(f"**{nom}** : {human}")
    if problemes:
        st.warning("**Qualité de lecture des documents :**\n" + "\n".join(problemes))

    if infos.get("regles_controle_appliquees") is False:
        st.info(
            "**Aucun document de société (pacte d'associés, statuts, procès-verbal ou "
            "modification statutaire) n'a été détecté.** Les contrôles juridiques "
            "spécifiques aux sociétés ne s'appliquent donc pas à ce dossier."
        )

    st.divider()

    render_section_title(
        "Points clés des documents",
        "Informations essentielles extraites automatiquement (société, associés, montants, dates)",
    )
    render_entities_panel(infos.get("entites_extraites", {}))

    anomalies = report.get("anomalies_juridiques", [])
    if anomalies:
        st.divider()
        render_section_title(
            f"Anomalies juridiques ({len(anomalies)})",
            "Points de vigilance identifiés par les règles de contrôle",
        )
        docs_by_name = {
            d.get("nom", ""): TYPE_LABELS_HUMAIN.get(d.get("type", ""), d.get("type", ""))
            for d in report.get("documents_analyses", [])
        }
        state_val = st.session_state.get("validation_state") or {}
        for i, a in enumerate(anomalies, 1):
            a_aff = dict(a)
            statut_val = ""
            val = state_val.get(f"anomalie_{i}", {})
            if val.get("statut") == "modifie" and val.get("nouveau_contenu"):
                statut_val = "modifie"
                nc = val["nouveau_contenu"]
                if nc.get("explication"):
                    a_aff["explication"] = nc["explication"]
                if nc.get("correction_recommandee"):
                    a_aff["correction_recommandee"] = nc["correction_recommandee"]
            render_anomalie_card(i, a_aff, docs_by_name, statut_validation=statut_val)
        render_validation_section()

    comparaison_ecartee = report.get("comparaison_ecartee")
    if comparaison_ecartee:
        st.divider()
        st.warning(comparaison_ecartee)

    incoherences = report.get("incoherences", [])
    if incoherences:
        st.divider()
        render_section_title(
            f"Incohérences entre documents ({len(incoherences)})",
            "Divergences relevées entre le pacte d'associés et les statuts",
        )
        for i, inc in enumerate(incoherences, 1):
            render_incoherence_card(i, inc)

    st.divider()

    render_section_title("Export", "Téléchargez votre rapport au format PDF")
    report_export = _rapport_avec_validations(
        report, st.session_state.get("validation_state") or {}
    )
    pdf_bytes = export_report_as_pdf(report_export)
    from datetime import datetime
    st.download_button(
        "📄 Télécharger le rapport (PDF)",
        data=pdf_bytes,
        file_name=f"rapport_analyse_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        help="Rapport professionnel en PDF, prêt à partager ou imprimer.",
    )


def _validations_pour_export(report: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    """Liste des validations faites par le juriste, à intégrer au rapport exporté."""
    result: list[dict[str, Any]] = []
    for i, a in enumerate(report.get("anomalies_juridiques", []), 1):
        val = state.get(f"anomalie_{i}", {})
        statut = val.get("statut", "en_attente")
        if statut == "en_attente":
            continue
        result.append({
            "numero": i,
            "nature": NATURE_CONTROLE_HUMAIN.get(
                a.get("nature_controle", ""), a.get("nature_controle", "Anomalie")
            ),
            "statut": statut,
            "commentaire_juriste": val.get("commentaire_juriste", ""),
            "motif_rejet": val.get("motif_rejet", ""),
            "nouveau_contenu": val.get("nouveau_contenu") or {},
        })
    return result


def _rapport_avec_validations(report: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Copie du rapport prête pour l'export :
    - les anomalies « modifiées » sont remplacées par le texte corrigé du juriste
      (comme dans l'interface) ;
    - la liste des validations est ajoutée pour la section « Validation humaine ».
    """
    rapport = dict(report)
    anomalies = []
    for i, a in enumerate(report.get("anomalies_juridiques", []), 1):
        a_aff = dict(a)
        val = state.get(f"anomalie_{i}", {})
        if val.get("statut") == "modifie" and val.get("nouveau_contenu"):
            nc = val["nouveau_contenu"]
            if nc.get("explication"):
                a_aff["explication"] = nc["explication"]
            if nc.get("correction_recommandee"):
                a_aff["correction_recommandee"] = nc["correction_recommandee"]
            a_aff["statut_validation"] = "modifie"
        anomalies.append(a_aff)
    rapport["anomalies_juridiques"] = anomalies
    rapport["validations_appliquees"] = _validations_pour_export(report, state)
    return rapport


def render_validation_section():
    """Panneau de validation humaine : le juriste approuve / rejette / modifie
    chaque anomalie détectée avant qu'elle ne soit intégrée au rapport final."""
    report = st.session_state.report
    report_id = report.get("rapport_id", "session")
    state = st.session_state.get("validation_state") or {}
    if not state:
        return

    st.divider()
    render_section_title(
        "Validation humaine", "Le juriste confirme chaque anomalie avant intégration au rapport"
    )
    render_validation_summary(validation_service.summary(report_id, state))

    anomalies = report.get("anomalies_juridiques", [])
    priorite_labels = {
        "bloquant": "Bloquant",
        "important": "Important",
        "alerte": "Alerte",
    }

    en_attente = sum(
        1 for v in state.values() if v.get("statut", "en_attente") == "en_attente"
    )
    if en_attente > 1:
        with st.expander("⚡ Actions groupées", expanded=True):
            st.caption(
                f"{en_attente} anomalie(s) en attente : approuvez ou rejetez "
                "l'ensemble en un clic, puis affinez au cas par cas."
            )
            comment_bulk = st.text_input(
                "Commentaire commun (optionnel)",
                key="val_bulk_comment",
                placeholder="Ex. : Validé après relecture par le cabinet.",
            )
            b1, b2 = st.columns(2)
            if b1.button("✅ Approuver tout", type="primary", use_container_width=True):
                try:
                    new_state = validation_service.apply_bulk_action(
                        report_id,
                        "approuver",
                        comment=comment_bulk or "",
                        current_state=st.session_state.validation_state,
                    )
                    st.session_state.validation_state = new_state
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            if b2.button("❌ Tout rejeter", use_container_width=True):
                try:
                    new_state = validation_service.apply_bulk_action(
                        report_id,
                        "rejeter",
                        comment=comment_bulk or "",
                        current_state=st.session_state.validation_state,
                    )
                    st.session_state.validation_state = new_state
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    for i, a in enumerate(anomalies, 1):
        finding_id = validation_service._finding_id(i)
        val = state.get(finding_id, {})
        statut = val.get("statut", "en_attente")
        statut_label = VALIDATION_STATUT_LABELS.get(statut, statut)
        nature = NATURE_CONTROLE_HUMAIN.get(a.get("nature_controle", ""), a.get("nature_controle", "Anomalie"))
        priorite = priorite_labels.get(a.get("priorite", ""), a.get("priorite", ""))
        explication = a.get("explication", "")
        docs_a_verifier = a.get("documents_a_verifier", [])

        with st.container(border=True):
            st.markdown(f"**Anomalie {i} — {nature}** · Statut : **{statut_label}**")
            apercu = explication if len(explication) <= 170 else explication[:170] + "…"
            infos = []
            if priorite:
                infos.append(priorite)
            if apercu:
                infos.append(apercu)
            if docs_a_verifier:
                infos.append(", ".join(docs_a_verifier))
            st.caption(" · ".join(infos))

            if statut != "en_attente":
                if val.get("commentaire_juriste"):
                    st.caption(f"Commentaire : {val['commentaire_juriste']}")
                if val.get("motif_rejet"):
                    st.caption(f"Motif : {val['motif_rejet']}")
                if statut == "modifie" and val.get("nouveau_contenu"):
                    nc = val["nouveau_contenu"]
                    st.caption("✏️ Contenu corrigé par le juriste :")
                    if nc.get("explication"):
                        st.caption(nc["explication"])
                    if nc.get("correction_recommandee"):
                        st.caption(nc["correction_recommandee"])
                if st.button("↩️ Remettre en attente", key=f"val_reset_{i}"):
                    reste = {
                        k: v for k, v in st.session_state.validation_state.items()
                        if k != finding_id
                    }
                    reste[finding_id] = {
                        "finding_id": finding_id,
                        "statut": "en_attente",
                        "action": "en_attente",
                    }
                    st.session_state.validation_state = reste
                    st.rerun()
                continue

            c1, c2 = st.columns([1, 3])
            action = c1.selectbox(
                "Action",
                ("Approuver", "Rejeter", "Modifier"),
                index=0,
                key=f"val_action_{i}",
                label_visibility="collapsed",
            )
            nouveau_contenu = None
            if action == "Rejeter":
                comment = c2.text_input(
                    "Motif du rejet (obligatoire)", key=f"val_reason_{i}", placeholder="Pourquoi cette anomalie n'est pas retenue ?"
                )
            elif action == "Modifier":
                st.caption(
                    "**Correction du texte par le juriste** : le contenu corrigé "
                    "remplace l'original dans le rapport."
                )
                expl_mod = st.text_area(
                    "Nouvelle explication",
                    key=f"val_edit_expl_{i}",
                    value=a.get("explication", ""),
                    height=90,
                )
                corr_mod = st.text_area(
                    "Nouvelle correction recommandée",
                    key=f"val_edit_corr_{i}",
                    value=a.get("correction_recommandee", ""),
                    height=70,
                )
                comment = st.text_input(
                    "Commentaire (optionnel)", key=f"val_comment_{i}", placeholder="Précision du juriste..."
                )
                nouveau_contenu = {
                    "explication": expl_mod,
                    "correction_recommandee": corr_mod,
                }
            else:
                comment = c2.text_input(
                    "Commentaire (optionnel)", key=f"val_comment_{i}", placeholder="Précision du juriste..."
                )
            if st.button("Appliquer", key=f"val_btn_{i}", type="primary"):
                act_map = {"Approuver": "approuver", "Rejeter": "rejeter", "Modifier": "modifier"}
                try:
                    kwargs: dict[str, Any] = {"current_state": st.session_state.validation_state}
                    if action == "Modifier":
                        nouveau_contenu["commentaire_juriste"] = comment or ""
                        kwargs["new_content"] = nouveau_contenu
                    elif action == "Rejeter":
                        kwargs["reason"] = comment or ""
                    else:
                        kwargs["comment"] = comment or ""
                    new_state = validation_service.apply_action(
                        report_id, finding_id, act_map[action], **kwargs
                    )
                    st.session_state.validation_state = new_state
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


def submit_question(user_question: str) -> bool:
    if not user_question.strip():
        return False

    report = st.session_state.report
    answer = answer_question_from_report(user_question, report)

    from datetime import datetime
    st.session_state.conversation_history.append({
        "question": user_question.strip(),
        "answer": answer,
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    return True


def render_chat_mode():
    if not require_analyzed():
        return

    render_section_title("Posez vos questions", "Interrogez le contenu du document analysé")

    render_chat_history(st.session_state.conversation_history)

    st.divider()
    st.caption("Nouvelle question :")

    question_type = st.pills(
        "Type de question",
        ("Question libre", "Question typique"),
        key="question_type_pills",
        label_visibility="collapsed",
    )

    if question_type == "Question typique":
        selected = st.selectbox(
            "Question prédéfinie",
            list(TYPICAL_QUESTIONS.keys()),
            key="typical_question",
            label_visibility="collapsed",
        )
        user_question = TYPICAL_QUESTIONS[selected]
        render_question_preview(user_question)

        if st.button("Envoyer la question", type="primary", use_container_width=True):
            if submit_question(user_question):
                st.rerun()
    else:
        user_question = st.chat_input("Posez votre question juridique...")
        if user_question:
            if submit_question(user_question):
                st.rerun()

    if st.session_state.conversation_history:
        st.divider()
        conv_txt = export_conversation_as_text(st.session_state.conversation_history)
        try:
            conv_pdf = export_conversation_as_pdf(st.session_state.conversation_history)
        except Exception:
            conv_pdf = None
        if conv_pdf is not None:
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button(
                    "💬 Conversation (TXT)",
                    data=conv_txt,
                    file_name="conversation.txt",
                    use_container_width=True,
                )
            with col_b:
                st.download_button(
                    "📄 Conversation (PDF)",
                    data=conv_pdf,
                    file_name="conversation.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.download_button(
                "💬 Exporter la conversation (TXT)",
                data=conv_txt,
                file_name="conversation.txt",
                use_container_width=True,
            )


def main():
    st.set_page_config(
        page_title="TOP-JURIDIQUE — Copilote IA Juridique",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session_state()
    inject_global_styles()

    render_hero_header()
    render_sidebar()
    render_status_banner(st.session_state.analyzed, len(st.session_state.doc_names))

    st.caption("Choisissez votre espace :")
    mode = st.pills(
        "Espace",
        ("📋 Analyse du dossier", "💬 Poser des questions"),
        key="mode_pills",
        label_visibility="collapsed",
    )

    if mode == "💬 Poser des questions":
        render_chat_mode()
    else:
        render_analysis_mode()


if __name__ == "__main__":
    main()
