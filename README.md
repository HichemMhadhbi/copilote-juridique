# Copilote IA Juridique — TOP-JURIDIQUE

**Stage TOP-JURIDIQUE — Prototype fonctionnel**

> Développer un prototype de copilote IA capable d'analyser les documents d'un dossier juridique, d'extraire les informations clés, de détecter les incohérences et de générer un rapport de contrôle pour le juriste.

> **Présentation à destination de l'encadrante** (utilité pour le formaliste, démarche, architecture, script de démo) :
> `livrables_stage/presentation_encadrante.md` (+ version PDF `presentation_encadrante.pdf`)

---

## Table des matières

1. [Compréhension de la mission](#1-compréhension-de-la-mission)
2. [Cas d'usage retenu](#2-cas-dusage-retenu)
3. [Architecture technique](#3-architecture-technique)
4. [Technologies utilisées](#4-technologies-utilisées)
5. [Base de connaissances juridique](#5-base-de-connaissances-juridique)
6. [Installation et utilisation](#6-installation-et-utilisation)
7. [Tests](#7-tests)
8. [Limites connues et recommandations](#8-limites-connues-et-recommandations)

---

## 1. Compréhension de la mission

### Objectif final

Créer un assistant IA pour la plateforme TOP-JURIDIQUE qui :
- Analyse le contenu juridique des documents (pactes d'associés, statuts, contrats)
- Détecte les failles et incohérences
- Identifie les risques immédiats ou futurs
- Propose des améliorations argumentées
- Laisse la décision finale au juriste ou au formaliste

### Réponses aux questions de l'encadrante

| # | Question | Réponse synthétique | Traitement dans le code |
|---|----------|---------------------|------------------------|
| 1 | Exemples de documents | Contrats commerciaux, pactes, statuts, actes de société, PV | `services/document_service.py` — classification par type |
| 2 | Formats | PDF natif, PDF scanné, Word, images | `services/document_service.py` + `ingestion/ocr_engine.py` (OCR réel Tesseract) |
| 3 | Langues | Français uniquement v1, architecture multilingue | Architecture modulaire prête |
| 4 | Types de dossiers | Contrats, pactes, statuts, modifications statutaires | `config.py` — `TypeDocument` enum |
| 5 | Anomalies à détecter | 19 types : clauses manquantes, contradictions, risques immédiats et futurs | `rules_engine/rules.py` — 19 règles déterministes |
| 6 | Sources externes | Légifrance/PISTE (OAuth2) + liens Légifrance | `services/legal_source_service.py` — vérification officielle |
| 7 | Base juridique | Créée pendant le stage | `legal_kb/` — schéma JSON + 18 entrées réelles, interrogée (RAG-lite) |
| 8 | Format du rapport | Structuré avec documents, documents manquants, incohérences, anomalies, corrections | `report_generator/report_builder.py` + `analysis_service._detecter_documents_manquants` |
| 9 | Recommandations | Explication + priorité + correction + source juridique | Chaque finding contient ces champs |
| 10 | Modèle d'IA | Groq, Google AI, OpenRouter (souveraineté) | `services/llm_service.py` — repli local automatique |
| 11 | Architecture | Modulaire, 10 couches séparées | Voir section 3 |
| 12 | Intégration | API REST FastAPI pour TOP-JURIDIQUE | `api/endpoints.py` |
| 13 | Périmètre 2 mois | 1 cas d'usage complet (pacte vs statuts) | Ce prototype |
| 14 | Validation juridique | Points réguliers avec juriste référent | `validation/validator.py` |
| 15 | Livrables | Code, base juridique, rapport, docs, tests | Tous les fichiers du projet |
| 16 | Ressources | Documentation PISTE/Légifrance, OCR, RAG | `docs/` |
| 17 | Benchmark | 18 outils analysés | `docs/02_benchmark.md` |

### Planning prévisionnel (8 semaines)

| Semaine | Tâche |
|---------|-------|
| 1-2 | Compréhension, benchmark, architecture, choix techniques |
| 3-4 | Ingestion, extraction, base juridique, moteur de règles |
| 5-6 | Comparaison inter-documents, RAG, génération de rapport |
| 7 | API, intégration, tests, validation juridique |
| 8 | Documentation, démo, passation |

---

## 2. Cas d'usage retenu

**Analyse d'un pacte d'associés comparé aux statuts de la société**

### Pourquoi ce cas d'usage ?

- Document central dans la vie des sociétés commerciales
- Comporte de nombreuses clauses techniques (agrément, sortie, veto, non-concurrence)
- Nécessite une comparaison croisée avec les statuts
- Permet de démontrer toutes les capacités du système

### Ce que le système fait

1. **Extraction** des clauses, dates, montants, parties depuis le pacte et les statuts
2. **Comparaison** croisée des deux documents (dates, montants, parties, clauses)
3. **Règles déterministes** : 19 règles de contrôle (agrément, sortie, veto, majorité, non-concurrence, conflit pacte/statuts, blocage, responsabilité gérant, valorisation, décès/incapacité, impayé, confidentialité, résiliation, déséquilibre…) dont 6 de risques futurs
4. **RAG-lite** : chaque anomalie interroge la base juridique (18 entrées) et reçoit les articles et règles de contrôle pertinents
5. **Rapport structuré** : JSON + Markdown + PDF avec recommandations
6. **Validation humaine** : chaque finding peut être validé, modifié ou rejeté par un juriste

### Extension à d'autres documents

L'architecture modulaire permet d'ajouter :
- Contrats commerciaux
- Modifications statutaires
- Procès-verbaux
- Dossiers de formalités

---

## 3. Architecture technique

```
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PRÉSENTATION                       │
│  CLI (main.py)  │  API FastAPI (api/)  │  Rapport (PDF/MD)  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    COUCHE ORCHESTRATION                      │
│              Pipeline: Ingest → Extract → Compare            │
│                   → Rules → RAG → Report                     │
└───┬───────────┬───────────┬───────────┬───────────┬────────┘
    │           │           │           │           │
┌───▼───┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌───▼────┐
│Ingest │ │Extract  │ │Compare  │ │Rules    │ │Legal   │
│       │ │         │ │         │ │Engine   │ │KB/RAG  │
│PDF    │ │Clauses  │ │Pacte vs │ │19 règles│ │RAG-lite│
│OCR    │ │Entities │ │Statuts  │ │déterm.  │ │recherche│
│Classif│ │         │ │         │ │         │ │pondérée│
└───────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘
                                    │
                           ┌────────▼────────┐
                           │  LLM Factory    │
                           │  Groq/Google/OR │
                           └─────────────────┘
```

### Arborescence du projet

```
top-juridique-copilote/
├── main.py                          # Point d'entrée CLI
├── config.py                        # Configuration globale
├── requirements.txt                 # Dépendances Python
│
├── ingestion/                       # Couche 1 : Lecture des documents
│   └── ocr_engine.py               # OCR réel des PDF scannés (Tesseract + français)
│
├── extraction/                      # Couche 2 : Extraction structurée
│   ├── clause_extractor.py         # Extraction des clauses (regex)
│   └── entity_extractor.py         # Dates, montants, parties, articles
│
├── comparison/                      # Couche 3 : Comparaison inter-documents
│   └── document_comparator.py      # Croisement pacte/statuts
│
├── rules_engine/                    # Couche 4 : Règles déterministes
│   ├── rules.py                    # 19 règles de contrôle (immédiats + futurs)
│   └── rule_checker.py             # Orchestrateur de règles
│
├── legal_kb/                        # Couche 5 : Base de connaissances
│   ├── schema.json                 # Schéma JSON de la KB
│   ├── knowledge_base.py           # Gestion + recherche RAG-lite (pertinence)
│   └── data/
│       ├── societes.json           # Articles Code de commerce
│       └── pactes.json             # Règles pactes d'associés
│
├── services/                        # Couches 6-7 : orchestration, sources, IA
│   ├── analysis_service.py         # Pipeline : extract → compare → règles → RAG → rapport
│   ├── legal_source_service.py     # Vérification officielle Légifrance / PISTE
│   └── llm_service.py              # IA optionnelle Groq/OpenRouter + repli local
│
├── report_generator/                # Couche 8 : Génération de rapport
│   ├── report_builder.py           # Construction JSON structurée
│   └── report_export.py            # Export Markdown + PDF
│
├── validation/                      # Couche 9 : Validation humaine
│   └── validator.py                # Approbation/rejet/modification
│
├── api/                             # Couche 10 : API REST
│   └── endpoints.py                # FastAPI (analyze, report, validate)
│
├── examples/                        # Exemples
│   └── rapport_exemple.md          # Rapport de contrôle exemple
│
    ├── tests/                           # Tests unitaires (164)
│   ├── test_rules_engine.py        # 41 tests moteur de règles
│   ├── test_knowledge_base.py      # 11 tests base juridique / RAG-lite
│   ├── test_extraction.py          # 19 tests extracteur
│   └── test_*_*.py                 # API, comparaison, OCR, qualité, LLM…
│
└── docs/                            # Documentation
    ├── 01_comprehension_mission.md
    ├── 02_benchmark.md
    ├── 03_cas_usage.md
    ├── 04_architecture.md
    ├── 05_base_juridique.md
    └── 06_integration.md
```

---

## 4. Technologies utilisées

| Couche | Technologie | Justification |
|--------|-------------|---------------|
| **LLM** | Groq (llama-3.3-70b), Google AI (gemini-2.0-flash), OpenRouter | Multi-provider, souveraineté, repli local automatique |
| **RAG-lite** | Recherche locale pondérée (type de doc + termes + domaine) | Références contrôlées, zéro hallucination, aucun service cloud requis |
| **PDF** | PyPDF2 + ReportLab | Lecture + génération PDF |
| **OCR** | Tesseract (français) via `pytesseract` | OCR open-source réel pour PDF scanné et images |
| **API** | FastAPI + Pydantic | Rapide, typé, auto-documenté |
| **Web** | Streamlit | Interface de démonstration rapide |
| **Sources officielles** | API PISTE / Légifrance (OAuth2) | Vérification réelle des références juridiques |
| **Tests** | pytest | Standard industry |

---

## 5. Base de connaissances juridique

### Structure (schéma JSON)

Chaque entrée contient :
- `id`, `source`, `titre_texte`, `numero_article`, `version`
- `date_entree_vigueur`, `date_abrogation`
- `domaine`, `mots_cles`, `types_documents_concernes`
- `regles_controle` : liste de règles associées

### Données actuelles

- **10 entrées** droit des sociétés (Code de commerce)
- **8 entrées** pactes d'associés (Code civil / procédure civile)
- **18 entrées** au total, **réellement interrogées** par le pipeline (RAG-lite) : chaque anomalie reçoit les articles et règles de contrôle pertinents (`knowledge_base.search_relevant`).

### Vérification officielle

- **Légifrance / PISTE** : le service `legal_source_service.py` obtient un jeton OAuth2 et vérifie chaque référence (identifiant LEGIARTI, texte officiel) ou renvoie un lien de recherche Légifrance. Aucune référence n'est inventée.
- `legal_kb/` reste la source locale hors ligne ; les liens officiels y sont rattachés à l'analyse.

### Mise à jour

1. **Manuelle** : ajout de nouvelles entrées JSON
2. **Via API Légifrance/PISTE** : inscription gratuite sur piste.gouv.fr, accès à l'API REST
3. **Documentation** : `docs/05_base_juridique.md`

---

## 6. Installation et utilisation

### Prérequis

- Python 3.10+
- pip

### Installation

```bash
cd top-juridique-copilote
pip install -r requirements.txt
```

### Utilisation en ligne de commande

```bash
# Analyse complète d'un dossier
python main.py --input ./mes_documents/ --output ./rapport/

# Mode avec un seul fichier
python main.py --input ./pacte.pdf --output ./resultat/
```

### Utilisation via API

```bash
# Démarrer le serveur (port 8000, configurable via API_HOST / API_PORT)
python run_api.py

# Alternative
uvicorn api.endpoints:app --reload --host 0.0.0.0 --port 8000

# Endpoints
POST /analyze          # Lancer une analyse (1 ou plusieurs fichiers PDF)
GET  /report/{id}      # Récupérer un rapport
POST /validate/{id}/{finding_id}  # Valider une recommandation
GET  /health           # Vérification santé

# Exemple avec plusieurs fichiers
curl -X POST http://localhost:8000/analyze \
  -F "mode=rapide" \
  -F "files=@pacte.pdf" \
  -F "files=@statuts.pdf"
```

Documentation interactive de l'API : `http://localhost:8000/docs` (Swagger).

### Exécution des tests

```bash
python -m pytest tests/ -v
```

---

## 7. Tests

**164 tests unitaires** couvrant :

| Module | Tests | Couverture |
|--------|-------|------------|
| `rules_engine` | 41 | 19 règles (dont 6 risques futurs) + orchestrateur + déduplication + formes sociales |
| `knowledge_base` | 11 | Chargement, recherche RAG-lite par pertinence, intégration pipeline |
| `extraction` | 19 | Dates, montants, parties, articles, cas vides |
| `comparison` | 13 | Dates, montants, parties, clauses, identiques |
| `api` | 12 | Health, analyse 1/n fichiers, rapport, validation |
| `llm_fallback` | 10 | Repli local déterministe, analyse de clauses, parse JSON |
| `legal_source` | 10 | Normalisation des références (forme canonique Légifrance), liens de recherche |
| `chat` | 11 | Réponses locales : parties, dates, montants, risques, recommandations, résumé |
| `validation` | 9 | Validation humaine : approuver / rejeter / modifier, résumé |
| `storage` | 8 | Sauvegarde / chargement / liste / suppression des rapports |
| `export` | 5 | Export Markdown, JSON, PDF (rapport + conversation) |
| Autres | 15 | OCR, qualité documents, pipeline analyse, documents manquants |
| **Total** | **164** | **Tous passent ✅** |

```bash
python -m pytest tests -q    # 164 passed
```

---

## 8. Limites connues et recommandations

### Limites du prototype

1. **Base juridique réduite** : 18 entrées couvrent le droit des sociétés et les pactes ; à étendre aux PV, contrats, baux…
2. **Extraction regex** : l'extraction des clauses utilise des expressions régulières, pas de NLP avancé
3. **Pas d'intégration TOP-JURIDIQUE** : l'API est prête mais l'accès à l'environnement de test n'a pas encore été fourni
4. **LLM optionnel** : les clés API (Groq/OpenRouter) doivent être configurées pour l'enrichissement ; le repli local reste complet
5. **Vérification Légifrance** : active si les identifiants PISTE sont configurés dans `.env` ; sinon repli sur des liens de recherche Légifrance

### Recommandations pour la suite

1. **Connecter l'environnement de test TOP-JURIDIQUE** (URL + identifiants) pour l'intégration réelle
2. **Étendre la base juridique** (PV, modifications statutaires, contrats) et les règles correspondantes
3. **Ajouter le NLP pour l'extraction de clauses** (spaCy, CamemBERT) en remplacement des regex
4. **Après le stage** :
   - Brancher des embeddings vectoriels (all-MiniLM-L6-v2 + FAISS) en extension du RAG-lite actuel
   - Développer un dashboard juridique pour la validation

### Benchmark

Voir `docs/02_benchmark.md` pour l'analyse de 18 solutions existantes (10 France + 8 International) et le positionnement différenciant de TOP-JURIDIQUE.

---

## Fichiers livrés

| Fichier | Description |
|---------|-------------|
| `docs/01_comprehension_mission.md` | Compréhension complète de la mission |
| `docs/02_benchmark.md` | Benchmark de 18 solutions legaltech |
| `docs/03_cas_usage.md` | Spécification du cas d'usage |
| `docs/04_architecture.md` | Architecture technique détaillée |
| `docs/05_base_juridique.md` | Documentation de la base juridique |
| `docs/06_integration.md` | Guide d'intégration TOP-JURIDIQUE |
| `examples/rapport_exemple.md` | Exemple de rapport de contrôle |
| `livrables_stage/presentation_encadrante.md` | Présentation métier pour l'encadrante (utilité pour le formaliste) + script de démo |
| `main.py` | Point d'entrée CLI |
| `config.py` | Configuration globale |
| `requirements.txt` | Dépendances |
| `tests/` | 164 tests unitaires |

---

**Projet réalisé dans le cadre du stage TOP-JURIDIQUE — Prototype Copilote IA Juridique**
