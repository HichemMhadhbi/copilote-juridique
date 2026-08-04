# 06 — Intégration TOP-JURIDIQUE

## Architecture globale

```
┌─────────────────────────────────────────────────────────────────┐
│                       TOP-JURIDIQUE                             │
│                                                                 │
│  ┌──────────┐   ┌────────────┐   ┌────────────┐   ┌──────────┐│
│  │ Ingestion │──▶│ Extraction │──▶│ Comparaison│──▶│  Règles  ││
│  │  (PDF/OCR)│   │ (Entités)  │   │(Inter-doc) │   │(Juridique)││
│  └──────────┘   └────────────┘   └────────────┘   └──────────┘│
│       │               │                │                │      │
│       └───────────────┴────────────────┴────────────────┘      │
│                              │                                 │
│                    ┌─────────▼─────────┐                       │
│                    │   Report Builder  │                       │
│                    └─────────┬─────────┘                       │
│                              │                                 │
│              ┌───────────────┼───────────────┐                 │
│              │               │               │                 │
│        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐           │
│        │  Markdown  │  │    PDF    │  │    JSON   │           │
│        └───────────┘  └───────────┘  └───────────┘           │
│                              │                                 │
│                    ┌─────────▼─────────┐                       │
│                    │  Validation Humaine│                       │
│                    └───────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## Endpoints API

### POST `/analyze`

**Description :** Upload et analyse de documents juridiques.

**Requête :**
```
Content-Type: multipart/form-data

files: [fichier1.pdf, fichier2.pdf]
mode: "complet" | "rapide" | "avance"
provider: "groq" | "google_ai" | "openrouter"
enable_rag: true | false
```

**Réponse :**
```json
{
  "report_id": "uuid-xxx",
  "statut": "termine",
  "message": "Analyse de 3 documents terminée.",
  "date_debut": "2026-07-16T14:30:00",
  "date_fin": "2026-07-16T14:32:15",
  "nombre_documents": 3,
  "niveau_risque": "eleve"
}
```

### GET `/report/{report_id}`

**Description :** Récupération d'un rapport d'analyse.

**Réponse :**
```json
{
  "rapport_id": "uuid-xxx",
  "date_analyse": "2026-07-16T14:32:15",
  "documents_analyses": [...],
  "informations_principales": {...},
  "incoherences": [...],
  "anomalies_juridiques": [...],
  "clauses_a_risque": [...],
  "clauses_manquantes": [...],
  "ameliorations_proposees": [...],
  "niveau_risque_global": "eleve",
  "recommandations_finales": [...],
  "points_validation_humaine": [...]
}
```

### POST `/validate/{report_id}/{finding_id}`

**Description :** Validation d'un finding spécifique par un juriste.

**Requête :**
```json
{
  "action": "approuver" | "rejeter" | "modifier",
  "comment": "Commentaire du juriste",
  "reason": "Motif (si rejet)",
  "new_content": {}
}
```

**Réponse :**
```json
{
  "finding_id": "anomalie-1",
  "statut": "approuve",
  "date_validation": "2026-07-16T15:00:00"
}
```

### GET `/health`

**Description :** Vérification de l'état de santé de l'API.

**Réponse :**
```json
{
  "statut": "operational",
  "version": "1.0.0",
  "uptime": "2h 30min",
  "fournisseurs_disponibles": ["groq"]
}
```

## Format d'échange de données

### Document en entrée

```json
{
  "nom": "Pacte_d_associes_SAS_2024.pdf",
  "type": "pacte_associes",
  "statut": "analyse",
  "texte_extrait": "..."
}
```

### Rapport en sortie

Le rapport suit le schéma standardisé défini par `ReportBuilder`.
Tous les champs sont optionnels mais recommandés.

## Flux d'authentification

### Phase 1 — MVP (sans authentification)

L'API est ouverte pour les tests en développement.
Aucune authentification n'est requise.

### Phase 2 — Authentification JWT

```python
# Génération du token
from api.auth import create_token

token = create_token(user_id="juriste-001", role="analyst")

# Utilisation dans les headers
headers = {"Authorization": f"Bearer {token}"}
response = requests.post("http://localhost:8000/analyze", headers=headers, files=files)
```

### Phase 3 — OAuth2 / SSO

Intégration avec un fournisseur d'identité existant (Azure AD, Google Workspace).

## Stockage des résultats

### Phase 1 — Fichiers JSON

Les rapports sont sauvegardés en JSON dans le dossier `output/`.
Structure :
```
output/
├── rapport_20260716_143000.json
├── rapport_20260716_143000.md
├── rapport_20260716_143000.pdf
└── ...
```

### Phase 2 — Base de données

Migration vers PostgreSQL ou MongoDB pour :
- Historique des analyses
- Suivi des validations
- Statistiques d'utilisation

## Workflow de validation

```
1. L'analyse automatique génère le rapport
        │
        ▼
2. Le rapport est stocké avec statut "en_attente"
        │
        ▼
3. Le juriste consulte le rapport via l'API
        │
        ▼
4. Pour chaque finding, le juriste valide :
   ├── Approuver → le finding est marqué "approuve"
   ├── Rejeter → le finding est marqué "rejete" (motif requis)
   └── Modifier → le finding est mis à jour avec le nouveau contenu
        │
        ▼
5. Le rapport final avec validations est exporté
```

## Intégration avec d'autres outils

### Webhook de notification

```json
// POST /webhooks (Phase 3)
{
  "url": "https://cabinet-avocat.fr/hook/top-juridique",
  "events": ["rapport.genere", "anomalie.detectee"],
  "secret": "clé_secrète"
}
```

### Export vers des systèmes tiers

- **SharePoint** : Export automatique des rapports PDF
- **Salesforce** : Synchronisation des comptes clients
- **Microsoft Teams** : Notification des anomalies critiques
