# TOP-JURIDIQUE — Cas d'usage n°1 : Analyse d'un pacte d'associés comparé aux statuts

> Spécification fonctionnelle détaillée du premier cas d'usage à implémenter.
> Document de référence pour le développement | Date : Juillet 2026

---

## 1. Pourquoi ce cas d'usage ?

### 1.1 Pertinence métier

Le **pacte d'associés** (ou pacte d'actionnaires) est l'un des documents juridiques les plus utilisés dans la vie des sociétés commerciales françaises. Il complète les statuts et régit les relations entre associés sur des aspects que les statuts ne couvrent pas ou ne couvrent que partiellement.

### 1.2 Problème concret

| Problème | Impact | Fréquence |
|----------|--------|-----------|
| Contradictions entre pacte et statuts | Nullité partielle, conflits entre associés | Fréquent (estimé 30-40% des pactes) |
| Clauses manquantes | Vide juridique, litiges potentiels | Très fréquent |
| Clauses non conformes au droit en vigueur | Inopposabilité, sanctions | Fréquent après évolutions législatives |
| Rédaction approximative | Interprétations divergentes, contentieux | Très fréquent |
| Vérification manuelle chronophage | 4-8h par juriste expérimenté | Systématique |

### 1.3 Valeur ajoutée de l'automatisation

| Aspect | Manuel | Avec TOP-JURIDIQUE |
|--------|--------|-------------------|
| Temps d'analyse | 4-8 heures | 5-15 minutes |
| Couverture | Partielle (selon expérience) | Systématique et complète |
| Références légales | Recherche manuelle | Automatisée (Légifrance) |
| Rapport | Word/PDF rédigé à la main | PDF structuré généré automatiquement |
| Suivi des évolutions | Non | Alerte sur changements législatifs |
| Reproductibilité | Variable | Identique à chaque exécution |

---

## 2. Description fonctionnelle du cas d'usage

### 2.1 Flux d'utilisation

```
Utilisateur                     TOP-JURIDIQUE
    │                               │
    │  1. Upload pacte d'associés   │
    │  ──────────────────────────>  │
    │                               │  2. Ingestion & OCR
    │                               │  3. Classification
    │                               │  4. Extraction des clauses
    │                               │
    │  5. Upload statuts            │
    │  ──────────────────────────>  │
    │                               │  6. Ingestion & OCR
    │                               │  7. Classification
    │                               │  8. Extraction des clauses
    │                               │
    │                               │  9. Comparaison multi-docs
    │                               │  10. Détection contradictions
    │                               │  11. Détection risques
    │                               │  12. Vérification conformité
    │                               │  13. Recherche sources légales
    │                               │  14. Génération recommandations
    │                               │
    │  15. Rapport PDF              │
    │  <──────────────────────────  │
    │                               │
    │  16. Validation humaine       │
    │  ──────────────────────────>  │
    │                               │  17. Validation / corrections
    │                               │
    │  18. Rapport final            │
    │  <──────────────────────────  │
```

### 2.2 Données en entrée

| Document | Format | Contenu attendu |
|----------|--------|-----------------|
| **Pacte d'associés** | PDF, DOCX | Pacte entre associés d'une SAS (ou autre forme) : clauses de gouvernance, cession, préemption, sortie, etc. |
| **Statuts de la société** | PDF, DOCX | Statuts constitutifs : forme juridique, capital, objet, gouvernance, obligations des associés, etc. |

### 2.3 Informations à extraire

#### A. Identification du document

- Type de document (pacte, statuts, avenant, contrat...)
- Société concernée (dénomination sociale)
- Forme juridique (SAS, SARL, SA, SCI...)
- Date de signature / modification
- Parties prenantes (noms, qualités)
- Capital social (si applicable)

#### B. Extraction des clauses (par document)

| Catégorie de clause | Exemples | Priorité |
|--------------------|---------|----------| 
| **Gouvernance** | Composition dirigeants, pouvoirs, quorum, majorité | Haute |
| **Cession de parts/actions** | Clause d'agrément, préemption, inaliénabilité | Haute |
| **Sortie** | Clause de sortie, rachat, valorisation | Haute |
| **Anti-dilution** | Protection contre dilution, préférence | Moyenne |
| **Non-concurrence** | Obligations de non-concurrence, durée, périmètre | Moyenne |
| **Dividendes** | Politique de distribution, priorités | Moyenne |
| **Litiges** | Arbitrage, juridiction compétente, médiation | Haute |
| **Obligations financières** | Apports, cautions, garanties | Haute |
| **Confidentialité** | Obligations de confidentialité, durée | Moyenne |
| **Gouvernance extra-statutaire** | Comités, conseils, réunions | Moyenne |

