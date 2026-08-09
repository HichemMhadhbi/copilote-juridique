# TOP-JURIDIQUE — Compréhension de la Mission

> Document de synthèse rédigé à l'issue des échanges avec le superviseur (Partie 3).
> Stagiaire : [À compléter] | Période : 2 mois | Direction : [À compléter]

> **Mise à jour (état actuel)** : ce document est le plan initial de la mission. Il a été ajusté pour refléter l'architecture réellement implémentée : pas de `rag/` ni de `llm/` (remplacés par `services/`), pas de FAISS/LangChain — la **recherche RAG-lite** interroge la base juridique localement, et l'IA optionnelle repose sur `services/llm_service.py` avec repli local. La base juridique contient **18 entrées réelles** vérifiées via Légifrance/PISTE.

---

## 1. Compréhension définitive de la mission

### Contexte

TOP-JURIDIQUE est un **Copilote Juridique IA** dédié aux professionnels du droit en France : avocats, juristes d'entreprise, notaires, et conseillers juridiques. Le projet s'inscrit dans la dynamique de digitalisation du secteur juridique, portée notamment par le programme **France Legaltech 2026** dont TOP-JURIDIQUE fait partie des 10 lauréats.

### Problématique identifiée

Les praticiens du droit passent un temps considérable à :
- **Comparer manuellement** des documents juridiques entre eux (statuts vs pacte, contrat vs modèle, etc.)
- **Vérifier la conformité** de documents avec le droit en vigueur
- **Rechercher des clauses manquantes** ou contradictoires
- **Rédiger des rapports d'analyse** pour leurs clients ou leurs supérieurs
- **Actualiser** des documents existants face aux évolutions législatives

Ce processus est chronophage, sujet à erreurs humaines, et manque de standardisation.

### Mission proposée

Concevoir et développer un **Système d'Analyse Juridique par Intelligence Artificielle** capable de :

1. **Ingestion** de documents juridiques (PDF, Word) avec OCR pour les documents scannés
2. **Classification automatique** du type de document (statuts, pacte d'associés, contrat, avenant, etc.)
3. **Extraction structurée** des clauses et informations clés
4. **Comparaison multi-documents** (ex. : pacte d'associés vs statuts d'une SAS)
5. **Détection automatique** des incohérences, contradictions, risques et clauses manquantes
6. **Vérification** par rapport aux sources officielles (Légifrance, Code civil, Code de commerce)
7. **Proposition d'améliorations** et de reformulations
8. **Génération de rapports** professionnels (PDF) avec références légales
9. **Validation humaine** avec système de confiance et alertes

Le tout doit être intégré comme un **plugin/module complémentaire** à l'existant écosystème TOP-JURIDIQUE, avec une architecture modulaire permettant des évolutions futures.

### Périmètre fonctionnel

| Dimension | Couverture |
|-----------|-----------|
| Types de documents | Statuts (SAS, SARL, SA), pactes d'associés, contrats, avenants, conventions |
| Sources juridiques | Code civil, Code de commerce, Code des sociétés, doctrine, jurisprudence |
| Langues | Français (prioritaire), anglais (évolution future) |
| Utilisateurs cibles | Avocats, juristes d'entreprise, notaires, students |
| Mode d'utilisation | Web (Streamlit), CLI pour intégration technique |

---

## 2. Premier cas d'usage : Analyse d'un pacte d'associés comparé aux statuts

### Pourquoi ce cas d'usage ?

Le **pacte d'associés** (ou pacte d'actionnaires) est un document fondamental dans la vie des sociétés commerciales. Il complète les statuts et régit les relations entre associés sur des aspects que les statuts ne couvrent pas (ou ne couvrent que partiellement) : clause de sortie, préemption, gouvernance, anti-dilution, etc.

**Problème concret** : il est fréquent que des contradictions existent entre le pacte et les statuts, que des clauses essentielles soient absentes, ou que certaines dispositions ne soient plus conformes au droit en vigueur. La vérification manuelle prend en moyenne **4 à 8 heures** pour un juriste expérimenté.

