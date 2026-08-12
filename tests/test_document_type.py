"""Tests de la détection du type de document (statuts vs modification).

Vérifie notamment qu'un document de statuts complets — même avec un en-tête
« MAJ STATUTS » — est classé comme « statuts » et non comme une simple
modification statutaire (sinon les règles de contrôle des statuts ne sont
jamais appliquées).
"""

from services.document_service import detect_document_type, _score_statuts_complets


def _statuts_texte_complet() -> str:
    return (
        "TRANSPORTS EXPRESS SARL MAJ STATUTS EN DATE DU 01 OCTOBRE 2024\n"
        "ARTICLE 1 - FORME\nLa societe est une SARL.\n"
        "La denomination de la SARL est TRANSPORTS EXPRESS.\n"
        "ARTICLE 2 - OBJET\nLa societe a pour objet le transport de marchandises.\n"
        "ARTICLE 3 - SIEGE SOCIAL\nLe siege social est fixe a ROUBAIX.\n"
        "ARTICLE 4 - DUREE DE LA SOCIETE\nLa duree de la societe est de 99 ans.\n"
        "ARTICLE 5 - CAPITAL SOCIAL\nLe capital social est fixe a 50 000 euros.\n"
        "ARTICLE 6 - PARTS SOCIALES\nIl est divise en 100 parts sociales.\n"
        "ARTICLE 7 - CESSION DE PARTS\nToute cession de parts est soumise a agrement.\n"
        "ARTICLE 8 - GERANCE\nLa societe est administree par un gerant.\n"
        "ARTICLE 9 - AFFECTATION DES RESULTATS\nLes resultats sont affectes chaque annee.\n"
        "ARTICLE 10 - DISSOLUTION\nLa dissolution est decidee par les associes.\n"
        "ARTICLE 11 - LIQUIDATION\nLa liquidation est regie par la loi.\n"
        "Assemblee generale extraordinaire du 01/10/2024 ayant decide "
        "l'augmentation du capital.\n"
    )


def test_maj_statuts_complets_detectes_comme_statuts():
    """Des statuts complets avec un en-tête « MAJ STATUTS » sont des statuts."""
    texte = _statuts_texte_complet()
    assert _score_statuts_complets(texte) >= 8
    assert detect_document_type(texte) == "statuts"


def test_annexe_modification_restee_modification_statutaire():
    """Une vraie décision de modification reste une modification statutaire."""
    texte = (
        "ASSEMBLEE GENERALE EXTRAORDINAIRE DU 01/10/2024\n"
        "Les associes ont decide l'augmentation du capital de 50 000 a 60 000 euros.\n"
        "Depot au greffe et publication legale.\n"
    )
    assert detect_document_type(texte) == "modification_statutaire"


def test_statuts_courts_detectes_comme_statuts():
    """Des statuts incomplets restent détectés comme statuts (repli société)."""
    texte = (
        "STATUTS DE LA SOCIETE TOP LEGAL CONSEIL (SARL)\n"
        "Article 1 - Forme juridique\nLa societe est une SARL.\n"
        "Article 2 - Capital social\nLe capital est fixe a 50 000 euros.\n"
        "Article 3 - Gerance\nLa societe est geree par un gerant.\n"
    )
    assert detect_document_type(texte) == "statuts"