#### C. Informations structurées à extraire

```json
{
  "clauses": [
    {
      "id": "PACTE-001",
      "categorie": "Gouvernance",
      "titre": "Composition du conseil d'administration",
      "contenu_original": "...",
      "articles_references": ["Art. L225-37 Code de commerce"],
      "obligations": ["..."],
      "conditions": ["..."],
      "délais": ["..."],
      "sanctions": ["..."],
      "risques_identifiés": [],
      "score_confiance": 0.85
    }
  ]
}
```

---

## 3. Fonctionnalités détaillées

### 3.1 Identification et catégorisation des clauses

Le système doit :

1. **Segmenter** chaque document en clauses individuelles
2. **Catégoriser** chaque clause selon un thésaurus juridique
3. **Hiérarchiser** les clauses par importance et criticité
4. **Indexer** pour recherche ultérieure

### 3.2 Extraction structurée

Pour chaque clause, le système extrait :
- **Texte original** de la clause
- **Résumé** en langage clair
- **Références légales** citées ou implicites
- **Obligations** créées
- **Conditions** d'application
- **Délais** mentionnés
- **Sanctions** prévues
- **Points d'attention** (clauses inhabituelles, à risque)

### 3.3 Détection des contradictions

| Type de contradiction | Exemple | Sévérité |
|----------------------|---------|----------|
| **Directe** | Pacte dit "majorité simple", statuts disent "unanimité" | Critique |
| **Implicite** | Pacte crée une obligation que statuts interdisent | Majeure |
| **Temporelle** | Pacte prévoit 2 ans, statuts prévoient 5 ans | Majeure |
| **Financière** | Pacte prévoit valorisation X, statuts prévoient valorisation Y | Critique |
| **Procédurale** | Pacte prévoit médiation, statuts prévoient arbitrage | Mineure |

### 3.4 Détection des clauses manquantes

Le système compare les clauses extraites avec une **base de référence** (modèle type) et identifie les absences :

| Clause attendue | Présente ? | Risque si absente |
|----------------|------------|-------------------|
| Clause d'agrément | Non | Cession libre possible, risque d'entrée d'associés indésirables |
| Clause de préemption | Non | Pas de droit de priorité |
| Clause de sortie | Non | Pas de mécanisme de liquidité |
| Clause de non-concurrence | Non | Associé peut créer une concurrence |
| Clause d'anti-dilution | Non | Dilution possible sans protection |
| Clause de gouvernance | Non | Gouvernance uniquement statutaire |

### 3.5 Identification des risques

Pour chaque risque identifié, le système fournit :

```json
{
  "risque": {
    "id": "RISK-001",
    "type": "Contradiction",
    "severite": "Critique",
    "description": "La clause de majorité au conseil d'administration est contradictoire entre le pacte (majorité qualifiée) et les statuts (majorité simple)",
    "clauses_impliquees": ["PACTE-003", "STATUT-012"],
    "consequence": "Possible nullité de la décision prise",
    "reference_legale": "Art. L225-99 Code de commerce",
    "recommandation": "Harmoniser les deux textes en faveur de la majorité qualifiée (plus protectrice)",
    "score_confiance": 0.92
  }
}
```

### 3.6 Vérification par rapport aux sources officielles

Le système croise les clauses avec les sources légales :

| Source | Utilisation |
|--------|------------|
| **Code de commerce** | Formes de sociétés, gouvernance, cession |
| **Code civil** | Obligations, contrats, nullités |
| **Code des sociétés** (si applicable) | Dispositions spécifiques |
| **Légifrance** | Textes en vigueur, mises à jour |
| **Jurisprudence** | Interprétations des tribunaux |
| **Doctrine** | Analyses d'experts |

### 3.7 Propositions d'amélioration

Pour chaque problème identifié, le système propose :

1. **Reformulation** de la clause problématique
2. **Ajout** de clauses manquantes (avec modèle)
3. **Suppression** de clauses obsolètes ou non conformes
4. **Modification** de clauses à risque
5. **Références légales** à intégrer

### 3.8 Génération du rapport

