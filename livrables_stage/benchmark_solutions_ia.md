# Benchmark des solutions IA juridiques — version simple

Date : août 2026

## En 10 lignes

J'ai analysé plus de 15 solutions d'IA juridique (françaises et internationales). Toutes se rangent dans 3 catégories :
1. **Les IA d'assistance** (Jimini, Ordalie, Haiku, Doctrine...) : elles aident le juriste à chercher, résumer et rédiger.
2. **Les outils d'entreprise** (Harvey, Luminance, Kira...) : très chers, réservés aux gros cabinets, orientés contrats.
3. **Les plateformes de formalités** (JURIDIFEEL, Manewco, LegalVision...) : elles gèrent la création d'entreprises et les démarches administratives.

**Aucune ne combine les deux : faire l'analyse juridique du contenu d'un dossier ET contrôler sa conformité aux formalités, avec validation par un juriste.**

C'est notre espace libre : TOP-JURIDIQUE = plateforme de formalités + copilote d'analyse du dossier.

---

## Le marché en 3 catégories

### Catégorie 1 — Les IA d'assistance (France)
Elles répondent à des questions de droit, résument et rédigent. Elles ne font pas de contrôle de dossier.

| Outil | Ce qu'il fait | Coût | Limite pour nous |
|-------|---------------|------|------------------|
| **Jimini AI** | Analyse de documents, recherche juridique, rédaction | ~250 €/mois/utilisateur | Pas de formalités, pas de contrôle de conformité |
| **Ordalie** | Répond aux questions de droit français, simple | 89 €/mois | Pas d'analyse multi-documents, pas de formalités |
| **Haiku** | Modèles IA entraînés sur le droit français | Low cost | Pas de contrôle de dossier, pas de formalités |
| **Doctrine** | Moteur de recherche juridique (jurisprudence) | Sur devis | C'est un moteur de recherche, pas un analyseur |
| **GenIA-L** (Lefebvre) | Recherche et rédaction juridique | Sur devis | Pas de formalités |
| **Predictice** | Justice prédictive (statistiques) | Sur devis | Complémentaire, pas notre métier |

### Catégorie 2 — Les outils d'entreprise (International)
Très puissants mais chers et orientés gros cabinets / contrats.

| Outil | Ce qu'il fait | Limite pour nous |
|-------|---------------|------------------|
| **Harvey** | Assistant IA des plus grands cabinets (recherche, rédaction, revue) | ~288 000 $/an, inaccessible, pas de droit français formaliste |
| **Luminance** | Revue de contrats en due diligence, 60+ langues | Enterprise, pas de formalités |
| **Kira** | Extraction de clauses (standard due diligence) | Pas de droit français formaliste |
| **Spellbook** | Rédaction/revue de contrats dans Word | 99-199 $/mois, droit nord-américain |
| **Ironclad** | Gestion du cycle de vie des contrats | Gestion contractuelle, pas d'analyse |
| **LegalOn** | Revue de contrats par « playbooks » d'avocats | Marché américain |
| **Robin AI** | Analyse de contrats | Activité réduite depuis fin 2025 (marché incertain) |

### Catégorie 3 — Les plateformes de formalités (France)
Concurrentes directes de la partie « formalités » de TOP-JURIDIQUE, mais sans analyse du contenu.

| Outil | Ce qu'il fait | Limite pour nous |
|-------|---------------|------------------|
| **JURIDIFEEL** | Génération d'actes, formalités, suivi des sociétés, IA contextualisée | Pas d'analyse de failles/risques du dossier |
| **Manewco** | Formalités pour professions du droit et du chiffre | Pas d'analyse juridique du contenu |
| **LegalVision** | Automatisation des formalités juridiques | Pas d'analyse juridique du contenu |
| **Leegal** | Création d'entreprise, formalités, multilingue | Pas d'analyse juridique du contenu |

### Outils utiles pour nous (sources de données)
| Outil | Ce qu'il apporte |
|-------|------------------|
| **Pappers** | Données officielles sur les entreprises (Kbis, statuts) → utile pour vérifier la conformité |
| **Légifrance / PISTE** | Les sources officielles du droit français (à intégrer dans notre base juridique) |

---

## Ce que le marché ne fait pas (notre avantage)

| Besoin du juriste | Solutions existantes | Nous |
|-------------------|---------------------|------|
| Analyser le contenu juridique d'un dossier | Certaines (Jimini) | ✅ intégré au dossier |
| Détecter les failles et risques (immédiats et futurs) | Presque aucune | ✅ 19 règles déterministes |
| Comparer 2 documents (pacte vs statuts) | Non | ✅ comparaison automatique |
| Contrôler la conformité aux formalités (Kbis, RCS...) | Non | ✅ à construire avec Pappers/Légifrance |
| Sources officielles citées (Légifrance/PISTE) | Partiellement | ✅ vérifiées via PISTE (OAuth2) ou liens Légifrance |
| Validation humaine obligatoire | Non | ✅ implémentée |
| Fonctionner sans envoyer de données à l'extérieur | Rare | ✅ repli local 100 % |

---

## Conclusion

Le marché est divisé : les IA d'assistance ne font pas de formalités, les plateformes de formalités ne font pas d'analyse juridique. **Notre prototype est le premier à vouloir faire les deux**, avec des règles traçables et une validation humaine obligatoire. C'est une vraie place à prendre.

À noter : le marché bouge vite (Ordalie annonce de l'analyse prédictive, Tomorro lance son IA). Il faut donc avancer sur l'intégration Légifrance/PISTE et la validation humaine dès les semaines 5-6 pour garder l'avantage.
