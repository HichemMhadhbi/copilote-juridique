# Rapport d'Analyse Juridique — TOP-JURIDIQUE

**Rapport ID :** `196dc871-9f66-4262-9d65-031999e469c5`  
**Date d'analyse :** 2026-08-04T17:32:36.218524

---

## 1. Documents Analysés

- **statuts_sarl.pdf** — Type: statuts de societe — Statut: analyse
- **pacte_associes_sarl.pdf** — Type: pacte d'associes — Statut: analyse

## 2. Informations Principales

**Nombre Documents :** 2
**Types Documents :** {'statuts_sarl.pdf': 'statuts de societe', 'pacte_associes_sarl.pdf': "pacte d'associes"}
**Regles Controle Appliquees :** True
**Entites Extraites :** {'statuts_sarl.pdf': {'dates': [], 'montants': [{'valeur': '50000', 'devise': 'EUR', 'position': 494}, {'valeur': '100', 'devise': 'EUR', 'position': 540}], 'parties': [{'nom': 'STATUTS DE LA SOCIETE TOP LEGAL CONSEIL', 'type': 'societe', 'position': 0}, {'nom': 'SARL', 'type': 'societe', 'position': 41}], 'personnes': [], 'articles': []}, 'pacte_associes_sarl.pdf': {'dates': [], 'montants': [{'valeur': '50000', 'devise': 'EUR', 'position': 297}, {'valeur': '100', 'devise': 'EUR', 'position': 343}], 'parties': [{'nom': 'PACTE D', 'type': 'societe', 'position': 0}, {'nom': 'ASSOCIES', 'type': 'societe', 'position': 8}, {'nom': 'SARL TOP LEGAL CONSEIL', 'type': 'societe', 'position': 19}], 'personnes': [], 'articles': []}}
**Base Juridique :** 18 entrees
**Statut Lecture :** {'statuts_sarl.pdf': 'natif', 'pacte_associes_sarl.pdf': 'natif'}
**Qualite Documents :** {'statuts_sarl.pdf': {'illisible': False, 'ocr_faible': False, 'page_manquante': False, 'incomplet': False, 'detail': 'lecture correcte'}, 'pacte_associes_sarl.pdf': {'illisible': False, 'ocr_faible': False, 'page_manquante': False, 'incomplet': False, 'detail': 'lecture correcte'}}
**Document Text :** STATUTS DE LA SOCIETE TOP LEGAL CONSEIL (SARL) Article 1 - Forme juridique La société est une société à responsabilité limitée (SARL) régie par le Code de commerce.
Article 2 - Objet social La société a pour objet le conseil juridique, la formation et toutes opérations connexes.
Article 3 - Dénomination sociale La société a pour dénomination sociale Top Legal Conseil.
Article 4 - Siège social Le siège social est fixé à Paris (75002).
Article 5 - Capital social Le capital social est fixé à 50 000 euros, divisé en 500 parts sociales de 100 euros.
Article 6 - Gérance et pouvoirs du gérant La société est gérée par un gérant nommé par les associés.
Le gérant dispose des pouvoirs les plus étendus pour agir au nom de la société, dans la limite de l'objet social et des restrictions prévues aux statuts.

PACTE D'ASSOCIES - SARL TOP LEGAL CONSEIL Article 1 - Objet du pacte Le présent pacte a pour objet de régir les relations entre les associés de la société Top Legal Conseil et de compléter les statuts.
Article 2 - Capital social et répartition des parts Le capital social de la société est fixé à 50 000 euros, divisé en 500 parts sociales de 100 euros chacune, réparties entre les associés.
Article 3 - Agrément des cessions de parts Toute cession de parts sociales à un tiers est soumise à l'agrément préalable des associés statuant à la majorité des deux tiers.
Article 4 - Non-concurrence Chaque associé s'engage, pendant la durée du pacte et pendant une durée de deux ans après sa cessation, à ne pas concurrencer la société.
Article 5 - Médiation en cas de conflit En cas de désaccord entre les associés, les parties conviennent de recourir à une médiation préalable avant toute action judiciaire.
**Sources Officielles :** {'mode': 'piste', 'piste_mode': 'oauth', 'piste_token_configured': True, 'anomalies_liees_a_legifrance': 3, 'anomalies_reference_fictive': 0, 'references_verifiees_piste': 3, 'verification_active': True, 'avertissement': "Les références marquées 'fictif' doivent être remplacées par de vraies références vérifiées via Légifrance/PISTE avant production."}

## 4. Anomalies Juridiques

### Anomalie 1 🔴 [BLOQUANT]

**Explication :** Aucune clause d'agrément trouvée dans le document. (cession de parts sociales, article L.223-14 du Code de commerce)

- **Nature du contrôle :** clause_manquante
- **Conséquence :** Aucune clause d'agrément trouvée dans le document. (cession de parts sociales, article L.223-14 du Code de commerce)
- **Source juridique :** Art. L223-14
- **Vérification source :** Vérifiée dans Légifrance (PISTE)
- **Extrait texte officiel :** Les parts sociales ne peuvent être cédées à des tiers étrangers à la société qu'avec le consentement de la majorité des associés représentant au moins la moitié des parts sociales, à moins que les statuts prévoient une majorité plus forte. Lorsque la société comporte plus d'un associé, le projet de cession est notifié à la société et à chacun des associés. Si la société n'a pas fait connaître sa d…
- **Correction recommandée :** Ajouter une clause d'agrément précisant la majorité requise pour l'entrée d'un nouvel associé.
- **Documents à vérifier :**
  - statuts_sarl.pdf
- **⚠️ Validation humaine requise**

### Anomalie 2 🟠 [IMPORTANT]

**Explication :** Aucune clause de sortie (drag-along / tag-along) identifiée.

- **Nature du contrôle :** clause_manquante
- **Conséquence :** Aucune clause de sortie (drag-along / tag-along) identifiée.
- **Source juridique :** Art. 1103 C. civ
- **Vérification source :** Vérifiée dans Légifrance (PISTE)
- **Extrait texte officiel :** Les contrats légalement formés tiennent lieu de loi à ceux qui les ont faits.…
- **Correction recommandée :** Envisager l'ajout d'une clause de sortie conjointe pour protéger les associés minoritaires.
- **Documents à vérifier :**
  - statuts_sarl.pdf
- **⚠️ Validation humaine requise**

### Anomalie 3 🟠 [IMPORTANT]

**Explication :** Aucun mécanisme de résolution de blocage (médiation / arbitrage) trouvé.

- **Nature du contrôle :** clause_manquante
- **Conséquence :** Aucun mécanisme de résolution de blocage (médiation / arbitrage) trouvé.
- **Source juridique :** Art. 1530 C. proc. civ
- **Vérification source :** Vérifiée dans Légifrance (PISTE)
- **Extrait texte officiel :** La conciliation et la médiation régies par le présent titre s'entendent de tout processus structuré par lequel plusieurs personnes tentent, avec l'aide d'un tiers, de parvenir à un accord destiné à la résolution du différend qui les oppose.…
- **Correction recommandée :** Ajouter une clause de médiation préalable et une clause compromissoire.
- **Documents à vérifier :**
  - statuts_sarl.pdf
- **⚠️ Validation humaine requise**

## 8. Niveau de Risque Global : 🟠 ELEVE

---
*Rapport généré automatiquement par TOP-JURIDIQUE — Copilote IA Juridique*
*Ce document nécessite une relecture par un professionnel du droit.*