import os
import re
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from menu_data import get_menu_text, get_item_by_id
from excel_tracker import add_reservation
from google_calendar import create_reservation_event
from voice_agent import register_voice_routes

app = Flask(__name__)

# Enregistrer les routes de l'agent vocal
register_voice_routes(app)

sessions = {}

STATE_ACCUEIL = "accueil"
STATE_MENU_PRINCIPAL = "menu_principal"
STATE_RESERVATION_DATE = "resa_date"
STATE_RESERVATION_HEURE = "resa_heure"
STATE_RESERVATION_NOM = "resa_nom"
STATE_RESERVATION_NB = "resa_nb"
STATE_COMMANDE_MENU = "commande_menu"
STATE_COMMANDE_ITEM = "commande_item"
STATE_COMMANDE_ACCOMP = "commande_accomp"
STATE_COMMANDE_QTE = "commande_qte"
STATE_COMMANDE_SUITE = "commande_suite"
STATE_CONFIRMATION = "confirmation"
STATE_TERMINE = "termine"

ACCOMPAGNEMENTS = [
    "Igname pilee", "Igname frite", "Alloco", "Akassa", "Telibo",
    "Agbeli", "Piron", "Amiwo", "Haricots verts", "Couscous",
    "Riz", "Pommes sautees", "Pommes frites"
]

# Numero de telephone pour l'agent vocal traiteur
# A remplacer par votre vrai numero Twilio Voice
NUMERO_VOCAL_TRAITEUR = os.environ.get("TWILIO_VOICE_NUMBER", "+14155238886")
URL_BASE = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "https://le-talier-bot-production.up.railway.app")


def get_session(phone):
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


def reset_session(phone):
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


def calcul_total(commande):
    total = 0
    for item in commande:
        prix = item.get("prix", 0)
        qte = item.get("quantite", 1)
        if isinstance(prix, int):
            total += prix * qte
        elif isinstance(prix, str) and "-" in prix:
            try:
                prix_min = int(prix.split("-")[0].strip().replace(" ", ""))
                total += prix_min * qte
            except Exception:
                pass
    return total


def format_recapitulatif(session):
    lines = [
        "*RECAPITULATIF DE VOTRE RESERVATION*",
        "---",
        "Restaurant Le Talier",
        "Client: " + session["nom_client"],
        "Tel: " + session["telephone"],
        "Date: " + session["date"],
        "Heure: " + session["heure"],
        "Personnes: " + str(session["nb_personnes"]),
    ]
    type_labels = {
        "sur_place": "Sur place",
        "emporter": "A emporter",
        "traiteur": "Service traiteur"
    }
    lines.append("Service: " + type_labels.get(session["type_service"], "Sur place"))
    if session["commande"]:
        lines.append("\nVotre commande:")
        for item in session["commande"]:
            prix = item["prix"]
            prix_str = str(prix) + " FCFA"
            line = str(item["quantite"]) + "x " + item["nom"] + " - " + prix_str
            if item.get("accompagnement"):
                line += " + " + item["accompagnement"]
            lines.append("  " + line)
        total = calcul_total(session["commande"])
        lines.append("\nTotal estime: " + str(total) + " FCFA")
    lines.append("\n---")
    return "\n".join(lines)


