# ============================================================
# MENU DU RESTAURANT LE TALIER
# Spécialités Africaines & Européennes
# ============================================================

RESTAURANT_INFO = {
    "nom": "Le Talier",
    "specialites": "Spécialités africaines et européennes",
    "services": ["Sur place", "À emporter", "Service traiteur"],
    "horaires": "Lundi au Samedi, 11h à 18h",
    "jours_ouverture": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"],
}

ACCOMPAGNEMENTS = [
    "Igname pilée", "Igname frite", "Alloco", "Akassa", "Télibo",
    "Agbéli", "Piron", "Amiwo", "Haricots verts", "Couscous",
    "Riz", "Pommes sautées", "Pommes frites"
]

MENU = {
    "sauces": {
        "titre": "🍲 Sauces africaines",
        "items": [
            {"nom": "Sauce Feuille",       "prix": 3000,  "dispo": "Lundi uniquement",   "id": "S1"},
            {"nom": "Sauce Fetri Gboman",  "prix": 3000,  "dispo": "Mardi uniquement",   "id": "S2"},
            {"nom": "Sauce Poissons frais","prix": 3500,  "dispo": "Mercredi uniquement","id": "S3"},
            {"nom": "Sauce Assrokouin",    "prix": 3000,  "dispo": "Jeudi uniquement",   "id": "S4"},
            {"nom": "Sauce Arachide",      "prix": 2500,  "dispo": "Tous les jours",     "id": "S5"},
            {"nom": "Sauce Graine",        "prix": 2500,  "dispo": "Tous les jours",     "id": "S6"},
            {"nom": "Sauce Tchayo",        "prix": 2500,  "dispo": "Tous les jours",     "id": "S7"},
        ]
    },
    "viandes_poissons": {
        "titre": "🥩 Viandes & Poissons",
        "items": [
            {"nom": "Sole",                "prix": "6500 - 13000", "dispo": "Tous les jours", "id": "V1"},
            {"nom": "Pintade",             "prix": 4500,           "dispo": "Tous les jours", "id": "V2"},
            {"nom": "Lapin",               "prix": 4500,           "dispo": "Tous les jours", "id": "V3"},
            {"nom": "Langue de bœuf",      "prix": 4500,           "dispo": "Tous les jours", "id": "V4"},
            {"nom": "Poulet braisé",       "prix": "3500 - 6000",  "dispo": "Tous les jours", "id": "V5"},
            {"nom": "Bar / Carpe / Daurade","prix": "3500 - 7000", "dispo": "Tous les jours", "id": "V6"},
        ]
    }
}

def get_menu_text():
    """Retourne le menu complet formaté pour WhatsApp."""
    lines = ["🍽️ *MENU DU RESTAURANT LE TALIER*\n"]
    for categorie, data in MENU.items():
        lines.append(f"\n{data['titre']}")
        lines.append("─────────────────")
        for item in data["items"]:
            prix = item["prix"]
            if isinstance(prix, int):
                prix_str = f"{prix:,} FCFA".replace(",", " ")
            else:
                prix_str = f"{prix} FCFA"
            lines.append(f"*{item['id']}* {item['nom']} — {prix_str}")
            if item["dispo"] != "Tous les jours":
                lines.append(f"    _(Disponible: {item['dispo']})_")

    lines.append(f"\n🥗 *Accompagnements disponibles:*")
    lines.append(", ".join(ACCOMPAGNEMENTS))
    lines.append("\n_(Les sauces sont servies avec l'accompagnement de votre choix)_")
    return "\n".join(lines)


def get_item_by_id(item_id):
    """Retourne un item du menu par son ID."""
    for categorie, data in MENU.items():
        for item in data["items"]:
            if item["id"].upper() == item_id.upper():
                return item
    return None


def get_all_items():
    """Retourne tous les items du menu."""
    items = []
    for categorie, data in MENU.items():
        items.extend(data["items"])
    return items
