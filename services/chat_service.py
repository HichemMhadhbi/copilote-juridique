"""Service de chat - recherche precise dans le texte du document."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import services.llm_service as llm_service


def _normalize(text: str) -> str:
    """Supprime les accents et met en minuscules (crucial pour le francais)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _tokenize(text: str) -> list[str]:
    """Tokenise le texte en mots significatifs (mots et nombres)."""
    words = re.findall(r'\w{3,}', _normalize(text))
    stopwords = {
        "les", "des", "une", "est", "son", "ses", "ces", "aux", "par", "sur",
        "pas", "que", "qui", "dans", "pour", "avec", "sont", "mais", "plus",
        "tout", "bien", "aussi", "comme", "fait", "cette", "etre", "avoir",
        "nous", "vous", "ils", "elle", "leur", "leurs", "dont", "entre",
        "apres", "avant", "tres", "tous", "toute", "toutes", "autre",
        "autres", "meme", "memes", "alors", "donc", "ainsi", "car",
        "quels", "quelle", "quelles", "peut", "cette", "sont",
        "quoi", "quel", "comment", "pourquoi", "quand", "ou", "où",
    }
    return [w for w in words if w not in stopwords]


_JUNK_PATTERNS = [
    re.compile(r'^\s*fiche\s*\d+', re.IGNORECASE),
    re.compile(r'\bfiche\s*\d+\b', re.IGNORECASE),
    re.compile(r'^\s*\d+\s*$'),
    re.compile(r'^\s*\.indd'),
    re.compile(r'et la procédure\s*\d*\s*$', re.IGNORECASE),
]


def _is_junk_sentence(sentence: str) -> bool:
    """Detecte les phrases/en-tetes sans valeur informative (Fiche N, numeros de page...)."""
    if len(sentence) < 15:
        return True
    low = sentence.lower()
    if re.search(r'fiche\s*\d+', low):
        return True
    for pat in _JUNK_PATTERNS:
        if pat.search(sentence):
            return True
    return False


def _effective_score(score: int, sentence: str) -> int:
    """Penalise les phrases bruit (en-tetes) au lieu de les supprimer."""
    if not _is_junk_sentence(sentence):
        return score
    return max(score - 3, 0)


def _stem(word: str) -> str:
    """Approximation de stemmisation simple (pluriel)."""
    if word.endswith("s") and len(word) > 4:
        return word[:-1]
    return word


def _split_sentences(text: str) -> list[str]:
    """Decoupe le texte en phrases (titre, elements de liste, en-tetes)."""
    sentences: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = re.split(r'(?=\.(?=[A-ZÀ-Ý]))', line)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if len(p) > 400:
                sub = re.split(r'(?<=\.)\s+', p)
                for s in sub:
                    s = s.strip()
                    if s:
                        sentences.append(s)
            else:
                sentences.append(p)
    return sentences


def _join_as_lines(sentences: list[str], max_chars: int = 700) -> str:
    """Joint les phrases en lignes separees par des retours a la ligne (1 phrase = 1 ligne)."""
    lines: list[str] = []
    total = 0
    truncated = False
    for s in sentences:
        line = s.strip()
        if not line:
            continue
        if total + len(line) + (1 if lines else 0) > max_chars:
            truncated = True
            break
        lines.append(line)
        total += len(line) + (1 if lines else 0)
    if truncated:
        lines.append("...")
    return "\n".join(lines)


def _is_list_item(sentence: str) -> bool:
    """True si la phrase est un element de liste (commence par . - ou –)."""
    return sentence[:1] in (".", "-", "–")


def _word_matches(stem: str, word: str) -> bool:
    """Correspondance de mot : sous-chaine exacte, ou prefixe commun raisonnable."""
    if len(word) < 3 or len(stem) < 3:
        return False
    if stem in word:
        return True
    if len(word) >= 4 and word in stem:
        return True
    if len(stem) < 5:
        return False
    required = 5 if max(len(stem), len(word)) >= 8 else 4
    limit = min(len(stem), len(word), required)
    return limit >= 3 and stem[:limit] == word[:limit]


def _proximity_bonus(low: str, stems: list[str]) -> int:
    """Bonus de pertinence si plusieurs mots de la question sont proches dans la phrase.

    Une phrase où les termes de la question apparaissent à quelques mots d'intervalle
    (ex. « durée » et « pacte » dans « conclu pour une durée de dix années ») est plus
    probablement la réponse que des phrases où ces termes sont éparpillés.
    """
    words = re.findall(r'\w{3,}', low)
    positions = sorted(
        i for i, w in enumerate(words)
        if any(_word_matches(s, w) for s in stems)
    )
    for j in range(len(positions) - 1):
        if positions[j + 1] - positions[j] <= 8:
            return 1
    return 0