def process_message(phone, message):
    session = get_session(phone)
    msg = message.strip().lower()
    state = session["state"]

    if msg in ["annuler", "cancel", "quitter"]:
        reset_session(phone)
        return "Demande annulee. Tapez *0* pour recommencer."

    if msg in ["menu", "aide", "help", "0", "recommencer", "restart",
               "bonjour", "bonsoir", "salut", "hello"] or state == STATE_ACCUEIL:
        session = get_session(phone)
        session["state"] = STATE_MENU_PRINCIPAL
        return (
            "Bienvenue au *Restaurant Le Talier* !\n"
            "Specialites africaines et europeennes\n\n"
            "Ouvert Lundi-Samedi | 11h-18h\n\n"
            "Que souhaitez-vous faire ?\n\n"
            "*1* - Voir le menu\n"
            "*2* - Faire une reservation\n"
            "*3* - Commander (a emporter)\n"
            "*4* - Informations & contact\n"
            "*5* - Service traiteur (evenement)\n\n"
            "Tapez le numero de votre choix"
        )

    if state == STATE_MENU_PRINCIPAL:
        if msg == "1":
            return get_menu_text() + "\n\nTapez *2* pour reserver | *3* pour commander | *0* menu"

        elif msg == "2":
            session["state"] = STATE_RESERVATION_DATE
            session["type_service"] = "sur_place"
            return "RESERVATION SUR PLACE\n\nQuelle est la date souhaitee ?\n(Format: JJ/MM/AAAA - ex: 15/04/2026)"

        elif msg == "3":
            session["state"] = STATE_RESERVATION_DATE
            session["type_service"] = "emporter"
            return "COMMANDE A EMPORTER\n\nPour quel jour ?\n(Format: JJ/MM/AAAA - ex: 15/04/2026)"

        elif msg == "4":
            return (
                "RESTAURANT LE TALIER\n\n"
                "Specialites africaines et europeennes\n"
                "Sur place | A emporter | Traiteur\n"
                "Lundi-Samedi : 11h a 18h\n\n"
                "Tapez *0* pour revenir au menu"
            )

        elif msg == "5":
            return (
                "SERVICE TRAITEUR - Le Talier\n\n"
                "Pour votre evenement special (mariage, bapteme,\n"
                "anniversaire, fete d'entreprise...), notre agent\n"
                "vocal vous accompagne personnellement.\n\n"
                "Appelez maintenant notre ligne dediee :\n\n"
                "*" + NUMERO_VOCAL_TRAITEUR + "*\n\n"
                "Notre assistant vocal vous posera des questions sur :\n"
                "- La date et l'heure de votre evenement\n"
                "- Le nombre de convives\n"
                "- Le type d'evenement\n"
                "- Vos demandes specifiques et allergies\n\n"
                "Votre demande sera enregistree automatiquement\n"
                "et notre equipe vous rappellera pour le devis.\n\n"
                "_Tapez *0* pour revenir au menu_"
            )

        else:
            return "Tapez *1* Menu | *2* Reserver | *3* Commander | *4* Infos | *5* Traiteur | *0* Accueil"

    if state == STATE_RESERVATION_DATE:
        if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", message.strip()):
            session["date"] = message.strip()
            session["state"] = STATE_RESERVATION_HEURE
            return "Date: *" + message.strip() + "*\n\nA quelle heure ?\n(Format: HH:MM - ex: 12:30)\nHoraires: 11h00 a 18h00"
        else:
            return "Format invalide. Entrez la date en *JJ/MM/AAAA*\nEx: *15/04/2026*"

    if state == STATE_RESERVATION_HEURE:
        heure_input = message.strip().replace("h", ":").replace("::", ":")
        if ":" not in heure_input:
            heure_input += ":00"
        try:
            parts = heure_input.split(":")
            h = int(parts[0])
            m = int(parts[1])
            if 11 <= h <= 17:
                session["heure"] = "{:02d}:{:02d}".format(h, m)
                session["state"] = STATE_RESERVATION_NOM
                return "Heure: *{:02d}:{:02d}*\n\nQuel est votre nom complet ?".format(h, m)
            else:
                return "Nous sommes ouverts de *11h00 a 18h00*.\nChoisissez une heure dans nos horaires."
        except Exception:
            return "Format invalide. Entrez l'heure en *HH:MM*\nEx: *12:30*"

    if state == STATE_RESERVATION_NOM:
        if len(message.strip()) >= 2:
            session["nom_client"] = message.strip().title()
            session["state"] = STATE_RESERVATION_NB
            return "Nom: *" + session["nom_client"] + "*\n\nPour combien de personnes ?\n(Ex: 2)"
        else:
            return "Veuillez entrer votre nom complet."

    if state == STATE_RESERVATION_NB:
        try:
            nb = int(message.strip())
            if 1 <= nb <= 50:
                session["nb_personnes"] = nb
                session["state"] = STATE_COMMANDE_MENU
                return (
                    str(nb) + " personne(s)\n\n"
                    "Souhaitez-vous pre-commander maintenant ?\n\n"
                    "*1* - Oui, je veux commander\n"
                    "*2* - Non, je commanderai sur place"
                )
            else:
                return "Nombre invalide. Entrez entre 1 et 50."
        except Exception:
            return "Veuillez entrer un nombre. Ex: *4*"

    if state == STATE_COMMANDE_MENU:
        if msg == "1":
            session["state"] = STATE_COMMANDE_ITEM
            return get_menu_text() + "\n\n---\nTapez l'ID du plat (ex: S1, V3)\nou *FIN* pour terminer"
        elif msg == "2":
            session["state"] = STATE_CONFIRMATION
            return format_recapitulatif(session) + "\n\nConfirmez-vous ? *OUI* ou *NON*"
        else:
            return "Tapez *1* pour commander ou *2* pour commander sur place."

    if state == STATE_COMMANDE_ITEM:
        if msg in ["fin", "terminer"]:
            session["state"] = STATE_CONFIRMATION
            return format_recapitulatif(session) + "\n\nConfirmez-vous ? *OUI* ou *NON*"
        item_id = message.strip().upper()
        item = get_item_by_id(item_id)
        if item:
            session["item_en_cours"] = dict(item)
            if item_id.startswith("S"):
                session["state"] = STATE_COMMANDE_ACCOMP
                accomp_list = "\n".join(
                    [str(i + 1) + " - " + a for i, a in enumerate(ACCOMPAGNEMENTS)]
                )
                return "Plat: *" + item["nom"] + "*\n\nChoisissez votre accompagnement :\n\n" + accomp_list
            else:
                session["state"] = STATE_COMMANDE_QTE
                prix = item["prix"]
                prix_str = str(prix) + " FCFA"
                return "Plat: *" + item["nom"] + "* - " + prix_str + "\n\nQuelle quantite ? (ex: 1)"
        else:
            return "ID non reconnu. Tapez un ID valide (ex: S1, V2)\nTapez *FIN* pour terminer"

    if state == STATE_COMMANDE_ACCOMP:
        try:
            choix = int(message.strip()) - 1
            if 0 <= choix < len(ACCOMPAGNEMENTS):
                session["item_en_cours"]["accompagnement"] = ACCOMPAGNEMENTS[choix]
                session["state"] = STATE_COMMANDE_QTE
                return "Accompagnement: *" + ACCOMPAGNEMENTS[choix] + "*\n\nQuelle quantite ? (ex: 1)"
            else:
                return "Tapez un numero entre 1 et " + str(len(ACCOMPAGNEMENTS))
        except Exception:
            return "Tapez un numero. Ex: *3*"

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
                nb_items = len(session["commande"])
                return (
                    str(qte) + "x *" + item["nom"] + "* ajoute(s) !\n"
                    + str(nb_items) + " article(s) dans votre commande\n"
                    "Total: *" + str(session["total"]) + " FCFA*\n\n"
                    "*1* - Ajouter un autre plat\n"
                    "*2* - Terminer et confirmer\n"
                    "*0* - Menu principal"
                )
            else:
                return "Quantite entre 1 et 20 svp."
        except Exception:
            return "Entrez un nombre. Ex: *2*"

    if state == STATE_COMMANDE_SUITE:
        if msg == "1":
            session["state"] = STATE_COMMANDE_ITEM
            return get_menu_text() + "\n\nTapez l'ID du prochain plat :"
        elif msg == "2":
            session["state"] = STATE_CONFIRMATION
            return format_recapitulatif(session) + "\n\nConfirmez-vous ? *OUI* ou *NON*"
        else:
            return "Tapez *1* pour ajouter un plat ou *2* pour terminer."

    if state == STATE_CONFIRMATION:
        if msg in ["oui", "yes", "o", "confirmer", "ok", "confirme"]:
            session["total"] = calcul_total(session["commande"])
            try:
                resa_num = add_reservation(session)
                excel_status = "Enregistre (N " + str(resa_num) + ")"
            except Exception as e:
                print("Excel error:", e)
                excel_status = "Erreur Excel"
                resa_num = "N/A"
            try:
                cal_link = create_reservation_event(session)
                cal_status = "Ajoute a Google Calendar" if cal_link else "Calendar non configure"
            except Exception as e:
                print("Calendar error:", e)
                cal_status = "Erreur Calendar"
            session["state"] = STATE_TERMINE
            return (
                "RESERVATION CONFIRMEE !\n\n"
                "N de reservation: *#" + str(resa_num) + "*\n"
                + session["nom_client"] + "\n"
                + session["date"] + " a " + session["heure"] + "\n"
                + str(session["nb_personnes"]) + " personne(s)\n"
                "Total: *" + str(session["total"]) + " FCFA*\n\n"
                + excel_status + "\n"
                + cal_status + "\n\n"
                "Merci ! Le Talier vous attend.\n"
                "Tapez *0* pour une nouvelle reservation"
            )
        elif msg in ["non", "no", "n", "annuler"]:
            reset_session(phone)
            return "Reservation annulee.\nTapez *0* pour recommencer."
        else:
            return "Tapez *OUI* pour confirmer ou *NON* pour annuler."

    if state == STATE_TERMINE:
        reset_session(phone)
        session = get_session(phone)
        session["state"] = STATE_MENU_PRINCIPAL
        return (
            "Bienvenue au *Restaurant Le Talier* !\n\n"
            "*1* - Voir le menu\n"
            "*2* - Faire une reservation\n"
            "*3* - Commander (a emporter)\n"
            "*4* - Informations & contact\n"
            "*5* - Service traiteur (evenement)"
        )

    return "Tapez *0* pour revenir au menu principal."


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")
    response_text = process_message(sender, incoming_msg)
    resp = MessagingResponse()
    resp.message(response_text)
    return str(resp)


@app.route("/", methods=["GET"])
def health():
    return "Bot WhatsApp Le Talier - En ligne", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)