### Ce que le système doit réaliser

1. **Identifier et catégoriser** chaque clause du pacte et des statuts
2. **Extraire les informations structurées** (parties, montants, délais, conditions, etc.)
3. **Détecter les contradictions** entre les deux documents
4. **Identifier les clauses manquantes** par rapport au modèle de référence
5. **Évaluer les risques juridiques** (clauses abusives, clauses non conformes au droit)
6. **Proposer des références légales** (articles du Code de commerce, jurisprudence)
7. **Suggérer des améliorations** avec reformulations
8. **Générer un rapport PDF** structuré avec scoring de confiance
9. **Signaler les points nécessitant une validation humaine**

### Résultat attendu

Un rapport comparatif complet au format PDF contenant :
- Un résumé exécutif
- Un tableau comparatif clause par clause
- Les contradictions identifiées avec niveau de sévérité
- Les risques détectés avec recommandations
- Les références légales applicables
- Les propositions d'amélioration
- Un score de confiance global
- Les points nécessitant une intervention humaine

---

## 3. Architecture technique envisagée

### Principe directeur : Architecture modulaire et séparée

Le système doit être **indépendant** de l'application principale TOP-JURIDIQUE tout en pouvant y être intégré via une API. Cela permet :

- Une maintenance indépendante
- Des tests unitaires sur chaque module
- Une scalabilité future
- Un remplacement de composants sans impacter le reste

### Architecture en couches

```
┌─────────────────────────────────────────────────┐
│              COUCHE PRÉSENTATION                │
│         (Streamlit / Interface Web)              │
├─────────────────────────────────────────────────┤
│              COUCHE API                          │
│           (FastAPI REST)                         │
├──────────┬──────────┬──────────┬────────────────┤
│ Ingestion│Extraction│Comparaison│  Reporting    │
│  & OCR   │& Classif.│& Règles  │  & Export     │
├──────────┴──────────┴──────────┴────────────────┤
│           SERVICES (orchestration)              │
│  analysis • document • legal_source • llm       │
├─────────────────────────────────────────────────┤
│    BASE DE CONNAISSANCE JURIDIQUE               │
│     (RAG-lite : type doc + termes + domaine)    │
├─────────────────────────────────────────────────┤
│         COUCHE VALIDATION HUMAINE               │
│    (Workflow d'approbation + scoring)           │
├─────────────────────────────────────────────────┤
│         COUCHE PERSISTANCE                      │
│      (SQLite / PostgreSQL + fichiers)           │
└─────────────────────────────────────────────────┘
```

> Les couches `rag/` et `llm/` prévues au départ ont été remplacées par la couche `services/` : la recherche contextuelle est réalisée en **local** (RAG-lite sur la base juridique) et l'IA optionnelle (Groq/OpenRouter) est gérée par `services/llm_service.py` avec repli local.

### Modules principaux

| Module | Responsabilité | Technologies |
|--------|---------------|-------------|
| `ingestion/` | Lecture PDF/Word/images + OCR des PDF scannés | PyPDF2, Tesseract, pytesseract, python-docx |
| `extraction/` | Classification, extraction structurée (regex) | Regex + règles, PyPDF2 |
| `comparison/` | Comparaison multi-documents, détection écarts | Règles métier (dates, montants, parties, clauses) |
| `rules_engine/` | Moteur de règles juridiques, conformité | 19 règles codées, patterns juridiques |
| `legal_kb/` | Base de connaissances juridiques + **RAG-lite** | JSON structuré, recherche locale pondérée |
| `services/` | Orchestration : analyse, lecture/classification, sources officielles (Légifrance/PISTE), IA optionnelle | FastAPI-compatible, OAuth2, repli local |
| `report_generator/` | Génération de rapports | Markdown + ReportLab (PDF) |
| `validation/` | Workflow de validation humaine | API + Streamlit |
| `api/` | API REST pour intégration | FastAPI, Pydantic |

