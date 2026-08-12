# Présentation du stage — Copilote IA Juridique pour TOP-JURIDIQUE

**Stagiaire :** Hichem Mhadhbi
**Sujet :** Prototype de copilote IA d'analyse de documents juridiques
**Point principal :** comment l'outil aide le **formaliste** au quotidien

---

## 1. Le pitch en 30 secondes

L'outil développé est un **copilote d'analyse de dossiers juridiques** : il prend en entrée les documents
d'une société (pacte d'associés, statuts, contrats…), extrait les informations clés, applique
**19 règles de contrôle juridique**, compare les documents entre eux, puis génère un
**rapport de contrôle professionnel** qui liste les contradictions, les clauses manquantes et les risques,
chacun expliqué, **sourcé (Légifrance/PISTE)** et accompagné d'une correction recommandée.

La décision finale reste toujours au **formaliste** : l'outil signale, il ne décide pas.

---

## 2. L'utilité pour le formaliste (l'essentiel de la demande)

### 2.1 Le rôle du formaliste, et ses difficultés

Le formaliste prépare et vérifie les actes avant leur dépôt (greffe, RCS, INPI) :
il doit s'assurer que les documents d'un dossier sont **complets**, **cohérents entre eux** et
**conformes** aux règles de droit. Ses difficultés quotidiennes :

- **Relire manuellement** des dizaines de pages (pacte, statuts, PV) à la recherche d'incohérences ;
- **Croiser deux documents** (pacte vs statuts) pour vérifier qu'ils disent la même chose ;
- **Repérer les clauses manquantes** avant qu'un tiers ou un refus de dépôt ne les mette en évidence ;
- **Gérer sa responsabilité professionnelle** : une incohérence non détectée peut être reprochée.

### 2.2 Ce que l'outil apporte concrètement

