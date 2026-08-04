# Copilote IA Juridique — TOP-JURIDIQUE

**Stage TOP-JURIDIQUE — Prototype fonctionnel**

> Développer un prototype de copilote IA capable d'analyser les documents d'un dossier juridique, d'extraire les informations clés, de détecter les incohérences et de générer un rapport de contrôle pour le juriste.

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
| 1 | Exemples de documents | Contrats commerciaux, pactes, statuts, actes de société, PV | `ingestion/document_classifier.py` — classification par type |
| 2 | Formats | PDF natif, PDF scanné, Word, images | `ingestion/pdf_reader.py` + `ocr_engine.py` (OCR mocké) |
| 3 | Langues | Français uniquement v1, architecture multilingue | Architecture modulaire prête |
| 4 | Types de dossiers | Contrats, pactes, statuts, modifications statutaires | `config.py` — `TypeDocument` enum |
| 5 | Anomalies à détecter | 8+ types : clauses manquantes, contradictions, risques | `rules_engine/rules.py` — 8 règles déterministes |
| 6 | Sources externes | Légifrance/PISTE en priorité | `legal_kb/` — base mockée, API documentée |
| 7 | Base juridique | À créer pendant le stage | `legal_kb/` — schéma JSON + 18 entrées exemple |
| 8 | Format du rapport | Structuré avec documents, incohérences, anomalies, corrections | `report_generator/report_builder.py` |
| 9 | Recommandations | Explication + priorité + correction + source juridique | Chaque finding contient ces champs |
| 10 | Modèle d'IA | Groq, Google AI, OpenRouter (souveraineté) | `llm/llm_factory.py` — factory pattern |
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
3. **Règles déterministes** : 8 règles de contrôle (agrément, sortie, veto, majorité, non-concurrence, conflit pacte/statuts, blocage, responsabilité gérant)
4. **RAG** : recherche dans la base juridique pour les références officielles
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
│PDF    │ │Clauses  │ │Pacte vs │ │8 règles │ │FAISS + │
│OCR    │ │Entities │ │Statuts  │ │déterm.  │ │HF Emb. │
│Classif│ │         │ │         │ │         │ │        │
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
│   ├── pdf_reader.py               # Extraction texte PDF (PyPDF2)
│   ├── ocr_engine.py               # OCR pour PDF scanné (mock)
│   └── document_classifier.py      # Classification du type de document
│
├── extraction/                      # Couche 2 : Extraction structurée
│   ├── clause_extractor.py         # Extraction des clauses (regex)
│   └── entity_extractor.py         # Dates, montants, parties, articles
│
├── comparison/                      # Couche 3 : Comparaison inter-documents
│   └── document_comparator.py      # Croisement pacte/statuts
│
├── rules_engine/                    # Couche 4 : Règles déterministes
│   ├── rules.py                    # 8 règles de contrôle
│   └── rule_checker.py             # Orchestrateur de règles
│
├── legal_kb/                        # Couche 5 : Base de connaissances
│   ├── schema.json                 # Schéma JSON de la KB
│   ├── knowledge_base.py           # Classe de gestion
│   └── data/
│       ├── societes.json           # Articles Code de commerce
│       └── pactes.json             # Règles pactes d'associés
│
├── rag/                             # Couche 6 : Recherche augmentée
│   ├── embeddings.py               # HuggingFace all-MiniLM-L6-v2
│   └── vector_store.py             # FAISS vector store
│
├── llm/                             # Couche 7 : Modèles de langage
│   └── llm_factory.py              # Factory Groq/Google/OpenRouter
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
├── tests/                           # Tests unitaires
│   ├── test_rules_engine.py        # 11 tests moteur de règles
│   ├── test_comparison.py          # 7 tests comparateur
│   └── test_extraction.py          # 12 tests extracteur
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
| **LLM** | Groq (llama-3.3-70b), Google AI (gemini-2.0-flash), OpenRouter | Multi-provider, souveraineté, performance |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 | Léger, performant, français acceptable |
| **Vector Store** | FAISS (faiss-cpu) | Rapide, local, pas de dépendance cloud |
| **Orchestration** | LangChain | Standard pour RAG, chains, prompts |
| **PDF** | PyPDF2 + ReportLab | Lecture + génération PDF |
| **OCR** | Tesseract/easyocr (mock pour le prototype) | OCR open-source pour PDF scanné |
| **API** | FastAPI + Pydantic | Rapide, typé, auto-documenté |
| **CLI** | argparse | Standard Python |
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

- **10 entrées** droit des sociétés (fictives, basées sur le Code de commerce)
- **8 entrées** pactes d'associés (fictives)
- **18 entrées** au total

### Mise à jour

1. **Manuelle** : ajout de nouvelles entrées JSON
2. **Via API Légifrance/PISTE** : inscription gratuite sur piste.gouv.fr, accès à l'API REST
3. **Documentation** : `docs/05_base_juridique.md`

### Avertissement

> **Toutes les références juridiques dans la base sont FICTIVES.** En production, elles doivent être remplacées par de vraies références vérifiées via Légifrance/PISTE.

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

**67 tests unitaires** couvrant :

| Module | Tests | Couverture |
|--------|-------|------------|
| `rules_engine` | 11 | 8 règles + orchestrateur + déduplication |
| `comparison` | 7 | Dates, montants, parties, clauses, identiques |
| `extraction` | 12 | Dates, montants, parties, articles, cas vides |
| `api` | 12 | Health, analyse 1/n fichiers, rapport, validation |
| Autres | 25 | OCR, LLM fallback, qualité documents, analyse |
| **Total** | **67** | **Tous passent ✅** |

---

## 8. Limites connues et recommandations

### Limites du prototype

1. **Base juridique fictive** : les 18 entrées sont des exemples, pas de vraies références Légifrance
2. **OCR mocké** : l'OCR réel (Tesseract/easyocr) n'est pas implémenté
3. **Extraction regex** : l'extraction des clauses utilise des expressions régulières, pas de NLP avancé
4. **Pas d'intégration TOP-JURIDIQUE** : l'API est prête mais l'intégration réelle n'a pas été faite
5. **LLM non testé en conditions réelles** : les clés API doivent être configurées
6. **Pas de persistence** : les résultats ne sont pas sauvegardés en base de données

### Recommandations pour la suite

1. **Semaine 3-4** : Connecter l'API Légifrance/PISTE pour peupler la base juridique
2. **Semaine 5-6** : Implémenter l'OCR réel avec Tesseract/easyocr
3. **Semaine 7** : Intégrer l'environnement de test TOP-JURIDIQUE
4. **Après le stage** :
   - Ajouter le NLP pour l'extraction de clauses (spaCy, CamemBERT)
   - Implémenter la classification automatique des documents
   - Ajouter la détection de scan de mauvaise qualité
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
| `main.py` | Point d'entrée CLI |
| `config.py` | Configuration globale |
| `requirements.txt` | Dépendances |
| `tests/` | 34 tests unitaires |

---

**Projet réalisé dans le cadre du stage TOP-JURIDIQUE — Prototype Copilote IA Juridique**
