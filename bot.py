# ============================================================
# BOT WHATSAPP — Restaurant Le Talier
# ============================================================
# Technologie : Flask + Twilio WhatsApp API
# Fonctions   : Infos restaurant, réservation, commande,
#               récapitulatif → Excel + Google Calendar
# ============================================================

import os
import re
import json
from datetime import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from menu_data import (
    RESTAURANT_INFO, MENU, ACCOMPAGNEMENTS,
    get_menu_text, get_item_by_id, get_all_items
)
from excel_tracker import add_reservation
from google_calendar import create_reservation_event

app = Flask(__name__)

# ── Stockage des sessions en mémoire (remplacer par Redis en prod) ──
sessions = {}

# ── États de la conversation ──
STATE_ACCUEIL          = "accueil"
STATE_MENU_PRINCIPAL   = "menu_principal"
STATE_INFO             = "info"
STATE_RESERVATION_DATE = "resa_date"
STATE_RESERVATION_HEURE= "resa_heure"
STATE_RESERVATION_NOM  = "resa_nom"
STATE_RESERVATION_NB   = "resa_nb"
STATE_SERVICE_TYPE     = "service_type"
STATE_COMMANDE_MENU    = "commande_menu"
STATE_COMMANDE_ITEM    = "commande_item"
STATE_COMMANDE_ACCOMP  = "commande_accomp"
STATE_COMMANDE_QTE     = "commande_qte"
STATE_COMMANDE_SUITE   = "commande_suite"
STATE_CONFIRMATION     = "confirmation"
STATE_TERMINE          = "termine"
STATE_TRAITEUR	       = "service-traiteur"

def get_session(phone: str) -> dict:
    """Récupère ou initialise la session d'un utilisateur."""
    if phone not in sessions:
        sessions[phone] = {
            "state": STATE_ACCUEIL,
            "nom_client": "",
            "telephone": phone,
            "date": "",
            "heure": "",
            "nb_personnes": 1,
            "type_service": "sur_place",
            "commande": [],
            "item_en_cours": None,
            "total": 0,
        }
    return sessions[phone]


def reset_session(phone: str):
    """Réinitialise la session (nouvelle conversation)."""
    sessions[phone] = {
        "state": STATE_ACCUEIL,
        "nom_client": "",
        "telephone": phone,
        "date": "",
        "heure": "",
        "nb_personnes": 1,
        "type_service": "sur_place",
        "commande": [],
        "item_en_cours": None,
        "total": 0,
    }


def calcul_total(commande: list) -> int:
    """Calcule le total de la commande."""
    total = 0
    for item in commande:
        prix = item.get("prix", 0)
        qte = item.get("quantite", 1)
        if isinstance(prix, int):
            total += prix * qte
        elif isinstance(prix, str) and "-" in prix:
            # Fourchette de prix : on prend le min
            try:
                prix_min = int(prix.split("-")[0].strip().replace(" ", ""))
                total += prix_min * qte
            except:
                pass
    return total


def format_recapitulatif(session: dict) -> str:
    """Génère le message récapitulatif final."""
    lines = [
        "✅ *RÉCAPITULATIF DE VOTRE RÉSERVATION*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🏠 *Restaurant Le Talier*",
        f"👤 *Client:* {session['nom_client']}",
        f"📱 *Tél:* {session['telephone']}",
        f"📅 *Date:* {session['date']}",
        f"🕐 *Heure:* {session['heure']}",
        f"👥 *Personnes:* {session['nb_personnes']}",
    ]

    type_labels = {
        "sur_place": "🍽️ Sur place",
        "emporter": "🛍️ À emporter",
        "traiteur": "🎉 Service traiteur"
    }
    lines.append(f"🛎️ *Service:* {type_labels.get(session['type_service'], 'Sur place')}")

    if session["commande"]:
        lines.append("\n📋 *Votre commande:*")
        for item in session["commande"]:
            prix = item["prix"]
            if isinstance(prix, int):
                prix_str = f"{prix:,} FCFA".replace(",", " ")
            else:
                prix_str = f"{prix} FCFA"
            line = f"  • {item['quantite']}x {item['nom']} — {prix_str}"
            if item.get("accompagnement"):
                line += f"\n    ↳ Accompagnement: {item['accompagnement']}"
            lines.append(line)

        total = calcul_total(session["commande"])
        lines.append(f"\n💰 *Total estimé: {total:,} FCFA*".replace(",", " "))

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📌 _Réservation enregistrée dans notre système._")
    lines.append("Nous vous attendons au *Restaurant Le Talier* ! 🙏")
    return "\n".join(lines)


