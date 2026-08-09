# 05 — Base de Connaissances Juridique

> **Mise à jour (état actuel)** : la base contient **18 entrées réelles** (10 droit des sociétés, 8 pactes d'associés), interrogées à chaque analyse via la **recherche RAG-lite** (`knowledge_base.search_relevant`). Aucune référence n'est fictive ni inventée.

## Vue d'ensemble

La base de connaissances juridique de TOP-JURIDIQUE fournit le référentiel normatif
utilisé par le moteur de règles et par la **recherche RAG-lite** pour contextualiser les analyses.

## Schéma de la base

```
legal_kb/
├── schema.json                # Schéma JSON de validation
├── knowledge_base.py          # Gestion + recherche RAG-lite (search_relevant)
└── data/
    ├── societes.json          # 10 entrées — droit des sociétés (Code de commerce)
    └── pactes.json            # 8 entrées — pactes d'associés (Code civil / proc. civile)
```

### Structure d'une entrée

Chaque entrée de la base suit le schéma JSON suivant (`legal_kb/schema.json`) :

```json
{
  "id": "SOC-001",
  "source": "Code de commerce",
  "titre_texte": "Code de commerce — Gérance de SARL",
  "numero_article": "Art. L223-18",
  "version": "2024",
  "date_entree_vigueur": "2024-01-01",
  "date_abrogation": null,
  "domaine": "droit des sociétés",
  "mots_cles": ["gérance", "SARL", "nomination", "pouvoirs", "représentation légale"],
  "types_documents_concernes": ["statuts", "pacte_associes"],
  "regles_controle": [
    {
      "type_regle": "conformité",
      "description": "Vérifier que les statuts désignent nommément le ou les gérants et précisent l'étendue de leurs pouvoirs.",
      "priorite": "bloquant",
      "correction_recommandee": "Ajouter la désignation du gérant et la limite de ses pouvoirs."
    }
  ]
}
```

### Champs obligatoires

| Champ | Type | Description |
|-------|------|-------------|
| `id` | string | Identifiant unique de l'entrée (ex. SOC-001) |
| `source` | string | Source officielle (Code de commerce, Légifrance…) |
| `titre_texte` | string | Titre complet du texte de référence |
| `numero_article` | string | Numéro de l'article concerné |
| `version` | string | Version ou millésime du texte |
| `date_entree_vigueur` | date | Date d'entrée en vigueur |
| `date_abrogation` | date\|null | Date d'abrogation éventuelle |
| `domaine` | string | Domaine juridique (droit des sociétés, droit commercial…) |
| `mots_cles` | list[str] | Mots-clés pour la recherche |
| `types_documents_concernes` | list[str] | Types de documents auxquels la règle s'applique |
| `regles_controle` | list[object] | Règles de contrôle associées (type, description, priorité, correction recommandée) |

## Sources de données

### Sources actuelles (implémentées)

- **Légifrance / PISTE** — Base officielle de la législation française (https://www.legifrance.gouv.fr)
  - Les 18 entrées sont des **articles réels** (ex. Art. L223-14, Art. 1103 C. civ, Art. 1530 C. proc. civ)
  - Vérification officielle : `services/legal_source_service.py` obtient un jeton PISTE (OAuth2) et vérifie chaque référence (identifiant LEGIARTI, texte officiel) ou renvoie un lien de recherche Légifrance

### Sources futures (évolutions)

- Étendre aux procès-verbaux, décisions sociales, modifications statutaires, contrats commerciaux, baux
- Doctrine et jurisprudence (Dalloz, Cour de cassation)
- Conventions collectives IDCC

## Méthode de mise à jour

### Mise à jour manuelle

```bash
# Ajout d'une entrée : modifier data/societes.json ou data/pactes.json en respectant schema.json
# Validation du format : les tests test_knowledge_base.py vérifient la conformité au schéma
```

### Mise à jour automatique (prévue)

```python
from services.legal_source_service import LegalSourceService

service = LegalSourceService()
service.fetch_and_update(article_refs=["L223-14", "1103", "1530"])
```

## Exemples d'entrées

### SOC-001 — Gérance de SARL (Code de commerce, Art. L223-18)

```json
{
  "id": "SOC-001",
  "source": "Code de commerce",
  "titre_texte": "Code de commerce — Gérance de SARL",
  "numero_article": "Art. L223-18",
  "domaine": "droit des sociétés",
  "mots_cles": ["gérance", "SARL", "nomination", "pouvoirs", "représentation légale"],
  "types_documents_concernes": ["statuts", "pacte_associes"]
}
```

### Entrée pacte — Règles de contrôle associées aux pactes (Code civil)

Les 8 entrées de `data/pactes.json` couvrent par exemple l'agrément des cessions de parts, les clauses de sortie, la non-concurrence et les mécanismes de résolution de blocage, avec les règles de contrôle rattachées.

## Utilisation par le pipeline

1. **Moteur de règles** — Consulte la base pour rattacher les références aux anomalies
2. **RAG-lite** — `knowledge_base.search_relevant(type_document, texte_anomalie)` classe les entrées par **type de document + termes + domaine** et renvoie les articles et règles de contrôle pertinents (sans service cloud, zéro hallucination)
3. **Vérification officielle** — `legal_source_service.py` relie chaque référence à Légifrance (lien de recherche ou vérification PISTE)
4. **Générateur de rapports** — Cite les sources juridiques dans les recommandations et les anomalies détectées