> Les modules `rag/` (FAISS/LangChain) et `llm/` (HuggingFace) initialement prévus n'ont pas été retenus : la recherche est faite en local (RAG-lite) et l'IA est appelée à distance via `services/llm_service.py`.

---

## 4. Technologies proposées

### Stack technique complète

| Couche | Technologie | Justification |
|--------|------------|---------------|
| **Langage principal** | Python 3.11+ | Écosystème IA/ML dominant, bibliothèques disponibles |
| **RAG-lite** | Recherche locale pondérée (type de doc + termes + domaine) | Références contrôlées, zéro hallucination, aucun service cloud requis |
| **IA optionnelle** | Groq (llama-3.3-70b), OpenRouter | Souveraineté, repli local automatique si échec/sans clé |
| **Sources officielles** | API PISTE / Légifrance (OAuth2) | Vérification réelle des références juridiques |
| **NLP / extraction** | Regex + règles | Extraction des clauses, dates, montants, parties (évolutions spaCy possibles) |
| **Interface web** | Streamlit | Prototypage rapide, UI interactive, data science |
| **Rapports PDF** | ReportLab + Markdown | Génération de PDF professionnels avec mise en forme |
| **API** | FastAPI | API REST performante, auto-documentée, async |
| **Base de données** | SQLite (dev) / PostgreSQL (prod) | Métadonnées, historique, sessions |
| **OCR** | Tesseract + pytesseract | OCR réel des PDF scannés et images (français) |
| **Tests** | pytest | Tests unitaires et d'intégration |
| **Gestion de config** | python-dotenv + Pydantic | Validation des configurations |

> **Évolutions écartées au prototype** : LangChain, FAISS et les embeddings HuggingFace ne sont pas utilisés (la recherche RAG-lite suffit et évite toute dépendance lourde) ; leur intégration reste possible en extension future.

### Choix du modèle LLM

Pour un usage juridique en français, l'IA repose sur des API distantes avec **repli local automatique** :
1. **Groq (llama-3.3-70b)** — prioritaire, rapide
2. **OpenRouter** — secours si la clé Groq est absente/invalide
3. **Repli local déterministe** — si aucun fournisseur ne répond, l'analyse est produite localement (aucun blocage, aucune référence inventée)

Le système est **agnostic vis-à-vis du modèle** : il suffit de configurer une clé dans `.env` pour changer de fournisseur sans refonte majeure.

---

## 5. Méthode de création de la première base juridique

### Étape 1 : Collecte des sources (Semaine 3-4)

- **Sources officielles** : Légifrance (API ou scraping légal), Code civil, Code de commerce, Code des sociétés
- **Doctrine** : articles juridiques, revues spécialisées (actualité du droit)
- **Jurisprudence** : décisions de cour d'appel et Cour de cassation pertinentes
- **Modèles** : modèles de statuts (SAS, SARL, SA), modèles de pactes d'associés

### Étape 2 : Structuration (Semaine 4-5)

- Découpage en **chunks** pertinents (articles, clauses, paragraphes)
- Enrichissement métadonnées (code, date, domaine, mots-clés)
- Tagging par catégorie juridique (sociétés, obligations, travail, etc.)

### Étape 3 : Structuration et indexation (Semaine 5-6)

- Structuration en **entrées JSON** (schéma `legal_kb/schema.json`) : article, domaine, mots-clés, types de documents, règles de contrôle
- **Recherche RAG-lite** (`knowledge_base.search_relevant`) : classement par type de document + termes de l'anomalie + domaine — aucune indexation vectorielle requise
- Création d'un index par mots-clés pour recherche hybride

### Étape 4 : Validation et enrichissement (Semaine 6-7)

- Validation par un **expert juridique** (si disponible) ou par confrontation croisée
- Enrichissement avec des **Q&A juridiques** pour le fine-tuning éventuel
- Création de **cas tests** pour évaluer la qualité de la base