| Bénéfice | Exemple concret |
|---|---|
| **Gain de temps** | Analyse complète d'un pacte + statuts en **quelques minutes** au lieu d'une relecture manuelle de plusieurs heures |
| **Contradictions détectées** | Un droit de veto présent dans le pacte mais **absent des statuts** → alerté immédiatement |
| **Complétude du dossier** | Détection des **documents manquants** (ex. : statuts absents d'un dossier de société) |
| **Risques identifiés et priorisés** | 3 niveaux : **bloquant** (à corriger avant action), **important**, **alerte** |
| **Chaque point est sourcé** | Chaque anomalie cite sa base juridique (Code de commerce, Code civil) avec lien Légifrance — **aucune référence inventée** |
| **Corrections suggérées** | Pour chaque anomalie : une rédaction/action correctrice recommandée |
| **Traçabilité totale** | Rapport professionnel exportable en PDF, conversation avec le document, historique |
| **Maîtrise humaine** | Chaque anomalie doit être **validée, modifiée ou rejetée** par le professionnel — le formaliste garde la main |

### 2.3 Le bénéfice de confiance

Pour un formaliste, la valeur n'est pas seulement le temps gagné : c'est la **réduction du risque
d'erreur** et donc du **risque de responsabilité professionnelle**. L'outil agit comme un
**deuxième jeu d'yeux systématique et exhaustif** qui ne se fatigue pas — tout en laissant le
professionnel décider en dernier ressort.

---

## 3. Ce que fait l'outil — le pipeline en 7 étapes

Comme une chaîne de montage :

```
1. INGESTION    → lecture des fichiers (PDF natif, PDF scanné via OCR, Word, images, texte)
2. CLASSIFICATION → deviner le type de document (pacte, statuts, autre) + signaler les documents manquants
3. EXTRACTION   → trouver les dates, montants, parties, références d'articles, clauses
4. COMPARAISON  → croiser 2 documents (pacte vs statuts) et relever les incohérences
5. RÈGLES       → appliquer 19 règles de contrôle juridique déterministes
6. BASE JURIDIQUE (RAG-lite) → rattacher chaque anomalie aux articles et règles pertinents
7. RAPPORT      → générer le rapport final (KPI, anomalies, incohérences, risque global, export PDF)
```

### Les formats gérés

**PDF natif, PDF scanné (OCR Tesseract en français), Word (.docx/.doc), images (PNG/JPG/JPEG), texte (.txt)**.

### Les 3 niveaux de priorité des anomalies

| Priorité | Signification |
|---|---|
| **Bloquant** | Le document est incomplet ou contraire à une règle — à corriger avant toute action |
| **Important** | Risque juridique réel à traiter |
| **Alerte** | Point de vigilance à vérifier |

---

## 4. Les 19 règles de contrôle (le cœur métier)

### 13 règles de risques immédiats

1. Clause d'agrément absente ou incomplète
2. Clause de sortie d'associé
3. Droit de veto
4. Majorités de décision
5. Clause de non-concurrence
6. **Contradiction pacte / statuts**
7. Clause de blocage de la société
8. Pouvoirs du gérant / responsabilité
9. PV : quorum
10. PV : résolutions
11. Modification statutaire
12. Champs à compléter (information manquante)
13. Formulations et forme

### 6 règles de risques futurs (anticipation)

14. Valorisation des titres en cas de sortie
15. Décès ou incapacité d'un associé (aucune clause prévue)
16. Non-paiement (impayé) d'un associé
17. Confidentialité / secret des affaires
18. Résiliation : durée sans issue possible
19. Déséquilibre de gouvernance

Les règles sont **déterministes** (pas du hasard) : le même document donne toujours le même résultat,
chaque alerte est explicable ligne par ligne.

---

## 5. Fiabilité juridique : la base de connaissances

- **Base locale structurée** : 18 entrées réelles (10 droit des sociétés / Code de commerce + 8 pactes d'associés / Code civil), chacune avec article, version, dates de vigueur, mots-clés et règles de contrôle associées.
- **RAG-lite** : à chaque analyse, les entrées pertinentes sont **réellement interrogées** et citées dans le rapport (chiffre affiché).
- **Vérification officielle Légifrance / PISTE** : le service obtient un jeton OAuth2 et vérifie chaque référence ou renvoie un lien de recherche officiel.
- **Anti-hallucination** : le système **n'invente jamais** de référence juridique. Sans source fiable, il le dit explicitement.

---

## 6. Démo pas à pas (à présenter en direct)

### Préparation

1. Ouvrir l'application : version locale (`streamlit run app.py`) **ou** version en ligne (URL Render).
2. Préparer les documents d'exemple :
   - **Dossier de démonstration** : `livrables_stage/documents_exemple/pacte_associes_sarl.pdf` + `statuts_sarl.pdf`
   - **Dossier réel** (plus riche) : `analyse_reel/entrees/2B_MANAGEMENT/Pacte.pdf` + `Statuts.pdf`

### Déroulé (environ 10 minutes)

| Étape | Action | Ce qu'on montre |
|---|---|---|
| 1 | Déposer les 2 fichiers dans l'interface | Le multi-format : PDF, Word, images acceptés |
| 2 | Cliquer **« Analyser le dossier »** | Le pipeline tourne en quelques secondes |
| 3 | Regarder les **KPI** | Niveau de risque global, nombre d'anomalies, d'incohérences |
| 4 | Tableau **Documents analysés** | Types détectés automatiquement + documents manquants signalés |
| 5 | **Informations clés** | Dates, parties, montants extraits automatiquement |
| 6 | Cartes **Anomalies** | Badge de priorité + explication + source + correction recommandée |
| 7 | Cartes **Incohérences** | Contradictions pacte/statuts avec sévérité |
| 8 | Ouvrir la **Synthèse intelligente** (si clé IA configurée) | Résumé argumenté de l'analyse |
| 9 | Poser une question au **chatbot** | Ex. : « Quel est le droit de veto prévu ? », « Quels sont les risques bloquants ? » |
| 10 | **Exporter le rapport PDF** | Le document professionnel remis au client / versé au dossier |

### Les phrases à dire à l'étape 6

> « Ici, le système a détecté que la clause X du pacte n'est pas reprise dans les statuts.
> C'est une contradiction importante : elle est expliquée, sourcée (article de loi) et accompagnée
> d'une correction suggérée. C'est exactement le type de point qui peut poser problème au dépôt,
> ou être utilisé contre le client plus tard. »

---

## 7. Le travail réalisé pendant le stage

### Cheminement semaine par semaine

| Semaine | Travail effectué |
|---|---|
| 1-2 | Compréhension de la mission, benchmark de 18 solutions legaltech, définition du cas d'usage, choix techniques, architecture |
| 3-4 | Module d'ingestion multi-format + OCR, module d'extraction, création de la base juridique, moteur de 19 règles |
| 5-6 | Comparaison inter-documents (pacte vs statuts), RAG-lite, génération de rapport, interface Streamlit |
| 7 | API REST, module de validation humaine, 164 tests automatisés, tests sur dossiers réels |
| 8 | Déploiement (Render), documentation, démonstration, livrables |

### Les 17 points de la mission — tous traités

1. Compréhension de la mission et de l'écosystème legaltech
2. Traitement multi-format (PDF natif, scanné, Word, images, illisible, OCR)
3. Analyse des documents juridiques
4. Comparaison et détection de contradictions
5. Détection des risques (19 règles, dont 6 risques futurs)
6. Sources fiables et vérifiables (Légifrance, PISTE — jamais de référence inventée)
7. Base juridique structurée et interrogée (RAG-lite)
8. Rapport d'analyse clair et structuré
9. Export multi-formats (PDF, Markdown, JSON, texte)
10. Benchmark des solutions IA / legaltech (18 outils analysés)
11. Architecture technique modulaire (10 couches séparées)
12. Intégration TOP-JURIDIQUE (API REST documentée)
13. Cas d'usage : pacte d'associés comparé aux statuts
14. Validation juridique (process de validation humaine)
15. Livrables complets (code, base juridique, rapport, docs, tests)
16. Documentation et ressources officielles
17. Benchmark et suivi

### Chiffres clés du travail

| Indicateur | Valeur |
|---|---|
| Lignes de code Python | ~6 700 (30+ fichiers) |
| Tests automatisés | **164, tous verts** |
| Règles de contrôle | **19** (dont 6 risques futurs) |
| Entrées base juridique | **18**, réellement interrogées |
| Formats de fichiers | 6 (PDF, PDF scanné, Word, images, texte) |
| Fournisseurs IA | 3 (Groq, Google AI, OpenRouter) avec repli local |
| Exports | 4 (PDF, Markdown, JSON, texte) |
| Dossiers de démo réels analysés | 6 (SARL et SAS) |

---

## 8. Architecture en une page (vue simplifiée)

```
   PRESENTATION
   CLI (main.py) | Interface web Streamlit (app.py) | API REST FastAPI (api/)

        │
   ORCHESTRATION  →  services/analysis_service.py (le pipeline en 7 étapes)
        │
   INGESTION      →  lecture multi-format + OCR des PDF scannés
   EXTRACTION     →  dates, montants, parties, clauses
   COMPARAISON    →  croisement pacte / statuts
   RÈGLES         →  19 règles déterministes (rules_engine/)
   BASE JURIDIQUE →  legal_kb/ (18 entrées) + RAG-lite + Légifrance/PISTE
   RAPPORT        →  report_generator/ (Markdown, PDF, JSON)
   VALIDATION     →  validation/ (approbation/rejet/modification par le juriste)
```

**3 façons d'utiliser l'outil :**
1. **Interface web** (Streamlit) : déposer des fichiers, analyser, lire le rapport, poser des questions ;
2. **Ligne de commande** (CLI) : analyser un dossier de PDF sans interface ;
3. **API REST** (FastAPI) : prête à être intégrée dans la plateforme TOP-JURIDIQUE.

---

## 9. Limites honnêtes et suites possibles

### Limites actuelles du prototype

1. **Base juridique réduite** : 18 entrées couvrent le droit des sociétés et les pactes ; à étendre (PV, contrats, baux).
2. **Extraction par règles** (regex) : robuste mais pas encore du NLP avancé (spaCy, CamemBERT en cours d'évaluation).
3. **Intégration TOP-JURIDIQUE** : l'API est prête, mais l'accès à l'environnement de test reste à fournir.
4. **OCR sur le cloud** : l'OCR Tesseract n'est pas installé sur l'hébergement Render (les PDF scannés y sont signalés, l'OCR complet fonctionne en local).
5. **Clés IA optionnelles** : sans clé, l'outil fonctionne à 100 % en local ; l'IA enrichit (synthèse, analyse de clauses) quand une clé est configurée.

### Suites possibles

1. Connecter la plateforme TOP-JURIDIQUE à l'API (phase d'intégration).
2. Étendre la base juridique et les règles aux autres types de documents (PV, modifications statutaires, contrats).
3. NLP avancé pour l'extraction de clauses.
4. Dashboard juridique de validation (tableau de bord des dossiers).
5. Recherche vectorielle (embeddings + FAISS) en extension du RAG-lite.

---

## 10. Où trouver chaque chose

| Contenu | Emplacement |
|---|---|
| Rapport d'exemple généré | `livrables_stage/rapport_exemple/rapport_analyse.pdf` |
| Documents de démo | `livrables_stage/documents_exemple/` |
| Analyse complète du travail | `livrables_stage/analyse_complete_travail.md` |
| Benchmark des solutions | `livrables_stage/benchmark_solutions_ia.md` |
| Documentation mission & architecture | `docs/01…06` |
| Code source + tests | racine du projet (`app.py`, `main.py`, `services/`, `rules_engine/`, `tests/`) |
| Démo en ligne | URL Render (https://top-juridique-copilote-iqgi.onrender.com) |

---

**Projet réalisé dans le cadre du stage TOP-JURIDIQUE — Prototype Copilote IA Juridique.**
