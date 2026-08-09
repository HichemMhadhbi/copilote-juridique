"""
TOP-JURIDIQUE - Copilote IA Juridique
Point d'entree Streamlit.
Interface professionnelle : documents, analyse, chatbot.
"""

import streamlit as st

import services.llm_service as llm_service
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
    render_documents_table,
    render_entities_panel,
    render_anomalie_card,
    render_incoherence_card,
    render_question_preview,
    render_validation_summary,
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

    llm_cfg = llm_service.get_llm_config()
    if llm_cfg:
        st.sidebar.caption(
            f"Mode IA : **{llm_cfg['provider'].title()}** actif "
            "(réponses enrichies, repli automatique si échec)"
        )
    else:
        st.sidebar.caption("Mode IA : désactivé — réponses locales (ajoutez une clé dans .env)")

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
            label = doc_type if doc_type != "non_classe" else "non classé"
            st.sidebar.markdown(f"• **{name}** — {label}")
        if st.session_state.get("report_saved_to"):
            st.sidebar.caption(f"💾 Rapport enregistré : {st.session_state.report_saved_to}")

    render_saved_reports_section()
    return uploaded_files


def render_saved_reports_section():
    """Liste des rapports sauvegardés sur disque (reprise de dossier)."""
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

    render_section_title("Rapport d'analyse", "Synthèse de l'analyse juridique automatique")

    report = st.session_state.report
    render_metric_cards(report)

    synthese = report.get("synthese_intelligente")
    if synthese:
        render_section_title("Synthèse intelligente", "Analyse approfondie générée par IA")
        st.html(_md_to_html(synthese))

    st.divider()

    render_section_title("Documents analysés", "Typologie détectée automatiquement")
    render_documents_table(
        report.get("documents_analyses", []),
        report.get("informations_principales", {}).get("statut_lecture", {}),
    )

    docs_manquants = report.get("documents_manquants", [])
    if docs_manquants:
        st.warning(
            "**Documents manquants :** " + ", ".join(f"**{d}**" for d in docs_manquants)
            + "\n\nL'analyse comparative (pacte vs statuts) ne peut pas être complète "
            "sans ce document. À fournir pour une analyse exhaustive."
        )

    infos = report.get("informations_principales", {})
    qualites = infos.get("qualite_documents", {})
    problemes = [
        f"**{nom}** : {q.get('detail', '')}"
        for nom, q in qualites.items()
        if q.get("detail") != "lecture correcte"
    ]
    if problemes:
        st.warning("**Qualité de lecture des documents :**\n" + "\n".join(problemes))

    if infos.get("regles_controle_appliquees") is False:
        st.info(
            "**Aucun document de type pacte d'associés, statuts, procès-verbal ou "
            "modification statutaire détecté.** Les règles de contrôle spécifiques aux "
            "sociétés ne sont donc pas appliquées et aucune anomalie n'est rapportée : "
            "ce document est analysé en lecture (cours, manuel, contrat hors société...)."
        )

    sources = infos.get("sources_officielles", {})
    if sources:
        piste_ok = sources.get("piste_token_configured") is True
        verif_active = sources.get("verification_active") is True
        verifiees = sources.get("references_verifiees_piste", 0)
        st.info(
            f"**Sources officielles :** {sources.get('anomalies_liees_a_legifrance', 0)} "
            f"anomalie(s) liée(s) à Légifrance · Service PISTE "
            f"{'✅ configuré' if piste_ok else '⚠️ non configuré (recherche Légifrance en mode lien)'} "
            f"{'· vérification live active' if verif_active else ''} "
            f"{f'· {verifiees} référence(s) vérifiée(s) dans Légifrance' if verifiees else ''}"
            f"· {sources.get('anomalies_reference_fictive', 0)} référence(s) fictive(s) "
            f"signalée(s) à vérifier."
        )

    st.divider()

    render_section_title("Informations clés", "Entités extraites automatiquement du texte")
    render_entities_panel(infos.get("entites_extraites", {}))

    anomalies = report.get("anomalies_juridiques", [])
    if anomalies:
        st.divider()
        render_section_title(
            f"Anomalies juridiques ({len(anomalies)})",
            "Points de vigilance identifiés par les règles de contrôle",
        )
        for i, a in enumerate(anomalies, 1):
            render_anomalie_card(i, a)
        render_validation_section()

    incoherences = report.get("incoherences", [])
    if incoherences:
        st.divider()
        render_section_title(
            f"Incohérences entre documents ({len(incoherences)})",
            "Divergences relevées lors de la comparaison",
        )
        for i, inc in enumerate(incoherences, 1):
            render_incoherence_card(i, inc)

    st.divider()

    render_section_title("Export", "Téléchargez votre rapport au format PDF")
    pdf_bytes = st.session_state.get("report_pdf")
    if pdf_bytes is None:
        pdf_bytes = export_report_as_pdf(report)
        st.session_state["report_pdf"] = pdf_bytes
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
    for i, a in enumerate(anomalies, 1):
        finding_id = validation_service._finding_id(i)
        val = state.get(finding_id, {})
        statut = val.get("statut", "en_attente")
        statut_label = VALIDATION_STATUT_LABELS.get(statut, statut)
        nature = a.get("nature_controle", "Anomalie")
        with st.container(border=True):
            st.markdown(f"**Anomalie {i} — {nature}** · Statut : **{statut_label}**")
            if val.get("commentaire_juriste"):
                st.caption(f"Commentaire : {val['commentaire_juriste']}")
            if val.get("motif_rejet"):
                st.caption(f"Motif : {val['motif_rejet']}")
            c1, c2 = st.columns([1, 3])
            action = c1.selectbox(
                "Action",
                ("Approuver", "Rejeter", "Modifier"),
                index=0,
                key=f"val_action_{i}",
                label_visibility="collapsed",
            )
            if action == "Rejeter":
                comment = c2.text_input(
                    "Motif du rejet (obligatoire)", key=f"val_reason_{i}", placeholder="Pourquoi cette anomalie n'est pas retenue ?"
                )
            else:
                comment = c2.text_input(
                    "Commentaire (optionnel)", key=f"val_comment_{i}", placeholder="Précision du juriste..."
                )
            if st.button("Appliquer", key=f"val_btn_{i}", type="primary"):
                act_map = {"Approuver": "approuver", "Rejeter": "rejeter", "Modifier": "modifier"}
                try:
                    new_state = validation_service.apply_action(
                        report_id,
                        finding_id,
                        act_map[action],
                        comment=comment or "",
                        reason=comment or "",
                        current_state=st.session_state.validation_state,
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
