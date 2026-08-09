# Architecture du Copilote IA Juridique — TOP-JURIDIQUE

> **Guide d'explication du projet, du rôle de chaque fichier et de la démarche d'une analyse.**
> Stage TOP-JURIDIQUE — Prototype fonctionnel. Interface : français.

---

## 1. Vue d'ensemble

Le projet est un **copilote IA juridique** qui :
1. Reçoit des **documents de société** (pactes d'associés, statuts, procès-verbaux, modifications statutaires…)
2. **Extrait** les informations clés (dates, montants, parties, clauses)
3. **Compare** les documents entre eux pour détecter les incohérences
4. Applique des **règles juridiques** pour détecter les anomalies
5. Rattache des **références juridiques** (base de connaissances contrôlée)
6. Génère un **rapport professionnel** (JSON / Markdown / PDF)
7. Soumet chaque conclusion à une **validation humaine obligatoire**

Le point d'architecture le plus important : le projet expose **3 interfaces** (web, ligne de commande, API REST) qui partagent **un seul et même pipeline métier**. Il n'y a pas de logique dupliquée.

---

## 2. Architecture générale

```
                3 INTERFACES                         1 PIPELINE MÉTIER
        ┌─────────────────────────────┐      ┌──────────────────────────────────┐
        │  app.py   (interface web)   │      │                                  │
        │  main.py  (ligne de commande)│───→ │      services/  (orchestration)  │
        │  api/     (API REST)        │      │                                  │
        └─────────────────────────────┘      └──────────────────────────────────┘
                                                    │
        ┌───────────────────────────────────────────┼──────────────────────────┐
        ▼                ▼                 ▼                ▼                ▼
   ┌───────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  ┌────────────┐
   │  INGESTION │  │ EXTRACTION │  │  RÈGLES     │  │  RAPPORT   │  │ VALIDATION │
   │ document_  │  │ entity_    │  │ rules.py    │  │ report_    │  │ validator  │
   │ service    │  │ clause_    │  │ rule_       │  │ builder    │  │            │
   │ ocr_engine │  │ extractor  │  │ checker     │  │ report_    │  │            │
   │            │  │            │  │             │  │ export     │  │            │
   └────────────┘  └─────┬───────┘  └──────┬──────┘  └─────┬──────┘  └────────────┘
                        │                  │              │
                        ▼                  ▼              ▼
                   ┌──────────────────────────────────────────────┐
                   │  COMPARAISON   │  BASE JURIDIQUE  │  LLM      │
                   │  document_     │  legal_kb/       │  llm_     │
                   │  comparator    │  (données .json) │  service  │
                   └──────────────────────────────────────────────┘
```

---

## 3. Rôle de chaque fichier, dossier par dossier

### 3.1 Points d'entrée (racine)

| Fichier | Rôle |
|---|---|
| `app.py` | **Interface web Streamlit** : upload des fichiers, affichage du rapport, chat documentaire, validation humaine. |
| `main.py` | **Interface ligne de commande** : `python main.py --upload-dir ... --mode rapide|complet|avance`. Idéal pour tester et pour l'intégration. |
| `api/endpoints.py` | **API REST FastAPI** : `POST /analyze`, `GET /report/{id}`, `POST /validate/{id}/{finding_id}`, `GET /health`. Prête pour une intégration dans la plateforme TOP-JURIDIQUE. |

### 3.2 Configuration (racine)

| Fichier | Rôle |
|---|---|
| `config.py` | Énumérations métier : `TypeDocument` (pacte, statuts, PV…) et `Priorite` (bloquant, important, alerte). Utilisées par le moteur de règles et le rapport. |
| `config_app.py` | Config applicative : formats acceptés (PDF, Word, image, texte), modèles LLM, questions typiques, et **lecture des clés API depuis `.env`** (aucune clé dans le code). |
| `.env` / `.env.example` | Stocke les clés API (GROQ_API_KEY, OPENROUTER_API_KEY). Le `.env` est ignoré par Git. |
| `requirements.txt` | Dépendances Python du projet. |

### 3.3 `services/` — le cœur : orchestration du pipeline

Ce dossier contient toute la logique métier, appelée par les 3 interfaces.

| Fichier | Rôle |
|---|---|
| `document_service.py` | **Ingestion** : lit un PDF (natif ou scanné), un Word, une image ou un texte ; extrait le contenu ; **détecte le type de document** (pacte, statuts, PV…). Gère proprement le cas où l'OCR n'est pas disponible. |
| `analysis_service.py` | **Orchestrateur principal** : enchaîne l'extraction → la comparaison → les règles juridiques → la base juridique → la construction du rapport. Point central de toute analyse. |
| `chat_service.py` | **Question / Réponse documentaire** : l'utilisateur pose une question sur son rapport ; le système cherche les passages pertinents puis rédige la réponse (avec ou sans LLM). |
| `validation_service.py` | **Validation humaine** : approuver / rejeter chaque anomalie avec un commentaire du juriste. |
| `storage_service.py` | **Persistance** : sauvegarde et charge les rapports en JSON dans le dossier `reports/`. |
| `export_service.py` | **Export du rapport** au format Markdown, PDF ou JSON. |
| `legal_source_service.py` | **Sources juridiques** : retrouve les textes de loi / liens Légifrance associés à une anomalie. |
| `llm_service.py` | **Appels aux modèles de langage** avec **repli automatique** : Groq (prioritaire) → OpenRouter (secours) → génération locale (dernier recours). |

### 3.4 `extraction/` — lecture intelligente des documents

| Fichier | Rôle |
|---|---|
| `entity_extractor.py` | Extrait les **entités** : dates, montants, parties, société, capital social, durée… |
| `clause_extractor.py` | Découpe le texte en **clauses / articles** (avec leur titre et leur position). |

### 3.5 `comparison/` — comparaison inter-documents

| Fichier | Rôle |
|---|---|
| `document_comparator.py` | **Compare 2 documents entre eux** (ex. pacte d'associés vs statuts) : dates, montants, parties, clauses. Produit des **incohérences** avec un niveau de gravité. |

### 3.6 `rules_engine/` — la logique juridique

| Fichier | Rôle |
|---|---|
| `rules.py` | Les **règles de contrôle** elles-mêmes (16) : agrément de cession de parts, clause de non-concurrence, majorité des décisions, veto bloquant, cohérence pacte/statuts, responsabilité du gérant… + **règles de risques futurs** (valorisation des titres en sortie, décès/incapacité d'un associé, non-paiement). Comparaisons insensibles aux accents. |
| `rule_checker.py` | **Applique les règles** sur les données extraites et produit les anomalies. Gère correctement les cas où un seul document est présent (les règles concernées ne tournent que si le document existe). |

### 3.7 `legal_kb/` — base de connaissances juridique

| Fichier | Rôle |
|---|---|
| `knowledge_base.py` | Charge la base juridique (18 entrées) et fournit la **recherche RAG-lite** `search_relevant` : pour chaque anomalie, les entrées pertinentes sont classées par type de document + termes + domaine, sans service cloud. |
| `data/societes.json` | Références du droit des sociétés (Code de commerce). |
| `data/pactes.json` | Références des pactes d'associés. |
| `schema.json` | Schéma (format) des entrées de la base. |

> ✔️ Les 18 entrées sont des **références réelles**, interrogées par le pipeline (RAG-lite) et rattachées à Légifrance via `services/legal_source_service.py` (lien de recherche ou vérification officielle PISTE si configuré). Aucune référence n'est inventée.

### 3.8 `report_generator/` — génération du rapport

| Fichier | Rôle |
|---|---|
| `report_builder.py` | Construit le **rapport structuré** : documents analysés, **documents manquants**, incohérences, anomalies, niveau de risque global. |
| `report_export.py` | Convertit le rapport en **Markdown** (lisible par un juriste) et en **PDF**. |

### 3.9 `validation/` — validation humaine

| Fichier | Rôle |
|---|---|
| `validator.py` | Gère le **statut de validation** de chaque anomalie : « à valider », « approuvée », « rejetée », avec commentaire. |

### 3.10 `ingestion/` — OCR

| Fichier | Rôle |
|---|---|
| `ocr_engine.py` | OCR pour les **PDF scannés**. Si Tesseract n'est pas installé, le système ne plante pas : il retourne un message « OCR indisponible » et marque le statut `ocr_indisponible`. |

### 3.11 `ui/` — composants de l'interface web

| Fichier | Rôle |
|---|---|
| `components.py` | Composants Streamlit : zone d'upload, cartes d'anomalies, sections du rapport. |
| `styles.py` | Styles CSS de l'interface. |
| `chat_display.py` | Affichage de l'historique du chat documentaire. |

### 3.12 `tests/` — validation automatisée

| Fichier | Rôle |
|---|---|
| `test_extraction.py` | Extraction des entités et clauses. |
| `test_rules_engine.py` | Règles juridiques, y compris les cas mono-document et la robustesse aux accents. |
| `test_comparison.py` | Comparaison entre documents. |
| `test_analysis_service.py` | Pipeline d'analyse complet (documents à vérifier, documents manquants). |
| `test_llm_fallback.py` | Repli LLM sans clé API. |

> **164 tests** unitaires, tous verts : `python -m pytest tests -q`

### 3.13 Documentation et livrables

| Dossier | Contenu |
|---|---|
| `docs/` | Documents de conception : mission, benchmark, cas d'usage, architecture, base juridique, intégration. |
| `examples/rapport_exemple.md` | Exemple concret de rapport de contrôle. |
| `livrables_stage/` | Livrables : analyse du travail, benchmark des solutions IA, mail d'avancement. |
| `reports/` | Rapports sauvegardés en JSON (persistance). |
| `output/` | Rapports exportés (Markdown). |

---

## 4. La démarche : cycle de vie d'une analyse

Voici le chemin exact d'un document, du dépôt au rapport final.

### Étape 1 — Ingestion (dépôt du document)
**Fichiers :** `document_service.py`, `ingestion/ocr_engine.py`

Le fichier est lu. S'il s'agit d'un PDF scanné sans texte, l'OCR est tenté (sinon repli gracieux). Le **type de document** est détecté automatiquement (pacte d'associés, statuts, PV, modification statutaire…).

Si le dossier contient des documents de société mais **pas de statuts** (document de référence obligatoire), ceux-ci sont signalés dans `report.documents_manquants` — l'analyse comparative pacte/statuts ne peut pas être complète sans eux.

### Étape 2 — Extraction structurée
**Fichiers :** `extraction/entity_extractor.py`, `extraction/clause_extractor.py`

On transforme le texte brut en **données structurées** : dates, montants, parties, société, et liste de clauses. C'est ce qui permet ensuite une analyse déterministe (non aléatoire).

### Étape 3 — Comparaison inter-documents
**Fichiers :** `comparison/document_comparator.py`

Si plusieurs documents sont fournis (ex. pacte **et** statuts), on les **croise** : dates de signature, capital, répartition des parts, clauses contradictoires → production d'**incohérences**.

### Étape 4 — Règles juridiques
**Fichiers :** `rules_engine/rules.py`, `rules_engine/rule_checker.py`

Chaque document est passé au crible des **règles de contrôle**. Chaque anomalie détectée (clause manquante, risque, contradiction) reçoit : explication, priorité, conséquence, correction recommandée, source juridique.

### Étape 5 — Références juridiques (RAG-lite)
**Fichiers :** `legal_kb/knowledge_base.py`, `services/legal_source_service.py`

Chaque anomalie **interroge la base juridique** (`search_relevant`) : type de document + termes de l'anomalie + domaine → les entrées pertinentes (articles, règles de contrôle associées) sont rattachées à l'anomalie. Le rapport indique le nombre d'entrées mobilisées. Ensuite, `legal_source_service.py` relie chaque référence à Légifrance (lien de recherche, ou vérification officielle via PISTE si configuré). Base contrôlée → aucune hallucination du LLM.

### Étape 5 bis — Analyse des clauses (IA)
**Fichiers :** `services/llm_service.py`

Chaque clause du pacte/statuts reçoit un niveau de risque (faible / modéré / élevé), une **analyse** et une **amélioration argumentée**, avec le fondement juridique. En l'absence de clé API, l'analyse locale déterministe garantit un rendu identique (aucun blocage).

### Étape 6 — Génération du rapport
**Fichiers :** `report_generator/report_builder.py`, `report_generator/report_export.py`, `services/export_service.py`

Le rapport structuré est construit : documents analysés, incohérences, anomalies, **niveau de risque global** (faible / modéré / élevé). Il est sauvegardé en JSON (`storage_service.py`) et exporté en Markdown / PDF.

### Étape 7 — Validation humaine
**Fichiers :** `validation/validator.py`, `services/validation_service.py`

Le juriste examine chaque anomalie et la **valide ou la rejette** avec un commentaire. L'IA propose, **l'homme décide** — c'est un choix clé pour un outil juridique.

### Étape 8 — (Optionnel) Enrichissement IA
**Fichiers :** `services/llm_service.py`, `services/chat_service.py`

Si une clé API est configurée, le LLM peut rédiger les explications en langage naturel ou répondre aux questions sur le rapport. Sans clé, le système fonctionne **entièrement en mode déterministe** (repli local).

---

## 5. Le module LLM et son repli

L'appel à l'IA est conçu pour **ne jamais bloquer l'analyse** :

```
Groq (llama-3.3-70b)  →  OpenRouter (secours)  →  Génération locale (dernier recours)
```

- Les clés API sont lues dans `.env` (jamais dans le code).
- Le pipeline d'analyse (étapes 1 à 7) ne dépend **pas** du LLM : il est déterministe.
- Le LLM sert uniquement à **enrichir** (rédaction, Q&A). S'il est indisponible, on bascule sur des modèles de réponse locaux.

---

## 6. Choix techniques à mettre en avant

| Choix | Pourquoi |
|---|---|
| **1 pipeline, 3 interfaces** | Pas de code dupliqué, comportement identique partout |
| **Règles déterministes** | Résultats reproductibles et expliquables (important en droit) |
| **RAG-lite** | Chaque anomalie mobilise réellement la base juridique (articles + règles de contrôle) sans service cloud |
| **Analyse des clauses (IA)** | Chaque clause reçoit risque + analyse + amélioration argumentée, avec repli local |
| **Références juridiques contrôlées** | Pas d'invention du LLM, fiabilité, vérification officielle Légifrance/PISTE |
| **Validation humaine obligatoire** | L'IA assiste, le juriste décide |
| **Repli multi-LLM + local** | L'outil ne plante jamais faute de clé API |
| **Robustesse** | Accents gérés, OCR indisponible géré, mono-document géré |
| **Persistance JSON** | `reports/` : chaque analyse est rejouable |

---

## 7. Tests

```bash
python -m pytest tests -q    # 164 tests, tous verts
```

| Suite | Couvre |
|---|---|
| `test_extraction.py` | Dates, montants, parties, clauses, cas vides |
| `test_rules_engine.py` | 19 règles (dont 6 risques futurs), cas mono-document, robustesse aux accents |
| `test_knowledge_base.py` | Base juridique, recherche RAG-lite, intégration pipeline |
| `test_comparison.py` | Comparaison pacte/statuts |
| `test_analysis_service.py` | Pipeline complet, documents à vérifier |
| `test_llm_fallback.py` | Repli LLM sans clé, analyse de clauses |

---

## 8. Pour aller plus loin

- `docs/04_architecture.md` — architecture technique détaillée
- `docs/02_benchmark.md` — benchmark de 18 solutions legaltech
- `docs/06_integration.md` — guide d'intégration dans TOP-JURIDIQUE
- `examples/rapport_exemple.md` — exemple de rapport de contrôle

---

**Projet réalisé dans le cadre du stage TOP-JURIDIQUE — Prototype Copilote IA Juridique**