def _sliding_window_search(question: str, text: str, window: int = 600, step: int = 150, top_k: int = 10) -> list[str]:
    """Recherche par phrases - retourne les blocs de phrases les plus pertinentes."""
    question_words = _tokenize(question)
    if not question_words:
        return []

    sentences = _split_sentences(text)
    stems = [_stem(w) for w in question_words]
    normalized_sentences = [_normalize(s) for s in sentences]

    scored: list[tuple[int, int, str]] = []
    score_map: dict[int, int] = {}
    for i, sentence in enumerate(sentences):
        low = normalized_sentences[i]
        low_words = set(re.findall(r'\w{3,}', low))
        distinct = {
            _stem(w) for w in question_words
            if any(_word_matches(_stem(w), ww) for ww in low_words)
        }
        stripped = low.lstrip('.–- ')
        is_title = bool(stripped) and any(stripped.startswith(s) for s in distinct)
        score = len(distinct) + (1 if is_title else 0)
        score += _proximity_bonus(low, stems)
        if is_title and len(sentence) < 15:
            eff = score
        else:
            eff = _effective_score(score, sentence)
        if eff > 0:
            scored.append((eff, i, sentence))
            score_map[i] = eff

    scored.sort(key=lambda x: (-x[0], x[1]))

    selected: set[int] = set()
    for eff, i, _ in scored:
        if len(selected) >= top_k:
            break
        selected.add(i)

    if not selected:
        return []

    expanded: set[int] = set(selected)
    for i in sorted(selected):
        nxt = i + 1
        while nxt < len(sentences):
            nxt_sentence = sentences[nxt]
            if _is_list_item(nxt_sentence) and not _is_junk_sentence(nxt_sentence):
                expanded.add(nxt)
                nxt += 1
            else:
                break

    ordered = sorted(expanded)
    runs: list[list[int]] = []
    for i in ordered:
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])

    run_meta = []
    for run in runs:
        best = max(score_map.get(i, 0) for i in run)
        run_meta.append((best, run[0], run))

    results = []
    for best, first, run in sorted(run_meta, key=lambda m: (-m[0], m[1])):
        if results and best * 2 < results[0][0]:
            continue
        block_sentences = [sentences[i] for i in run]
        block = _join_as_lines(block_sentences)
        results.append((best, block))

    return [b for _, b in results[:top_k]]


def answer_question_from_report(question: str, report: dict[str, Any]) -> str:
    """Repond a une question : IA si une cle valide est disponible, sinon repli local."""
    local_answer = _answer_local(question, report)
    if llm_service.get_llm_config() is None:
        return local_answer
    try:
        llm_answer = _answer_with_llm(question, report)
    except Exception:
        llm_answer = None
    if llm_answer and llm_answer.strip():
        return llm_answer.strip()
    return local_answer


def _answer_with_llm(question: str, report: dict[str, Any]) -> str | None:
    """Tente une reponse enrichie par l'IA, basee sur les extraits pertinents."""
    document_text = report.get("informations_principales", {}).get("document_text", "")
    excerpts = _sliding_window_search(question, document_text) if document_text else []
    resume_like = any(
        w in _normalize(question)
        for w in ["resume", "resumer", "apercu", "sommaire", "executif", "point"]
    )
    if document_text and (not excerpts or resume_like):
        apercu = _join_as_lines(_split_sentences(document_text), max_chars=1600)
        if apercu:
            excerpts = list(excerpts) + ["Début du document :\n" + apercu]
    system, user = llm_service.build_chat_prompt(question, report, excerpts)
    return llm_service.call_llm(system, user)


