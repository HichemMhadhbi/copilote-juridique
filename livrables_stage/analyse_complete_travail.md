# Analyse complète du travail réalisé — Stage TOP-JURIDIQUE (semaine 4/8)

Ce document détaille tout ce qui a été fait pendant le premier mois de stage : l'application, chaque fichier, chaque dossier, et comment tout fonctionne.

---

## 1. Vue d'ensemble

**Projet : Copilote IA Juridique — TOP-JURIDIQUE**

Une application qui analyse des documents juridiques (pactes d'associés, statuts, contrats, cours...), en extrait les informations clés, détecte les anomalies et les contradictions, et produit un rapport de contrôle professionnel pour le juriste.

### Chiffres clés
- **~6 700 lignes de code Python** (30+ fichiers)
- **131 tests automatisés** qui passent tous
- **6 formats de fichiers** supportés : PDF, Word (docx), images (PNG/JPG/JPEG), texte (TXT), PDF scannés (OCR Tesseract)
- **19 règles de contrôle** juridiques déterministes (dont 6 règles de risques futurs)
- **18 entrées** dans la base juridique, **réellement interrogées** à chaque analyse (RAG-lite)
- **3 fournisseurs IA** configurables (Groq, Google AI, OpenRouter) avec repli local automatique
- **4 formats d'export** : PDF, Markdown, JSON, texte
- **6 documents de documentation**

### 3 façons d'utiliser l'application
1. **Interface web (Streamlit)** — `app.py` : on dépose des fichiers, on clique « Analyser le dossier », on lit le rapport et on pose des questions
2. **Ligne de commande (CLI)** — `main.py` : analyse d'un dossier de PDF sans interface
3. **API REST (FastAPI)** — `api/endpoints.py` : pour intégrer TOP-JURIDIQUE dans une autre application

---

## 2. Comment ça marche (le pipeline)

L'analyse se fait en 7 étapes, comme une chaîne de montage :

```
1. Ingestion    → lire le fichier (PDF, Word, image, texte, PDF scanné via OCR)
2. Classification → deviner le type de document (pacte, statuts, autre) + signaler les **documents manquants** (ex. statuts absent d'un dossier de société)
3. Extraction   → trouver les dates, montants, parties, clauses
4. Comparaison  → comparer 2 documents entre eux (pacte vs statuts)
5. Règles       → appliquer 19 règles de contrôle juridique (dont 6 règles de risques futurs)
6. RAG-lite     → interroger la base juridique (articles + règles de contrôle) pour chaque anomalie
7. Rapport      → construire le rapport final (avec synthèse IA optionnelle)
```

Le tout est orchestré par `services/analysis_service.py` (fonction `analyze_documents`).

---

## 3. Les dossiers du projet et leur rôle

### `ingestion/` — Lire les documents
| Fichier | Rôle |
|---------|------|
| `ocr_engine.py` | **OCR réel des PDF scannés et images** (Tesseract, français) — texte extrait puis analysé comme un PDF natif |

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
| `rules.py` | **Les 19 règles** : ① clause d'agrément, ② clause de sortie, ③ droit de veto, ④ majorités de décision, ⑤ non-concurrence, ⑥ contradiction pacte/statuts, ⑦ clause de blocage, ⑧ pouvoirs du gérant, ⑨ PV/quorum, ⑩ PV/résolutions, ⑪ modification statutaire, ⑫ champs à compléter, ⑬ formulations/forme, et 6 règles de risques futurs : ⑭ valorisation des titres en sortie, ⑮ décès/incapacité d'un associé, ⑯ non-paiement (impayé), ⑰ confidentialité / secret des affaires, ⑱ résiliation (durée sans issue), ⑲ déséquilibre de gouvernance. |
| `rule_checker.py` | Orchestrateur : applique les règles sur le pacte et les statuts, déduplique les résultats, adapte les règles à la forme sociale (SAS/SARL/SCI…) |

### `legal_kb/` — La base de connaissances juridique
| Fichier | Rôle |
|---------|------|
| `schema.json` | Le schéma de chaque entrée (source, article, version, dates de vigueur, mots-clés, règles) |
| `data/societes.json` | 10 entrées droit des sociétés |
| `data/pactes.json` | 8 entrées pactes d'associés |
| `knowledge_base.py` | Classe de gestion (lecture, recherche, ajout) + **recherche RAG-lite** `search_relevant` : pour chaque anomalie, les entrées pertinentes (articles + règles de contrôle associées) sont classées par type de document + termes + domaine, sans service cloud |
| ✔️ Références | Les 18 entrées sont **réellement interrogées** à chaque analyse (le rapport indique le nombre d'entrées mobilisées) ; les liens Légifrance sont rattachés à l'analyse via `services/legal_source_service.py` |

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
| `legal_source_service.py` | Références officielles : obtient un jeton PISTE (OAuth2), vérifie chaque référence sur Légifrance ou renvoie un lien de recherche ; aucune référence inventée |
| `llm_service.py` | IA optionnelle : Groq prioritaire, OpenRouter secours, repli local si échec ; synthèse intelligente + **analyse de chaque clause** (risque, amélioration, fondement juridique) |
| `export_service.py` | Exports PDF/Markdown/JSON + export de la conversation (TXT et PDF) |

### `ui/` — L'interface utilisateur (Streamlit)
| Fichier | Rôle |
|---------|------|
| `components.py` | Composants : en-tête, badges de risque, cartes d'anomalies, tableaux, KPI |
| `styles.py` | Thème professionnel navy/or (CSS complet) |
| `chat_display.py` | Affichage de la conversation + conversion Markdown→HTML |

### `tests/` — Les tests (131 au total)
| Fichier | Rôle |
|---------|------|
| `test_extraction.py` | Extraction (dates, montants, parties, articles, cas vides) |
| `test_comparison.py` | Comparaison (dates, montants, parties, clauses, documents identiques) |
| `test_rules_engine.py` | Les 19 règles (dont 6 risques futurs) + orchestrateur + déduplication + formes sociales |
| `test_knowledge_base.py` | Base juridique, recherche RAG-lite, intégration au pipeline |
| `test_llm_fallback.py` | Le repli automatique sans clé API, analyse de clauses |
| autres `test_*` | API, pipeline, OCR, qualité documents |

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
4. Applique les 19 règles de contrôle → anomalies avec priorité (bloquant / important / alerte)
5. Rattache chaque anomalie à la base juridique (RAG-lite : articles + règles de contrôle pertinents) et ajoute les liens Légifrance
6. Calcule un niveau de risque global (faible / modéré / élevé)
7. Génère un rapport avec pour chaque anomalie : explication, source juridique, correction recommandée, documents à vérifier, validation humaine requise
8. (Optionnel) Produit une synthèse intelligente par IA et une analyse de chaque clause
9. Le juriste peut poser des questions et exporter le rapport en PDF

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

**131 tests, tous au vert** (`python -m pytest tests/ -v`) :

| Module | Nombre | Ce qui est vérifié |
|--------|--------|--------------------|
| Extraction | 19 | Dates, montants, parties, articles, cas vides |
| Comparaison | 13 | Dates, montants, parties, clauses, documents identiques |
| Règles | 41 | Les 19 règles (dont 6 risques futurs), formes sociales, orchestrateur, déduplication |
| Base juridique (RAG-lite) | 11 | Chargement, recherche par pertinence, intégration pipeline |
| Repli LLM | 10 | Comportement sans clé, clé invalide, échec d'appel, analyse de clauses |
| Références Légifrance | 10 | Normalisation des références (forme canonique), liens de recherche |
| API / pipeline / OCR / qualité | 23 | Endpoints, pipeline complet, OCR, qualité des documents |

En plus : `test_pipeline.py` (pipeline complet) et `test_api.py` (endpoints API).

---

## 8. Ce qui reste à faire (semaines 5 à 8)

1. **Intégration TOP-JURIDIQUE** : connecter l'API REST à l'environnement de test (URL + identifiants à fournir)
2. **Étendre la base juridique** (nouvelles règles, nouveaux types de documents : PV, contrats, baux)
3. **Étendre le workflow de validation humaine** dans l'interface
4. **Étendre à d'autres documents** : procès-verbaux, décisions sociales, modifications statutaires
5. **NLP** : remplacer progressivement les regex par de l'extraction avancée (spaCy, CamemBERT)
6. **Configurer les clés PISTE** dans l'environnement de production pour la vérification officielle automatique

---

## 9. Points forts du travail

- **Architecture modulaire** : chaque couche est séparée et remplaçable
- **Souveraineté/confidentialité** : le système fonctionne sans aucune donnée envoyée à l'extérieur
- **Anti-hallucination** : l'IA ne cite jamais une référence inventée ; sans source fiable, le système le dit
- **Règles déterministes traçables** : les anomalies sont expliquées, sourcées, avec correction recommandée
- **Validation humaine obligatoire** : le rapport rappelle toujours qu'un professionnel doit valider
- **Faux positifs évités** : un document qui n'est pas un pacte/statuts n'est pas passé au crible des règles de société