Le rapport PDF contient :

```
┌─────────────────────────────────────────────┐
│           RAPPORT D'ANALYSE JURIDIQUE       │
│           TOP-JURIDIQUE                      │
├─────────────────────────────────────────────┤
│                                             │
│  1. RÉSUMÉ EXÉCUTIF                         │
│     - Objet de l'analyse                    │
│     - Société concernée                     │
│     - Date d'analyse                        │
│     - Score de confiance global             │
│     - Nombre de problèmes identifiés        │
│                                             │
│  2. INFORMATIONS GÉNÉRALES                  │
│     - Dénomination sociale                  │
│     - Forme juridique                       │
│     - Capital social                        │
│     - Date de création/modification         │
│                                             │
│  3. TABLEAU COMPARATIF                      │
│     | Clause | Pacte | Statuts | Conforme |  │
│     |--------|-------|---------|----------|  │
│                                             │
│  4. CONTRADICTIONS IDENTIFIÉES              │
│     - Description                           │
│     - Sévérité (Critique/Majeure/Mineure)   │
│     - Impact                                │
│     - Recommandation                        │
│                                             │
│  5. CLAUSES MANQUANTES                      │
│     - Liste des clauses absentes            │
│     - Risque associé                        │
│     - Modèle de clause recommandée          │
│                                             │
│  6. RISQUES JURIDIQUES                      │
│     - Détection des risques                 │
│     - Scoring de sévérité                   │
│     - Références légales                    │
│     - Recommandations                       │
│                                             │
│  7. RÉFÉRENCES LÉGALES                      │
│     - Articles de loi cités                 │
│     - Jurisprudence pertinente              │
│     - Liens Légifrance                      │
│                                             │
│  8. PROPOSITIONS D'AMÉLIORATION             │
│     - Reformulations proposées              │
│     - Clauses à ajouter                     │
│     - Modifications à apporter              │
│                                             │
│  9. VALIDATION HUMAINE                      │
│     - Points nécessitant validation         │
│     - Niveau de confiance par section       │
│     - Recommandation d'intervention experte │
│                                             │
│ 10. ANNEXES                                 │
│     - Détail des extractions                │
│     - Sources consultées                    │
│     - Historique des analyses               │
│                                             │
├─────────────────────────────────────────────┤
│  AVERTISSEMENT : Ce rapport est généré      │
│  par une IA et ne constitue pas un avis     │
│  juridique. Il nécessite une validation      │
│  par un professionnel du droit.             │
└─────────────────────────────────────────────┘
```

---

## 4. Exemple concret d'analyse

### 4.1 Documents d'entrée

**Document 1 : Pacte d'associés de la SAS "TechInnov"**
- Signé le 15/03/2024
- Entre M. Martin (60%) et Mme Durand (40%)
- Contient : clause d'agrément, clause de préemption, clause de sortie, clause de non-concurrence

**Document 2 : Statuts de la SAS "TechInnov"**
- Modifiés le 01/01/2023
- Capital : 10 000 €
- Contient : gouvernance, objet, capital, dissolution

### 4.2 Résultats attendus de l'analyse

| # | Problème | Type | Sévérité |
|---|---------|------|----------|
| 1 | Contradiction sur la majorité au CA (pacte : 2/3, statuts : majorité simple) | Contradiction | Critique |
| 2 | Clause d'agrément dans le pacte mais pas dans les statuts | Incohérence | Majeure |
| 3 | Absence de clause de valuation en cas de sortie | Clause manquante | Majeure |
| 4 | Clause de non-concurrence de 3 ans (possible excès) | Risque | Mineure |
| 5 | Référence à ancien Code des sociétés (obsolète) | Conformité | Majeure |
| 6 | Absence de clause de médiation | Clause manquante | Mineure |
| 7 | Pacte prévoit 60 jours pour exercer la préemption, statuts 30 jours | Contradiction | Majeure |

### 4.3 Extraits du rapport généré

