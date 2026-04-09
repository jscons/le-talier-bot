import os
import json
import tempfile
from datetime import datetime, timedelta

CALENDAR_ID = "primary"


def get_calendar_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = None

    # Lire depuis les variables d'environnement Railway (prioritaire)
    token_json_str = os.environ.get("GOOGLE_TOKEN_JSON", "")
    credentials_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")

    if token_json_str:
        # Charger le token depuis la variable d'environnement
        token_data = json.loads(token_json_str)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    elif os.path.exists("token.json"):
        # Fallback : lire depuis le fichier local
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Mettre à jour la variable d'environnement avec le token rafraichi
            print("[Calendar] Token rafraichi. Mettez a jour GOOGLE_TOKEN_JSON dans Railway avec :")
            print(creds.to_json())
        else:
            # Utiliser credentials depuis variable d'environnement ou fichier
            if credentials_json_str:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                    f.write(credentials_json_str)
                    creds_file = f.name
            elif os.path.exists("credentials.json"):
                creds_file = "credentials.json"
            else:
                print("[Calendar] credentials.json introuvable. Configurez GOOGLE_CREDENTIALS_JSON dans Railway.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
            if credentials_json_str:
                os.unlink(creds_file)

        # Sauvegarder localement si possible
        try:
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        except Exception:
            pass

    return build("calendar", "v3", credentials=creds)


def create_reservation_event(reservation):
    try:
        service = get_calendar_service()
        if not service:
            return ""

        date_str = reservation.get("date", "")
        heure_str = reservation.get("heure", "12:00")

        try:
            dt_debut = datetime.strptime(date_str + " " + heure_str, "%d/%m/%Y %H:%M")
        except ValueError:
            dt_debut = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

        dt_fin = dt_debut + timedelta(hours=1, minutes=30)

        commande_lines = []
        for item in reservation.get("commande", []):
            prix = item.get("prix", 0)
            prix_str = str(prix) + " FCFA"
            accomp = item.get("accompagnement", "")
            line = str(item.get("quantite", 1)) + "x " + item.get("nom", "") + " - " + prix_str
            if accomp:
                line += " + " + accomp
            commande_lines.append("  - " + line)

        type_service_labels = {
            "sur_place": "Sur place",
            "emporter": "A emporter",
            "traiteur": "Service traiteur"
        }
        service_label = type_service_labels.get(reservation.get("type_service", "sur_place"), "Sur place")

        total = reservation.get("total", 0)
        total_str = str(total) + " FCFA"

        description = (
            "RESERVATION - Restaurant Le Talier\n\n"
            "Client: " + reservation.get("nom_client", "N/A") + "\n"
            "Tel: " + reservation.get("telephone", "N/A") + "\n"
            "Personnes: " + str(reservation.get("nb_personnes", 1)) + "\n"
            "Service: " + service_label + "\n\n"
            "COMMANDE:\n" + ("\n".join(commande_lines) if commande_lines else "A preciser") + "\n\n"
            "TOTAL: " + total_str + "\n\n"
            "Reservation creee via bot WhatsApp Le Talier."
        )

        event = {
            "summary": "Resa " + reservation.get("nom_client", "Client") + " - " + str(reservation.get("nb_personnes", 1)) + " pers. - Le Talier",
            "location": "Restaurant Le Talier",
            "description": description,
            "start": {
                "dateTime": dt_debut.isoformat(),
                "timeZone": "Africa/Abidjan",
            },
            "end": {
                "dateTime": dt_fin.isoformat(),
                "timeZone": "Africa/Abidjan",
            },
            "colorId": "2",
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }

        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return created_event.get("htmlLink", "")

    except Exception as e:
        print("[Google Calendar] Erreur:", e)
        return ""
