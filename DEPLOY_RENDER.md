# Déploiement du prototype sur Render

Ce guide décrit comment mettre le prototype TOP-JURIDIQUE en ligne sur Render
(interface Streamlit) pour le transmettre à l'encadrante.

## Prérequis

- Un compte GitHub (ou GitLab) pour héberger le code.
- Un compte Render (gratuit) : https://render.com.

## 1. Pousser le code sur GitHub

Depuis le dossier du projet (`top-juridique-copilote`) :

```powershell
git init
git add .
git commit -m "Prototype TOP-JURIDIQUE - Copilote IA Juridique"
git branch -M main
git remote add origin https://github.com/<TON_COMPTE>/top-juridique-copilote.git
git push -u origin main
```

> Le fichier `.gitignore` exclut déjà `.env` (les secrets ne partent jamais sur GitHub).
> Vérifier avec `git status` qu'aucun fichier sensible n'est suivi.

## 2. Créer l'application sur Render

1. Se connecter à https://dashboard.render.com.
2. « New » → « Blueprint » → sélectionner le dépôt GitHub.
3. Render détecte automatiquement `render.yaml` (service web + environnement).
4. « Apply Blueprint ».

Le fichier `render.yaml` configure :
- la commande de lancement : `streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT` ;
- les variables d'environnement à renseigner (voir ci-dessous).

## 3. Renseigner les variables d'environnement (secrets)

Sur Render, dans le service créé : « Environment » → « New Environment Variable ».
Ne pas utiliser le fichier `.env` (il n'est pas poussé).

Variables requises pour la vérification Légifrance (PISTE) :
- `PISTE_ENV` = `prod`
- `PISTE_CLIENT_ID` = <identifiant de l'application PISTE>
- `PISTE_CLIENT_SECRET` = <secret de l'application PISTE>
- `PISTE_API_KEY` = <clé API PISTE>
- `PISTE_API_SECRET` = <secret API PISTE>

Variables optionnelles (IA) :
- `GROQ_API_KEY` = <clé Groq> (sinon l'application fonctionne en local)
- `OPENROUTER_API_KEY` = <clé OpenRouter> (secours)

Sans aucune clé IA, l'application fonctionne à 100 % en local (aucun appel externe).

## 4. Accéder à l'application

- URL publique : https://<nom-du-service>.onrender.com (visible dans le tableau de bord Render).
- Tester avec les documents PDF (statuts + pacte d'associés).

## Limites connues sur Render

- **OCR** : l'OCR (Tesseract) n'est pas installé sur Render. Les PDF « natifs »
  sont lus normalement ; un PDF scanné est signalé comme « OCR indisponible »
  (statut `ocr` avec drapeau). Sur une machine locale avec Tesseract, l'OCR est complet.
- **Persistance** : les rapports ne sont pas sauvegardés sur disque
  (`SAVE_REPORTS_TO_DISK` désactivé par défaut) — les données restent en mémoire
  pour la session.