def _answer_local(question: str, report: dict[str, Any]) -> str:
    question_lower = _normalize(question)

    anomalies = report.get("anomalies_juridiques", [])
    incoherences = report.get("incoherences", [])
    documents = report.get("documents_analyses", [])
    infos = report.get("informations_principales", {})
    entites = infos.get("entites_extraites", {})
    risque = report.get("niveau_risque_global", "non_evalue")
    document_text = infos.get("document_text", "")

    def _search_and_format(extra_header: str = "") -> str:
        if not document_text:
            return ""
        windows = _sliding_window_search(question, document_text)
        if not windows:
            return ""
        answer = ""
        if extra_header:
            answer += extra_header + "\n\n"
        for w in windows:
            answer += "".join(f"> {line}\n" for line in w.split("\n"))
            answer += "\n"
        answer += "---\n*Recherche basee sur le contenu du document.*"
        return answer

    # N'utilise pas "societe" comme declencheur : ce mot apparait dans la majorite
    # des questions (capital, parts, gerant...) et ne signifie pas qu'on cherche
    # a identifier les parties.
    if any(w in question_lower for w in ["partie", "parties", "personne", "personnes", "identite", "signataire"]):
        all_parties = []
        for doc_entites in entites.values():
            for p in doc_entites.get("parties", []):
                all_parties.append(p.get("nom", ""))
        answer = ""
        if all_parties:
            answer = f"**Parties identifiees :** {', '.join(set(all_parties))}\n\n"
        extra = _search_and_format("**Extraits du document :**")
        if extra:
            answer += extra
        elif not answer:
            return "Aucune partie specifique identifiee."
        return answer

    if any(w in question_lower for w in ["date", "dates", "echeance", "signature"]):
        all_dates = []
        for doc_entites in entites.values():
            for d in doc_entites.get("dates", []):
                all_dates.append(d.get("valeur", ""))
        answer = ""
        if all_dates:
            dates_unique = list(set(all_dates))
            answer = f"**Dates identifiees :** {', '.join(dates_unique)}\n\n"
        extra = _search_and_format("**Extraits du document :**")
        if extra:
            answer += extra
        elif not answer:
            return "Aucune date specifique identifiee."
        return answer

    if any(w in question_lower for w in ["montant", "montants", "euro", "financier", "capital"]):
        all_montants = []
        for doc_entites in entites.values():
            for m in doc_entites.get("montants", []):
                all_montants.append(m.get("valeur", ""))
        if all_montants:
            answer = f"**Montants identifies :** {', '.join(set(all_montants))}\n\n"
            extra = _search_and_format("**Contexte :**")
            if extra:
                answer += extra
            return answer
        extra = _search_and_format()
        if extra:
            return extra
        return "Aucun montant financier identifie."

    if any(w in question_lower for w in ["risque", "risques", "danger", "critique"]):
        if anomalies:
            lines = [f"**Niveau de risque global : {risque.upper()}**\n"]
            for a in anomalies:
                lines.append(f"- [{a.get('priorite', '').upper()}] {a.get('explication', '')}")
            return "\n".join(lines)
        return "**Niveau de risque :** Aucune anomalie detectee."

    if any(w in question_lower for w in ["incoherence", "incoherences", "contradiction"]):
        if incoherences:
            lines = ["**Incoherences detectees :**\n"]
            for inc in incoherences:
                lines.append(f"- **{inc.get('type', '')}** ({inc.get('severite', '')}) : {inc.get('description', '')}")
            return "\n".join(lines)
        return "Aucune incoherence detectee entre les documents."

    if any(w in question_lower for w in ["recommandation", "recommandations", "correction", "ameliorer"]):
        lines = ["**Recommandations :**\n"]
        for a in anomalies:
            correction = a.get("correction_recommandee", "")
            if correction:
                lines.append(f"- {correction}")
        if len(lines) > 1:
            return "\n".join(lines)
        extra = _search_and_format("**Recommandations du document :**")
        if extra:
            return extra
        return "Aucune recommandation specifique."

    if any(w in question_lower for w in ["resume", "resumer", "executif", "sommaire"]):
        n_docs = len(documents)
        n_anomalies = len(anomalies)
        answer = (
            f"**Resume :**\n"
            f"- {n_docs} document(s) analyse(s)\n"
            f"- Risque global : **{risque}**\n"
            f"- {n_anomalies} anomalie(s) detectee(s)\n"
            f"- Documents : {', '.join(d.get('nom', '') for d in documents)}\n\n"
        )
        if document_text:
            apercu = _join_as_lines(_split_sentences(document_text), max_chars=2000)
            answer += "**Apercu :**\n" + "\n".join(f"> {l}" for l in apercu.split("\n"))
        return answer

    if any(w in question_lower for w in ["reference", "legale", "loi", "article"]):
        refs = set()
        for a in anomalies:
            ref = a.get("source_juridique", "")
            if ref and "fictif" not in ref.lower():
                refs.add(ref)
        answer = ""
        if refs:
            answer = "**References juridiques :**\n" + "\n".join(f"- {r}" for r in sorted(refs)) + "\n\n"
        extra = _search_and_format("**Extraits du document :**")
        if extra:
            answer += extra
        elif not answer:
            return "Aucune reference juridique specifique."
        return answer

    if any(w in question_lower for w in ["conforme", "conformite"]):
        if anomalies:
            bloquants = [a for a in anomalies if a.get("priorite") == "bloquant"]
            if bloquants:
                return f"**Conformite :** {len(bloquants)} anomalie(s) bloquante(s)."
            return f"**Conformite :** {len(anomalies)} anomalie(s) a ameliorer."
        extra = _search_and_format("**Voici ce que le document dit a ce sujet :**")
        if extra:
            return extra
        return "**Conformite :** Aucune anomalie detectee."

    extra = _search_and_format("**Voici ce que le document dit a ce sujet :**")
    if extra:
        return extra

    return (
        f"Je n'ai pas trouve de reponse precise dans le document. "
        f"Le document contient {len(anomalies)} anomalie(s) avec un risque **{risque}**. "
        f"Essayez de reformuler."
    )
