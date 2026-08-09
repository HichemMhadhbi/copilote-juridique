"""
Point d'entrée CLI pour TOP-JURIDIQUE.

Exécute le pipeline complet d'analyse juridique :
ingestion → extraction → comparaison → règles → rapport.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Optional

import config_app  # noqa: F401  (charge les variables d'environnement)


def parse_args() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        prog="top-juridique",
        description="TOP-JURIDIQUE — Copilote IA Juridique",
        epilog="Analyse automatisée de documents juridiques.",
    )

    parser.add_argument(
        "--upload-dir",
        type=str,
        required=True,
        help="Chemin du dossier contenant les PDF à analyser.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Chemin du dossier de sortie pour les rapports (défaut : ./output).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["rapide", "complet", "avance"],
        default="complet",
        help="Mode d'analyse (défaut : complet).",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["groq", "google_ai", "openrouter"],
        default="groq",
        help="Fournisseur LLM (défaut : groq).",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "pdf", "json", "all"],
        default="all",
        help="Format de sortie du rapport (défaut : all).",
    )
    parser.add_argument(
        "--enable-rag",
        action="store_true",
        default=True,
        help="Activer la recherche RAG (défaut : activé).",
    )
    parser.add_argument(
        "--no-rag",
        action="store_true",
        help="Désactiver la recherche RAG.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Activer le mode validation interactive.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Afficher les logs détaillés.",
    )

    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> Optional[str]:
    """
    Exécute le pipeline complet d'analyse.

    Utilise la pile unifiée `services/` (extraction → analyse → rapport),
    identique a celle de l'interface Streamlit et de l'API.

    Args:
        args: Arguments parsés de la ligne de commande.

    Returns:
        Chemin du rapport généré, ou None en cas d'erreur.
    """
    from services.document_service import extract_text_from_pdf_with_status
    from services.analysis_service import analyze_documents, format_report_markdown
    from services.export_service import export_report_as_pdf
    from services import storage_service

    upload_dir = Path(args.upload_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Vérification du dossier d'entrée
    if not upload_dir.exists():
        print(f"❌ Erreur : Le dossier '{upload_dir}' n'existe pas.")
        return None

    pdf_files = sorted(upload_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ Aucun fichier PDF trouvé dans '{upload_dir}'.")
        return None

    print(f"📂 {len(pdf_files)} fichier(s) PDF trouvé(s) dans '{upload_dir}'.")
    print(f"🔧 Mode : {args.mode} | Fournisseur : {args.provider}")
    print("=" * 60)

    # ── Étape 1 : Ingestion + extraction ───────────────────────────────────
    print("\n📄 Étape 1/3 — Ingestion et extraction des documents...")

    documents: dict[str, str] = {}
    statuses: dict[str, str] = {}
    documents_illisibles: list[str] = []

    for pdf_path in pdf_files:
        print(f"  → Traitement de {pdf_path.name}...")
        try:
            text, status = extract_text_from_pdf_with_status(
                pdf_path.read_bytes(), pdf_path.name
            )
            if not text or len(text.strip()) < 50 or text.startswith("[OCR indisponible"):
                documents_illisibles.append(pdf_path.name)
                print(f"    ⚠️ Document illisible ou trop court (lecture : {status}).")
                continue
            documents[pdf_path.name] = text
            statuses[pdf_path.name] = status
            print(f"    ✅ Texte extrait (lecture : {status}).")
        except Exception as exc:
            documents_illisibles.append(pdf_path.name)
            print(f"    ❌ Erreur : {exc}")

    if not documents:
        print("❌ Aucun document exploitable. Vérifiez les PDF du dossier.")
        return None

    # ── Étape 2 : Analyse juridique unifiée ────────────────────────────────
    print(f"\n⚖️ Étape 2/3 — Analyse juridique de {len(documents)} document(s)...")
    report = analyze_documents(documents, statuses)

    anomalies = len(report.get("anomalies_juridiques", []))
    incoherences = len(report.get("incoherences", []))
    print(f"  ✅ {anomalies} anomalie(s), {incoherences} incohérence(s) détectée(s).")

    # ── Étape 3 : Génération du rapport ────────────────────────────────────
    print("\n📊 Étape 3/3 — Génération du rapport...")

    try:
        saved_path = storage_service.save_report(report)
        if saved_path:
            print(f"  💾 Rapport sauvegardé : {saved_path}")
        else:
            print("  💾 Persistance désactivée (SAVE_REPORTS_TO_DISK=0) : rapport non sauvegardé sur disque.")
    except Exception as exc:
        print(f"  ⚠️ Sauvegarde du rapport impossible : {exc}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    export_formats = args.format if args.format != "all" else ["markdown", "pdf", "json"]
    files_written = []

    if "markdown" in export_formats:
        md_path = output_dir / f"rapport_{timestamp}.md"
        md_path.write_text(format_report_markdown(report), encoding="utf-8")
        files_written.append(str(md_path))
        print(f"  📝 Markdown : {md_path}")

    if "pdf" in export_formats:
        try:
            pdf_path = output_dir / f"rapport_{timestamp}.pdf"
            pdf_path.write_bytes(export_report_as_pdf(report))
            files_written.append(str(pdf_path))
            print(f"  📄 PDF : {pdf_path}")
        except Exception as exc:
            print(f"  ⚠️ PDF non généré : {exc}")

    if "json" in export_formats:
        json_path = output_dir / f"rapport_{timestamp}.json"
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        files_written.append(str(json_path))
        print(f"  📋 JSON : {json_path}")

    # Résumé final
    print("\n" + "=" * 60)
    print("✅ Analyse terminée avec succès !")
    print(f"  📊 Rapport ID : {report.get('rapport_id', 'N/A')}")
    print(f"  🎯 Niveau de risque : {report.get('niveau_risque_global', 'N/A').upper()}")
    print(f"  📁 Rapports générés : {len(files_written)}")
    for fw in files_written:
        print(f"     → {fw}")

    return files_written[0] if files_written else None


def main() -> None:
    """Point d'entrée principal du CLI."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = parse_args()

    # Désactivation du RAG si demandé
    if args.no_rag:
        os.environ["DISABLE_RAG"] = "1"

    print("╔══════════════════════════════════════════════════════════╗")
    print("║     TOP-JURIDIQUE — Copilote IA Juridique v1.0         ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    result = run_pipeline(args)

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
