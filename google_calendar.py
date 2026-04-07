# ============================================================
# INTÉGRATION GOOGLE CALENDAR — Restaurant Le Talier
# ============================================================
# Prérequis :
#   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
#
# Configuration :
#   1. Aller sur https://console.cloud.google.com
#   2. Créer un projet → Activer "Google Calendar API"
#   3. Créer des identifiants OAuth 2.0 (type: Desktop App)
#   4. Télécharger le fichier credentials.json dans ce dossier
#   5. Lancer une première fois pour autoriser → génère token.json
# ============================================================

import os
import json
from datetime import datetime, timedelta

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
CALENDAR_ID = "primary"  # Utilise l'agenda principal; remplacer par l'ID si agenda dédié

def get_calendar_service():
    """Crée et retourne le service Google Calendar authentifié."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_reservation_event(reservation: dict) -> str:
    """
    Crée un événement Google Calendar pour une réservation.

    Args:
        reservation: dict avec les clés:
            - nom_client (str)
            - telephone (str)
            - date (str, format: DD/MM/YYYY)
            - heure (str, format: HH:MM)
            - nb_personnes (int)
            - type_service (str): 'sur_place' | 'emporter' | 'traiteur'
            - commande (list of dicts)
            - total (int/float)

    Returns:
        URL de l'événement Google Calendar créé
    """
    try:
        service = get_calendar_service()

        # Parser la date et l'heure
        date_str = reservation.get("date", "")
        heure_str = reservation.get("heure", "12:00")

        try:
            dt_debut = datetime.strptime(f"{date_str} {heure_str}", "%d/%m/%Y %H:%M")
        except ValueError:
            dt_debut = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

        dt_fin = dt_debut + timedelta(hours=1, minutes=30)

        # Construire la description
        commande_lines = []
        for item in reservation.get("commande", []):
            prix = item.get("prix", 0)
            if isinstance(prix, int):
                prix_str = f"{prix:,} FCFA".replace(",", " ")
            else:
                prix_str = f"{prix} FCFA"
            commande_lines.append(
                f"  • {item.get('quantite', 1)}x {item.get('nom')} — {prix_str}"
            )

        type_service_labels = {
            "sur_place": "🍽️ Sur place",
            "emporter": "🛍️ À emporter",
            "traiteur": "🎉 Service traiteur"
        }
        service_label = type_service_labels.get(
            reservation.get("type_service", "sur_place"), "Sur place"
        )

        total = reservation.get("total", 0)
        total_str = f"{total:,} FCFA".replace(",", " ") if isinstance(total, (int, float)) else str(total)

        description = f"""🍽️ RÉSERVATION — Restaurant Le Talier

👤 Client: {reservation.get('nom_client', 'N/A')}
📱 Téléphone: {reservation.get('telephone', 'N/A')}
👥 Nombre de personnes: {reservation.get('nb_personnes', 1)}
🛎️ Type de service: {service_label}

📋 COMMANDE:
{chr(10).join(commande_lines) if commande_lines else '  (Commande à préciser sur place)'}

💰 TOTAL ESTIMÉ: {total_str}

---
Réservation créée automatiquement via le bot WhatsApp Le Talier."""

        event = {
            "summary": f"🍽️ Résa {reservation.get('nom_client', 'Client')} — {reservation.get('nb_personnes', 1)} pers. — Le Talier",
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
            "colorId": "2",  # Vert (sage)
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }

        created_event = service.events().insert(
            calendarId=CALENDAR_ID, body=event
        ).execute()

        return created_event.get("htmlLink", "")

    except Exception as e:
        print(f"[Google Calendar] Erreur: {e}")
        return ""
