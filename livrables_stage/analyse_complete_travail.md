# Analyse complète du travail réalisé — Stage TOP-JURIDIQUE (semaine 4/8)

Ce document détaille tout ce qui a été fait pendant le premier mois de stage : l'application, chaque fichier, chaque dossier, et comment tout fonctionne.

---

## 1. Vue d'ensemble

**Projet : Copilote IA Juridique — TOP-JURIDIQUE**

Une application qui analyse des documents juridiques (pactes d'associés, statuts, contrats, cours...), en extrait les informations clés, détecte les anomalies et les contradictions, et produit un rapport de contrôle professionnel pour le juriste.

### Chiffres clés
- **~6 700 lignes de code Python** (30+ fichiers)
- **39 tests automatisés** qui passent tous
- **6 formats de fichiers** supportés : PDF, Word (docx), images (PNG/JPG/JPEG), texte (TXT)
- **8 règles de contrôle** juridiques déterministes
- **18 entrées** dans la base juridique (schéma + données)
- **3 fournisseurs IA** configurables (Groq, Google AI, OpenRouter) avec repli local automatique
- **4 formats d'export** : PDF, Markdown, JSON, texte
- **6 documents de documentation**

### 3 façons d'utiliser l'application
1. **Interface web (Streamlit)** — `app.py` : on dépose des fichiers, on clique « Analyser le dossier », on lit le rapport et on pose des questions
2. **Ligne de commande (CLI)** — `main.py` : analyse d'un dossier de PDF sans interface
3. **API REST (FastAPI)** — `api/endpoints.py` : pour intégrer TOP-JURIDIQUE dans une autre application

---

## 2. Comment ça marche (le pipeline)

L'analyse se fait en 6 étapes, comme une chaîne de montage :

```
1. Ingestion    → lire le fichier (PDF, Word, image, texte)
2. Classification → deviner le type de document (pacte, statuts, autre)
3. Extraction   → trouver les dates, montants, parties, clauses
4. Comparaison  → comparer 2 documents entre eux (pacte vs statuts)
5. Règles       → appliquer 8 règles de contrôle juridique
6. Rapport      → construire le rapport final (avec synthèse IA optionnelle)
```

Le tout est orchestré par `services/analysis_service.py` (fonction `analyze_documents`).

---

## 3. Les dossiers du projet et leur rôle

### `ingestion/` — Lire les documents
| Fichier | Rôle |
|---------|------|
| `pdf_reader.py` | Extrait le texte des PDF (PyPDF2), nettoie le bruit (numéros de page, codes d'édition...) |
| `ocr_engine.py` | OCR des PDF scannés (structure prête, moteur réel à brancher) |
| `document_classifier.py` | Détecte le type de document (pacte/statuts/autre) par mots-clés pondérés |

### `extraction/` — Extraire les informations
| Fichier | Rôle |
|---------|------|
| `entity_extractor.py` | Cherche les dates, montants, organisations/parties, références d'articles (regex + règles) |
| `clause_extractor.py` | Découpe le texte en clauses titrées (agrément, cession, veto...) |

### `comparison/` — Comparer les documents
| Fichier | Rôle |
|---------|------|
| `document_comparator.py` | Croise 2 documents : dates, montants, parties, clauses ; produit des incohérences avec sévérité |

### `rules_engine/` — Les règles de contrôle (cœur métier)
| Fichier | Rôle |
|---------|------|
| `rules.py` | **Les 8 règles** : ① clause d'agrément, ② clause de sortie, ③ droit de veto, ④ majorités de décision, ⑤ non-concurrence, ⑥ contradiction pacte/statuts, ⑦ clause de blocage, ⑧ pouvoirs du gérant |
| `rule_checker.py` | Orchestrateur : applique les règles sur le pacte et les statuts, déduplique les résultats |

### `legal_kb/` — La base de connaissances juridique
| Fichier | Rôle |
|---------|------|
| `schema.json` | Le schéma de chaque entrée (source, article, version, dates de vigueur, mots-clés, règles) |
| `data/societes.json` | 10 entrées droit des sociétés |
| `data/pactes.json` | 8 entrées pactes d'associés |
| `knowledge_base.py` | Classe de gestion (lecture, recherche, ajout) |
| ⚠️ Attention | Les références actuelles sont **fictives** ; en production elles seront remplacées par de vraies références Légifrance/PISTE |

### `rag/` — La recherche intelligente dans les documents
| Fichier | Rôle |
|---------|------|
| `embeddings.py` | Vecteurs de texte (sentence-transformers, modèle léger multilingue) |
| `vector_store.py` | Index vectoriel FAISS (rapide, local, sans cloud) pour retrouver les passages pertinents |

### `llm/` — Les modèles de langage (couche IA)
| Fichier | Rôle |
|---------|------|
| `llm_factory.py` | Factory : choisit Groq / Google AI / OpenRouter selon les clés configurées |

### `report_generator/` — Le rapport
| Fichier | Rôle |
|---------|------|
| `report_builder.py` | Construit le rapport structuré (documents, entités, anomalies, incohérences, risque global) |
| `report_export.py` | Exporte en Markdown et PDF |

### `validation/` — La validation humaine
| Fichier | Rôle |
|---------|------|
| `validator.py` | Permet au juriste d'approuver, rejeter ou modifier chaque anomalie ; calcule un taux de validation |

### `api/` — L'API REST pour l'intégration
| Fichier | Rôle |
|---------|------|
| `endpoints.py` | FastAPI : `POST /analyze`, `GET /report/{id}`, `POST /validate/...`, `GET /health` |

### `services/` — La couche applicative (utilisée par l'interface web)
| Fichier | Rôle |
|---------|------|
| `document_service.py` | Lecture de tous les formats + classification du type de document |
| `analysis_service.py` | Le pipeline complet (étape 2) + formatage du rapport Markdown |
| `chat_service.py` | Le chatbot : recherche les passages pertinents dans le texte (moteur de recherche locale) |
| `llm_service.py` | IA optionnelle : Groq prioritaire, OpenRouter secours, repli local si échec ; synthèse intelligente |
| `export_service.py` | Exports PDF/Markdown/JSON + export de la conversation (TXT et PDF) |

### `ui/` — L'interface utilisateur (Streamlit)
| Fichier | Rôle |
|---------|------|
| `components.py` | Composants : en-tête, badges de risque, cartes d'anomalies, tableaux, KPI |
| `styles.py` | Thème professionnel navy/or (CSS complet) |
| `chat_display.py` | Affichage de la conversation + conversion Markdown→HTML |

### `tests/` — Les tests
| Fichier | Rôle |
|---------|------|
| `test_extraction.py` | Extraction (dates, montants, parties, articles, cas vides) |
| `test_comparison.py` | Comparaison (dates, montants, parties, clauses, documents identiques) |
| `test_rules_engine.py` | Les 8 règles + orchestrateur + déduplication |
| `test_llm_fallback.py` | Le repli automatique sans clé API |

### `docs/` — La documentation
| Fichier | Rôle |
|---------|------|
| `01_comprehension_mission.md` | Compréhension complète de la mission |
| `02_benchmark.md` | Benchmark des 18 solutions legaltech |
| `03_cas_usage.md` | Spécification du cas d'usage pacte vs statuts |
| `04_architecture.md` | Architecture technique détaillée |
| `05_base_juridique.md` | Documentation de la base juridique |
| `06_integration.md` | Guide d'intégration TOP-JURIDIQUE |

### Fichiers à la racine
| Fichier | Rôle |
|---------|------|
| `app.py` | Application web Streamlit (point d'entrée principal) |
| `main.py` | Interface ligne de commande (CLI) |
| `config.py` | Configuration : modèles LLM, chemins, énumérations (priorité, types de documents) |
| `config_app.py` | Configuration de l'application web : formats, questions typiques, clés API |
| `requirements.txt` | Les dépendances Python |
| `README.md` | Documentation principale (installation, utilisation, tests) |
| `.env` / `.env.example` | Clés API (Groq, OpenRouter) — jamais dans le code |
| `.gitignore` | Fichiers à ne pas versionner |
| `test_api.py`, `test_pipeline.py` | Tests rapides du pipeline et de l'API |
| `examples/rapport_exemple.md` | Exemple de rapport de contrôle |

### `livrables_stage/` — Documents remis (créés récemment)
| Fichier | Rôle |
|---------|------|
| `mail_avancement.txt` | Mail à l'encadrante |
| `benchmark_solutions_ia.md` | Benchmark des solutions |
| `analyse_complete_travail.md` | Ce document |

---

## 4. Le cas d'usage principal

**Pacte d'associés comparé aux statuts d'une société.**

L'utilisateur dépose les deux fichiers. Le système :
1. Identifie le pacte et les statuts (classification)
2. Extrait les dates, montants, parties, clauses
3. Compare les 2 documents (contradictions, incohérences)
4. Applique les 8 règles de contrôle → anomalies avec priorité (bloquant / important / alerte)
5. Calcule un niveau de risque global (faible / modéré / élevé)
6. Génère un rapport avec pour chaque anomalie : explication, source juridique, correction recommandée, documents à vérifier, validation humaine requise
7. (Optionnel) Produit une synthèse intelligente par IA
8. Le juriste peut poser des questions et exporter le rapport en PDF

### Les anomalies ont 3 niveaux de priorité
| Priorité | Signification |
|----------|---------------|
| **Bloquant** | Le document est incomplet ou contraire à une règle — à corriger avant toute action |
| **Important** | Risque juridique réel à traiter |
| **Alerte** | Point de vigilance à vérifier |

---

## 5. Le mode IA (optionnel mais puissant)

- **Principes** : tout est optionnel, aucune clé n'est dans le code, données jamais envoyées sans clé valide.
- **Priorité des fournisseurs** : Groq → OpenRouter (si clé Groq invalide/absente).
- **Validation des clés** : une clé manifestement invalide est ignorée (format vérifié) → pas d'appel réseau inutile.
- **Repli local** : si l'appel échoue, expire (timeout 30 s) ou renvoie du vide, le système retombe sur la logique locale et n'invente jamais de référence juridique.
- **Ce que l'IA ajoute** :
  - Des réponses de chat plus riches et structurées (toujours basées sur les extraits du document)
  - Une « Synthèse intelligente » dans le rapport d'analyse
- **Sans clé** : l'application fonctionne à 100 % en mode local.

---

## 6. L'interface professionnelle

- Thème **navy / or** avec CSS complet (`ui/styles.py`)
- **KPI** : niveau de risque, nombre d'anomalies, incohérences, documents
- **Documents analysés** : tableau type détecté / statut
- **Informations clés** : dates, organisations, montants sous forme de pastilles
- **Anomalies** : cartes avec badge de priorité, source, correction
- **Incohérences** : cartes avec sévérité
- **Export PDF** : rapport professionnel mis en page (A4, en-tête, pied de page, couleurs)
- **Chatbot** : questions libres ou typiques (10 questions prédéfinies), export de la conversation en TXT/PDF
- Message d'information quand aucun document de société n'est détecté (évite les fausses alertes sur un cours ou un manuel)

---

## 7. Tests et qualité

**39 tests, tous au vert** (`python -m pytest tests/ -v`) :

| Module | Nombre | Ce qui est vérifié |
|--------|--------|--------------------|
| Extraction | 12 | Dates, montants, parties, articles, cas vides |
| Comparaison | 7 | Dates, montants, parties, clauses, documents identiques |
| Règles | 11 | Les 8 règles + orchestrateur + déduplication |
| Repli LLM | 9 | Comportement sans clé, clé invalide, échec d'appel |

En plus : `test_pipeline.py` (pipeline complet) et `test_api.py` (endpoints API).

---

## 8. Ce qui reste à faire (semaines 5 à 8)

1. **Intégrer Légifrance/PISTE** pour remplacer les références fictives par de vraies sources officielles
2. **Brancher l'OCR réel** (Tesseract) pour les PDF scannés de mauvaise qualité
3. **Enrichir la base juridique** (nouvelles règles, nouveaux types de documents)
4. **Étendre le workflow de validation humaine** dans l'interface
5. **Étendre à d'autres documents** : procès-verbaux, décisions sociales, modifications statutaires
6. **Intégration TOP-JURIDIQUE** : connecter l'API REST à l'environnement de test

---

## 9. Points forts du travail

- **Architecture modulaire** : chaque couche est séparée et remplaçable
- **Souveraineté/confidentialité** : le système fonctionne sans aucune donnée envoyée à l'extérieur
- **Anti-hallucination** : l'IA ne cite jamais une référence inventée ; sans source fiable, le système le dit
- **Règles déterministes traçables** : les anomalies sont expliquées, sourcées, avec correction recommandée
- **Validation humaine obligatoire** : le rapport rappelle toujours qu'un professionnel doit valider
- **Faux positifs évités** : un document qui n'est pas un pacte/statuts n'est pas passé au crible des règles de société