### Étape 5 : Maintenance et mise à jour (continu)

- Script de mise à jour périodique des sources officielles
- Alertes sur les évolutions législatives
- Versioning de la base de connaissances

---

## 6. Planning prévisionnel sur 2 mois (8 semaines)

### Semaine 1 — Cadrage et environnement
- Installation et configuration de l'environnement de développement
- Analyse approfondie des besoins fonctionnels
- Cahier des charges détaillé
- Choix des modèles et benchmarks初步
- Architecture détaillée du système

### Semaine 2 — Module d'ingestion et OCR
- Développement du module de lecture PDF (PyMuPDF)
- Intégration de Tesseract pour OCR
- Extraction structurée du texte
- Tests avec différents formats de documents
- Classification basique des types de documents

### Semaine 3 — Module d'extraction et NER
- Entraînement/adaptation du modèle NER pour le juridique
- Extraction des clauses (identification, catégorisation)
- Extraction des entités nommées (parties, dates, montants, articles)
- Structuration JSON des données extraites
- Tests unitaires sur cas réels

### Semaine 4 — Module de comparaison et règles
- Développement du moteur de comparaison multi-documents
- Détection des contradictions et incohérences
- Moteur de règles juridiques (première version)
- Identification des clauses manquantes
- Scoring de sévérité des écarts

### Semaine 5 — Base de connaissances juridique (RAG-lite)
- Collecte et structuration des sources juridiques (entrées JSON réelles)
- Recherche locale par type de document + termes + domaine
- Rattachement des références à Légifrance/PISTE
- Tests de recherche et pertinence

### Semaine 6 — Module IA et analyse
- Intégration des fournisseurs IA (Groq, OpenRouter) avec repli local
- Chaîne d'analyse (synthèse, analyse de clauses)
- Génération de recommandations
- Détection des risques
- Propositions d'amélioration

### Semaine 7 — Reporting et validation humaine
- Génération de rapports PDF (ReportLab)
- Mise en page professionnelle
- Système de scoring de confiance
- Interface de validation humaine (Streamlit)
- Intégration API (FastAPI)

### Semaine 8 — Tests, optimisation et finalisation
- Tests d'intégration complets
- Optimisation des performances
- Documentation technique et utilisateur
- Démonstrateur fonctionnel
- Préparation de la soutenance/présentation

### Planning visuel

```
Semaine:  1    2    3    4    5    6    7    8
          ├────┼────┼────┼────┼────┼────┼────┤
Cadrage   ████████
Ingestion       ████████
Extraction           ████████
Comparaison               ████████
Base juridique                 ████████
LLM Analyse                        ████████
Reporting                              ████████
Finalisation                                ████████
```

---

## 7. Principaux risques techniques et juridiques

### Risques techniques

| Risque | Probabilité | Impact | Mitigation |
|--------|------------|--------|------------|
| Performance insuffisante du LLM pour l'analyse juridique | Moyenne | Élevé | Utiliser des modèles optimisés (quantization), chunking intelligent |
| Qualité OCR insuffisante sur documents扫描és | Moyenne | Moyen | Pré-traitement images, modèle OCR spécialisé, fallback manuel |
| Hallucinations du LLM (références inexistantes) | Élevée | Élevé | RAG systématique, vérification croisée, scoring de confiance |
| Temps de réponse trop long pour l'utilisateur | Moyenne | Moyen | Cache, async, traitement par lots, modèles légers |
| Intégration difficile avec l'existant TOP-JURIDIQUE | Faible | Élevé | API REST propre, documentation, tests d'intégration |
| Données d'entraînement insuffisantes | Moyenne | Élevé | Augmentation de données, few-shot learning, prompts soignés |

### Risques juridiques