def process_message(phone: str, message: str) -> str:
    """Traite le message entrant et retourne la réponse du bot."""
    session = get_session(phone)
    msg = message.strip().lower()
    state = session["state"]

    # ── Commandes universelles ──
    if msg in ["menu", "aide", "help", "0", "recommencer", "restart"]:
        reset_session(phone)
        session = get_session(phone)

    if msg in ["annuler", "cancel", "quitter"]:
        reset_session(phone)
        return (
            "❌ Votre demande a été annulée.\n\n"
            "Tapez *MENU* pour recommencer ou *1* pour voir nos informations."
        )

    # ══════════════════════════════════════════════
    # ÉTAT : ACCUEIL
    # ══════════════════════════════════════════════
    if state == STATE_ACCUEIL or msg in ["menu", "bonjour", "bonsoir", "salut", "hello", "0", "cc"]:
        session["state"] = STATE_MENU_PRINCIPAL
        return (
            f"👋 Bienvenue au *Restaurant Le Talier* !\n"
            f"_Spécialités africaines & européennes_\n\n"
            f"🕐 Ouvert *Lundi — Samedi | 11h — 18h*\n\n"
            f"Que souhaitez-vous faire ?\n\n"
            f"*1* — 📋 Voir le menu\n"
            f"*2* — 📅 Faire une réservation\n"
            f"*3* — 🛍️ Commander (à emporter)\n"
            f"*4* — ℹ️ Informations & contact\n"
	    f"*5* -    Solliciter notre service traiteur\n\n"
            f"_Tapez le numéro de votre choix_"
        )

    # ══════════════════════════════════════════════
    # ÉTAT : MENU PRINCIPAL
    # ══════════════════════════════════════════════
    if state == STATE_MENU_PRINCIPAL:
        if msg == "1":
            session["state"] = STATE_MENU_PRINCIPAL
            return (
                get_menu_text() +
                "\n\n_Tapez *2* pour réserver | *3* pour commander | *0* menu principal_"
            )

        elif msg == "2":
            session["state"] = STATE_RESERVATION_DATE
            session["type_service"] = "sur_place"
            return (
                "📅 *RÉSERVATION SUR PLACE*\n\n"
                "Quelle est la date souhaitée ?\n"
                "_(Format: JJ/MM/AAAA — ex: 15/04/2026)_"
            )

        elif msg == "3":
            session["state"] = STATE_RESERVATION_DATE
            session["type_service"] = "emporter"
            return (
                "🛍️ *COMMANDE À EMPORTER*\n\n"
                "Pour quel jour souhaitez-vous récupérer votre commande ?\n"
                "_(Format: JJ/MM/AAAA — ex: 15/04/2026)_"
            )

        elif msg == "4":
            session["state"] = STATE_MENU_PRINCIPAL
            return (
                "ℹ️ *RESTAURANT LE TALIER*\n\n"
                "🍽️ Spécialités africaines & européennes\n"
                "🛎️ Sur place | À emporter | Traiteur\n"
                "🕐 Lundi — Samedi : 11h à 18h\n\n"
		"   Nous sommes situés à Guinkomey Vons Chez Alex, à côté de l'Hotel Nicolif\n"
                "📞 Pour joindre le restaurant, répondez directement sur ce numéro.\n\n"
                "_Tapez *0* pour revenir au menu principal_"
            )
	elif msg == "5":
            session["state"] = STATE_TRAITEUR
            return (
                "📞 Pour joindre le restaurant, appelez directement sur ce numéro.\n\n"
                "_Tapez *0* pour revenir au menu principal_"
        else:
            return (
                "❓ Je n'ai pas compris. Tapez :\n"
                "*1* — Menu | *2* — Réserver | *3* — Commander | *4* — Infos | *5* - Service traiteur\n"
                "ou *0* pour recommencer."
            )

    # ══════════════════════════════════════════════
    # ÉTAT : RÉSERVATION — DATE
    # ══════════════════════════════════════════════
    if state == STATE_RESERVATION_DATE:
        date_pattern = r"^\d{1,2}/\d{1,2}/\d{4}$"
        if re.match(date_pattern, message.strip()):
            session["date"] = message.strip()
            session["state"] = STATE_RESERVATION_HEURE
            return (
                f"✅ Date : *{message.strip()}*\n\n"
                "🕐 À quelle heure ?\n"
                "_(Format: HH:MM — ex: 12:30)\n"
                "Nos horaires : 11h00 à 18h00_"
            )
        else:
            return (
                "❌ Format invalide. Veuillez entrer la date au format *JJ/MM/AAAA*\n"
                "Exemple : *15/04/2026*"
            )

    # ══════════════════════════════════════════════
    # ÉTAT : RÉSERVATION — HEURE
    # ══════════════════════════════════════════════
    if state == STATE_RESERVATION_HEURE:
        heure_pattern = r"^\d{1,2}[h:]\d{2}$|^\d{1,2}h$"
        heure_input = message.strip().replace("h", ":").replace("::", ":")
        if ":" not in heure_input:
            heure_input += ":00"
        try:
            h, m = heure_input.split(":")
            h, m = int(h), int(m)
            if 11 <= h <= 17 or (h == 17 and m == 0):
                session["heure"] = f"{h:02d}:{m:02d}"
                session["state"] = STATE_RESERVATION_NOM
                return (
                    f"✅ Heure : *{h:02d}:{m:02d}*\n\n"
                    "👤 Quel est votre nom complet ?"
                )
            else:
                return (
                    "⚠️ Nous sommes ouverts de *11h00 à 18h00*.\n"
                    "Veuillez choisir une heure dans nos horaires."
                )
        except:
            return (
                "❌ Format invalide. Entrez l'heure au format *HH:MM*\n"
                "Exemple : *12:30*"
            )

    # ══════════════════════════════════════════════
    # ÉTAT : RÉSERVATION — NOM
    # ══════════════════════════════════════════════
    if state == STATE_RESERVATION_NOM:
        if len(message.strip()) >= 2:
            session["nom_client"] = message.strip().title()
            session["state"] = STATE_RESERVATION_NB
            return (
                f"✅ Nom : *{session['nom_client']}*\n\n"
                "👥 Pour combien de personnes ?\n"
                "_(Tapez un chiffre : ex. 2)_"
            )
        else:
            return "❌ Veuillez entrer votre nom complet."

    # ══════════════════════════════════════════════
    # ÉTAT : RÉSERVATION — NB PERSONNES
    # ══════════════════════════════════════════════
    if state == STATE_RESERVATION_NB:
        try:
            nb = int(message.strip())
            if 1 <= nb <= 50:
                session["nb_personnes"] = nb
                session["state"] = STATE_COMMANDE_MENU
                return (
                    f"✅ *{nb} personne(s)*\n\n"
                    "🍽️ Souhaitez-vous pré-commander maintenant ?\n\n"
                    "*1* — Oui, je veux commander\n"
                    "*2* — Non, je commanderai sur place"
                )
            else:
                return "❌ Nombre invalide. Entrez entre 1 et 50 personnes."
        except:
            return "❌ Veuillez entrer un nombre. Exemple : *4*"

    # ══════════════════════════════════════════════
    # ÉTAT : COMMANDE — PROPOSITION DU MENU
    # ══════════════════════════════════════════════
    if state == STATE_COMMANDE_MENU:
        if msg == "1":
            session["state"] = STATE_COMMANDE_ITEM
            return (
                get_menu_text() +
                "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📝 *Tapez l'ID du plat choisi*\n"
                "_(ex: S1, V3, etc.)_\n"
                "ou *0* pour revenir au menu"
            )
        elif msg == "2":
            session["state"] = STATE_CONFIRMATION
            recap = format_recapitulatif(session)
            return (
                recap +
                "\n\nConfirmez-vous cette réservation ?\n"
                "*OUI* — Confirmer | *NON* — Annuler"
            )
        else:
            return (
                "Tapez *1* pour commander maintenant\n"
                "ou *2* pour commander sur place."
            )

    # ══════════════════════════════════════════════
    # ÉTAT : COMMANDE — CHOIX DU PLAT (ID)
    # ══════════════════════════════════════════════
    if state == STATE_COMMANDE_ITEM:
        if msg == "fin" or msg == "terminer":
            session["state"] = STATE_CONFIRMATION
            recap = format_recapitulatif(session)
            return (
                recap +
                "\n\nConfirmez-vous cette réservation ?\n"
                "*OUI* — Confirmer | *NON* — Annuler"
            )

        item_id = message.strip().upper()
        item = get_item_by_id(item_id)
        if item:
            session["item_en_cours"] = dict(item)
            # Les sauces ont des accompagnements
            if item_id.startswith("S"):
                session["state"] = STATE_COMMANDE_ACCOMP
                accomp_list = "\n".join(
                    [f"*{i+1}* — {a}" for i, a in enumerate(ACCOMPAGNEMENTS)]
                )
                return (
                    f"✅ *{item['nom']}* sélectionné(e)\n\n"
                    f"🥗 Choisissez votre accompagnement :\n\n"
                    f"{accomp_list}"
                )
            else:
                session["state"] = STATE_COMMANDE_QTE
                prix = item["prix"]
                prix_str = f"{prix:,} FCFA".replace(",", " ") if isinstance(prix, int) else f"{prix} FCFA"
                return (
                    f"✅ *{item['nom']}* — {prix_str}\n\n"
                    "Quelle quantité souhaitez-vous ?\n"
                    "_(Tapez un chiffre : ex. 1)_"
                )
        else:
            return (
                "❌ ID non reconnu. Consultez le menu et tapez un ID valide.\n"
                "_(ex: S1, S5, V2, etc.)_\n"
                "Tapez *1* pour revoir le menu | *FIN* pour terminer la commande"
            )

    # ══════════════════════════════════════════════
    # ÉTAT : COMMANDE — ACCOMPAGNEMENT (pour sauces)
    # ══════════════════════════════════════════════
    if state == STATE_COMMANDE_ACCOMP:
        try:
            choix = int(message.strip()) - 1
            if 0 <= choix < len(ACCOMPAGNEMENTS):
                session["item_en_cours"]["accompagnement"] = ACCOMPAGNEMENTS[choix]
                session["state"] = STATE_COMMANDE_QTE
                return (
                    f"✅ Accompagnement : *{ACCOMPAGNEMENTS[choix]}*\n\n"
                    "Quelle quantité ?\n_(Tapez un chiffre : ex. 1)_"
                )
            else:
                return f"❌ Tapez un numéro entre 1 et {len(ACCOMPAGNEMENTS)}."
        except:
            return f"❌ Tapez un numéro. Ex: *3*"

    # ══════════════════════════════════════════════
    # ÉTAT : COMMANDE — QUANTITÉ
    # ══════════════════════════════════════════════
    if state == STATE_COMMANDE_QTE:
        try:
            qte = int(message.strip())
            if 1 <= qte <= 20:
                item = session["item_en_cours"]
                item["quantite"] = qte
                session["commande"].append(item)
                session["total"] = calcul_total(session["commande"])
                session["item_en_cours"] = None
                session["state"] = STATE_COMMANDE_SUITE

                prix = item["prix"]
                prix_str = f"{prix:,} FCFA".replace(",", " ") if isinstance(prix, int) else f"{prix} FCFA"
                total_str = f"{session['total']:,} FCFA".replace(",", " ")
                nb_items = len(session["commande"])

                return (
                    f"✅ *{qte}x {item['nom']}* ajouté(s) !\n"
                    f"📦 *{nb_items} article(s)* dans votre commande\n"
                    f"💰 Total actuel : *{total_str}*\n\n"
                    "Que souhaitez-vous faire ?\n\n"
                    "*1* — Ajouter un autre plat\n"
                    "*2* — Terminer et confirmer\n"
                    "*0* — Revenir au menu principal"
                )
            else:
                return "❌ Quantité entre 1 et 20 svp."
        except:
            return "❌ Entrez un nombre. Ex: *2*"

    # ══════════════════════════════════════════════
    # ÉTAT : COMMANDE — SUITE (autre plat ou fin)
    # ══════════════════════════════════════════════
    if state == STATE_COMMANDE_SUITE:
        if msg == "1":
            session["state"] = STATE_COMMANDE_ITEM
            return (
                get_menu_text() +
                "\n\n📝 Tapez l'ID du prochain plat :"
            )
        elif msg == "2":
            session["state"] = STATE_CONFIRMATION
            recap = format_recapitulatif(session)
            return (
                recap +
                "\n\nConfirmez-vous cette réservation ?\n"
                "*OUI* — Confirmer | *NON* — Annuler"
            )
        else:
            return "Tapez *1* pour ajouter un plat ou *2* pour terminer."

    # ══════════════════════════════════════════════
    # ÉTAT : CONFIRMATION FINALE
    # ══════════════════════════════════════════════
    if state == STATE_CONFIRMATION:
        if msg in ["oui", "yes", "o", "confirmer", "ok", "confirme"]:
            session["total"] = calcul_total(session["commande"])

            # 1. Sauvegarder dans Excel
            try:
                resa_num = add_reservation(session)
                excel_status = f"✅ Enregistré (N° {resa_num})"
            except Exception as e:
                print(f"[Excel] Erreur: {e}")
                excel_status = "⚠️ Erreur enregistrement Excel"
                resa_num = "N/A"

            # 2. Créer l'événement Google Calendar
            try:
                cal_link = create_reservation_event(session)
                if cal_link:
                    session["calendar_link"] = cal_link
                    cal_status = "✅ Ajouté à Google Calendar"
                else:
                    cal_status = "⚠️ Calendar non configuré"
            except Exception as e:
                print(f"[Calendar] Erreur: {e}")
                cal_status = "⚠️ Erreur Google Calendar"

            session["state"] = STATE_TERMINE

            total_str = f"{session['total']:,} FCFA".replace(",", " ")

            return (
                f"🎉 *RÉSERVATION CONFIRMÉE !*\n\n"
                f"📋 N° de réservation : *#{resa_num}*\n"
                f"👤 {session['nom_client']}\n"
                f"📅 {session['date']} à {session['heure']}\n"
                f"👥 {session['nb_personnes']} personne(s)\n"
                f"💰 Total estimé : *{total_str}*\n\n"
                f"📊 {excel_status}\n"
                f"📅 {cal_status}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Merci pour votre confiance !\n"
                f"*Le Talier* vous attend 🙏\n\n"
                f"_Tapez *0* pour une nouvelle réservation_"
            )

        elif msg in ["non", "no", "n", "annuler"]:
            reset_session(phone)
            return (
                "❌ Réservation annulée.\n\n"
                "Tapez *0* pour recommencer."
            )
        else:
            return "Tapez *OUI* pour confirmer ou *NON* pour annuler."

    # ══════════════════════════════════════════════
    # ÉTAT : TERMINÉ
    # ══════════════════════════════════════════════
    if state == STATE_TERMINE:
        reset_session(phone)
        session = get_session(phone)
        session["state"] = STATE_MENU_PRINCIPAL
        return (
            f"👋 Bienvenue au *Restaurant Le Talier* !\n\n"
            f"Que souhaitez-vous faire ?\n\n"
            f"*1* — 📋 Voir le menu\n"
            f"*2* — 📅 Faire une réservation\n"
            f"*3* — 🛍️ Commander (à emporter)\n"
            f"*4* — ℹ️ Informations & contact\n"
	    f"*5* -    Service traiteur"
        )

    # Fallback
    return (
        "Je n'ai pas compris. Tapez *0* pour revenir au menu principal."
    )


# ══════════════════════════════════════════════════════════════
# WEBHOOK TWILIO WHATSAPP
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["POST"])
def webhook():
    """Point d'entrée Twilio WhatsApp."""
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")

    response_text = process_message(sender, incoming_msg)

    resp = MessagingResponse()
    resp.message(response_text)
    return str(resp)


@app.route("/", methods=["GET"])
def health():
    return "✅ Bot WhatsApp Le Talier — En ligne", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
