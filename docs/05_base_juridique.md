# 05 — Base de Connaissances Juridique

## Vue d'ensemble

La base de connaissances juridique de TOP-JURIDIQUE fournit le référentiel normatif
utilisé par le moteur de règles et le pipeline RAG pour contextualiser les analyses.

## Schéma de la base

```
legal_kb/
├── data/
│   ├── codes/                  # Textes de loi (Code civil, Code de commerce...)
│   ├── jurisprudence/          # Arrêts et décisions de justice
│   ├── doctrines/              # Articles de doctrine juridique
│   ├── conventions_collectives/# Conventions collectives par branche
│   └── indexes.json            # Index de recherche par mots-clés
```

### Structure d'une entrée

Chaque entrée de la base suit le schéma JSON suivant :

```json
{
  "id": "CIV-1843-4",
  "source": "code_civil",
  "titre": "Article 1843-4 du Code civil",
  "texte": "En cas de cession à titre onéreux de parts sociales souscrites...",
  "reference": "Legifrance",
  "date_modification": "2024-01-15",
  "tags": ["cession", "parts_sociales", "agrément", "société"],
  "applicable_a": ["pacte_associes", "statuts", "contrat_commercial"],
  "niveau_confiance": 0.95
}
```

### Champs obligatoires

| Champ | Type | Description |
|-------|------|-------------|
| `id` | string | Identifiant unique de l'entrée |
| `source` | enum | Origine (code_civil, jurisprudence, doctrine...) |
| `titre` | string | Titre de la référence |
| `texte` | string | Texte intégral ou extrait |
| `reference` | string | Source officielle (Legifrance, PISTE...) |
| `tags` | list[str] | Mots-clés pour la recherche |
| `applicable_a` | list[str] | Types de documents concernés |

## Sources de données

### Sources actuelles (fictives pour MVP)

- **Légifrance** — Base officielle de la legislation française (https://www.legifrance.gouv.fr)
  - Pour le MVP, des extraits fictifs mais réalistes sont utilisés
  - Phase 2 : API Légifrance pour la mise à jour automatique

- **PISTE** — Plateforme Interbancaire des Titres Électroniques
  - Données de référence pour les structures de capital
  - Phase 2 : intégration API

- **Doctrines juridiques** — Extraits de traités et articles de doctrine
  - Sources : Dalloz, Recueil Sirey, JCP
  - Phase 2 : connexion aux bases payantes

### Sources futures (Phase 2+)

- API Légifrance officielle
- Base de jurisprudence Cour de cassation
- Conventions collectives IDCC
- Guides AMF / ACPR

## Méthode de mise à jour

### Mise à jour manuelle (Phase 1)

```bash
# Import d'un fichier JSON dans la base
python -m legal_kb.import --file=new_entries.json --source=doctrine

# Vérification de la cohérence
python -m legal_kb.validate --check=all
```

### Mise à jour automatique (Phase 2 — prévu)

```python
from legal_kb.updater import KnowledgeBaseUpdater

updater = KnowledgeBaseUpdater()
updater.fetch_from_legifrance(dates=["2024-01-01", "2024-12-31"])
updater.validate_and_merge()
```

## Exemples d'entrées

### Article 1843-4 du Code civil

```json
{
  "id": "CIV-1843-4",
  "source": "code_civil",
  "titre": "Article 1843-4 — Cession de parts sociales",
  "texte": "En cas de cession à titre onéreux de parts sociales souscrites par des associés n'ayant pas la qualité de commerçants, la nullité de la cession pour défaut de consentement d'un ou de plusieurs associés ne peut être opposée par ceux-ci aux tiers agissant en justice.",
  "reference": "Legifrance — Législation en vigueur",
  "date_modification": "2024-01-15",
  "tags": ["cession", "parts_sociales", "consentement", "nullité"],
  "applicable_a": ["pacte_associes", "statuts"],
  "niveau_confiance": 0.95
}
```

### Article L. 231-1 du Code de commerce

```json
{
  "id": "COM-L231-1",
  "source": "code_commerce",
  "titre": "Article L. 231-1 — Clause de sortie conjointe",
  "texte": "Toute société peut prévoir dans ses statuts des clauses de sortie conjointe (tag-along) et de sortie forcée (drag-along).",
  "reference": "Legifrance — Code de commerce",
  "date_modification": "2023-06-01",
  "tags": ["tag-along", "drag-along", "cession", "protection"],
  "applicable_a": ["pacte_associes"],
  "niveau_confiance": 0.90
}
```

## Utilisation par le pipeline

1. **Moteur de règles** — Consulte la base pour vérifier la conformité
   des clauses par rapport aux textes de loi
2. **Pipeline RAG** — Utilise les embeddings FAISS pour retrouver les
   références pertinentes lors de l'analyse contextuelle
3. **Générateur de rapports** — Cite les sources juridiques dans
   les recommandations et les anomalies détectées
