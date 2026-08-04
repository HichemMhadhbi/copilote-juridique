"""Configuration pytest commune aux tests.

Les tests unitaires ne doivent pas dépendre du réseau ni des identifiants
PISTE : la vérification live des références Légifrance est désactivée ici.
"""

import os

os.environ.setdefault("LEGIFRANCE_VERIFY_LIVE", "0")