| Risque | Probabilité | Impact | Mitigation |
|--------|------------|--------|------------|
| Le LLM produit des conseils juridiques erronés | Élevée | Très élevé | **Disclaimer systématique**, validation humaine obligatoire, scoring de confiance |
| Non-conformité RGPD (données clients) | Faible | Élevé | Pas de stockage persistant des données sensibles, chiffrement |
| Responsabilité en cas d'erreur | Moyenne | Très élevé | CGU claires, "outil d'aide" et non "conseil juridique", assurance RC |
| Utilisation non autorisée de sources protégées | Faible | Moyen | Utilisation de sources officielles libres d'accès, veille juridique |
| Biais dans les modèles IA | Moyenne | Moyen | Diversité des sources, évaluation régulière, transparence |

### Mesures transversales

- **Disclaimer juridique obligatoire** sur chaque rapport généré
- **Validation humaine** systématique avant diffusion
- **Audit de traçabilité** (quel modèle, quelles sources, quand)
- **Versioning** des analyses pour rollback possible

---

## 8. Livrables réalisables dans le délai de 2 mois

### Livrables fonctionnels

| # | Livrable | Priorité | Semaine | Statut estimé |
|---|---------|----------|---------|---------------|
| L1 | Module d'ingestion et OCR multi-format | P0 | S2 | Réalisable |
| L2 | Module de classification de documents | P0 | S3 | Réalisable |
| L3 | Module d'extraction structurée (NER) | P0 | S3 | Réalisable |
| L4 | Module de comparaison multi-documents | P0 | S4 | Réalisable |
| L5 | Moteur de règles juridiques (v1) | P1 | S4 | Réalisable |
| L6 | Base de connaissances juridiques (v1) | P1 | S5 | Réalisé (18 entrées réelles) |
| L7 | Module d'analyse IA (optionnel, repli local) | P0 | S6 | Réalisable |
| L8 | Générateur de rapports PDF | P1 | S7 | Réalisable |
| L9 | Interface Streamlit (POC) | P1 | S7 | Réalisable |
| L10 | API REST (FastAPI) | P2 | S7-8 | Réalisable |

### Livrables techniques

| # | Livrable | Description |
|---|---------|-------------|
| T1 | Code source complet | Repository propre, documenté, avec README |
| T2 | Tests unitaires | Couverture minimale 70% sur modules critiques |
| T3 | Documentation technique | Architecture, API, guide d'installation |
| T4 | Démonstrateur fonctionnel | Cas d'usage complet (pacte vs statuts SAS) |
| T5 | Base juridique v1 | 18 entrées réelles (Code de commerce, Code civil) interrogées via RAG-lite |
| T6 | Configuration modèles | Clés API dans `.env` (Groq, OpenRouter), repli local |

### Livrables documentaires

| # | Livrable | Description |
|---|---------|-------------|
| D1 | Compréhension de la mission | Ce document |
| D2 | Benchmark legaltech | Analyse concurrentielle |
| D3 | Cas d'usage détaillé | Spécification fonctionnelle |
| D4 | Architecture technique | Diagrammes et choix techniques |
| D5 | Guide utilisateur | Manuel d'utilisation de la démo |
| D6 | Rapport de stage | Bilan complet du stage |

### Ce qui ne sera PAS réalisé (hors périmètre 2 mois)

- Fine-tuning complet d'un modèle juridique
- Production-ready avec déploiement cloud
- Multi-lingue (anglais, etc.)
- Intégration complète avec les logiciels existants (Clio, etc.)
- Conformité RGPD complète (nécessite DPO)
- Certification juridique des analyses

---

## Synthèse

La mission consiste à concevoir et développer un prototype fonctionnel d'un copilote juridique IA capable de comparer, analyser et auditer des documents juridiques français. Le premier cas d'usage (pacte d'associés vs statuts) servira de démonstrateur pour valider l'approche technique et fonctionnelle. L'architecture modulaire garantit l'évolutivité et l'intégration à l'écosystème TOP-JURIDIQUE existant.

> **Note** : Ce document est un living document qui sera mis à jour en fonction des découvertes techniques et des orientations du superviseur durant le stage.