```
RÉSUMÉ EXÉCUTIF
═══════════════
Analyse comparative du Pacte d'associés et des Statuts de la SAS "TechInnov".
Score de confiance global : 87%

Problèmes identifiés :
  - 2 contradictions (dont 1 critique)
  - 2 clauses manquantes
  - 1 risque identifié
  - 1 problème de conformité

Recommandation : Révision complète recommandée avant prochaine assemblée.

───────────────────────────────────────────────

CONTRADICTION #1 — CRITIQUE
═════════════════════════════
Objet : Majorité au Conseil d'Administration
Pacte (Art. 5.2) : Majorité qualifiée des 2/3
Statuts (Art. 18) : Majorité simple

Impact : Les décisions du CA pourraient être prises selon un régime 
incertain, créant un risque de nullité.

Référence : Art. L225-99 du Code de commerce

Recommandation : Harmoniser en faveur de la majorité qualifiée (plus 
protectrice) ou prévoir un régime dérogatoire clair dans le pacte avec 
référence explicite aux statuts.

Score de confiance : 95%

───────────────────────────────────────────────

CLAUSE MANQUANTE — MAJEURE
═══════════════════════════
Objet : Clause de valuation en cas de sortie
Statut : Absente des deux documents

Impact : En cas de départ d'un associé, la valorisation des parts 
pourrait être contestée, créant un litige potentiel.

Modèle recommandé :
"En cas de sortie d'un associé, la valorisation des actions sera 
déterminée par un expert indépendant désigné d'un commun accord, 
ou à défaut par le Président du Tribunal de commerce, en application 
de l'article 1843-4 du Code civil."

Score de confiance : 88%
```

---

## 5. Extension à d'autres types de documents

### 5.1 Documents compatibles avec le même moteur

| Type de document | Comparaison possible | Priorité |
|-----------------|---------------------|----------|
| **Pacte d'associés ↔ Statuts** | ✅ Premier cas d'usage | P0 |
| **Contrat ↔ Avenant** | ✅ Vérification cohérence | P1 |
| **Statuts (version ancienne) ↔ Statuts (version nouvelle)** | ✅ Suivi des modifications | P1 |
| **Modèle type ↔ Document personnalisé** | ✅ Vérification complétude | P1 |
| **Contrat ↔ Conditions générales** | ✅ Cohérence interne | P2 |
| **Offre ↔ Contrat signé** | ✅ Vérification intégralité | P2 |
| **Projet de délibération ↔ Procès-verbal** | ✅ Conformité | P2 |

### 5.2 Adaptations nécessaires pour chaque type

Chaque type de document nécessite :
1. Un **thésaurus de clauses** adapté
2. Des **règles de conformité** spécifiques
3. Des **références légales** ciblées
4. Un **modèle de rapport** ajusté

### 5.3 Évolution future

Le moteur de comparaison pourra être étendu à :
- **Droit du travail** (contrat de travail ↔ convention collective)
- **Droit immobilier** (bail ↔ état des lieux)
- **Droit de la propriété intellectuelle** (licence ↔ brevet)
- **Droit bancaire** (offre de prêt ↔ conditions générales)

---

## 6. Critères de succès

| Critère | Mesure | Objectif |
|---------|--------|----------|
| **Extraction** | Taux de clauses correctement identifiées | ≥ 90% |
| **Contradictions** | Taux de détection des contradictions connues | ≥ 95% |
| **Clauses manquantes** | Taux de détection vs checklist de référence | ≥ 85% |
| **Références légales** | Pertinence des articles cités | ≥ 80% |
| **Rapport** | Qualité perçue par un juriste testeur | ≥ 4/5 |
| **Temps** | Durée d'analyse complète | ≤ 15 minutes |
| **Confiance** | Précision du scoring de confiance | ≥ 85% |

---

## 7. Données de test

### 7.1 Cas de test requis

| # | Cas | Complexité | Objectif |
|---|-----|-----------|----------|
| CT-01 | SAS simple, 2 associés, pacte standard | Facile | Validation de base |
| CT-02 | SAS complexe, 5 associés, pacte avec avenants | Moyen | Gestion de la complexité |
| CT-03 | SARL, 2 associés, statuts anciens vs pacte récent | Moyen | Ancienneté des textes |
| CT-04 | SA, actionnaires multiples, pacte cadre | Difficile | Multi-parties |
| CT-05 | Documents avec OCR (scannés) | Variable | Test OCR |
| CT-06 | Document incomplet (pages manquantes) | Variable | Gestion des erreurs |

### 7.2 Données synthétiques

Si des documents réels ne sont pas disponibles, créer des **documents synthétiques** représentatifs avec :
- Des contradictions volontaires
- Des clauses manquantes intentionnelles
- Des références légales correctes et incorrectes
- Différentes formes juridiques (SAS, SARL, SA)
