# ============================================================
# AGENT VOCAL — Service Traiteur — Restaurant Le Talier
# ============================================================
# Technologie : Twilio Voice API + Speech Recognition (TwiML)
# Déclenchement : client choisit option 5 sur WhatsApp
# Flux vocal :
#   1. Accueil
#   2. Date de l'événement
#   3. Nombre de personnes
#   4. Type d'événement (mariage, baptême, anniversaire, etc.)
#   5. Demandes spécifiques / allergies / plats souhaités
#   6. Confirmation et récapitulatif
#   → Sauvegarde Excel + Google Calendar
# ============================================================

import os
from flask import request
from twilio.twiml.voice_response import VoiceResponse, Gather
from excel_tracker import add_reservation
from google_calendar import create_reservation_event

# Stockage des sessions vocales en mémoire
voice_sessions = {}


def get_voice_session(call_sid, phone=""):
    if call_sid not in voice_sessions:
        voice_sessions[call_sid] = {
            "step": "date",
            "nom_client": "Client Traiteur",
            "telephone": phone,
            "date": "",
            "heure": "",
            "nb_personnes": "",
            "type_evenement": "",
            "demandes_specifiques": "",
            "type_service": "traiteur",
            "commande": [],
            "total": 0,
        }
    return voice_sessions[call_sid]


def voice_accueil(response):
    """Message d'accueil de l'agent vocal."""
    gather = Gather(
        input="speech",
        action="/voice/date",
        method="POST",
        language="fr-FR",
        speech_timeout="auto",
        timeout=10
    )
    gather.say(
        "Bienvenue au service traiteur du Restaurant Le Talier. "
        "Spécialités africaines et européennes. "
        "Je suis votre assistant vocal pour organiser votre événement. "
        "Pour commencer, dites-moi la date de votre événement. "
        "Par exemple : le quinze avril deux mille vingt six.",
        language="fr-FR",
        voice="Polly.Léa"
    )
    response.append(gather)
    response.say(
        "Je n'ai pas entendu de réponse. Veuillez rappeler le Restaurant Le Talier. Au revoir.",
        language="fr-FR",
        voice="Polly.Léa"
    )
    return response


def voice_date(response, speech_result, call_sid, caller):
    """Traite la date et demande le nombre de personnes."""
    session = get_voice_session(call_sid, caller)
    session["date"] = speech_result if speech_result else "Date à confirmer"
    session["telephone"] = caller

    gather = Gather(
        input="speech",
        action="/voice/personnes",
        method="POST",
        language="fr-FR",
        speech_timeout="auto",
        timeout=10
    )
    gather.say(
        "Très bien, j'ai noté la date : " + session["date"] + ". "
        "Maintenant, combien de personnes attendez-vous pour votre événement ? "
        "Dites simplement le nombre.",
        language="fr-FR",
        voice="Polly.Léa"
    )
    response.append(gather)
    response.say("Je n'ai pas entendu. Merci de rappeler.", language="fr-FR", voice="Polly.Léa")
    return response


def voice_personnes(response, speech_result, call_sid):
    """Traite le nombre de personnes et demande le type d'événement."""
    session = voice_sessions.get(call_sid, {})
    session["nb_personnes"] = speech_result if speech_result else "À confirmer"

    gather = Gather(
        input="speech",
        action="/voice/evenement",
        method="POST",
        language="fr-FR",
        speech_timeout="auto",
        timeout=10
    )
    gather.say(
        "Parfait, " + session["nb_personnes"] + " personnes. "
        "Quel est le type de votre événement ? "
        "Par exemple : mariage, anniversaire, baptême, fête d'entreprise, ou autre événement.",
        language="fr-FR",
        voice="Polly.Léa"
    )
    response.append(gather)
    response.say("Je n'ai pas entendu. Merci de rappeler.", language="fr-FR", voice="Polly.Léa")
    return response


def voice_evenement(response, speech_result, call_sid):
    """Traite le type d'événement et demande les demandes spécifiques."""
    session = voice_sessions.get(call_sid, {})
    session["type_evenement"] = speech_result if speech_result else "Événement"

    gather = Gather(
        input="speech",
        action="/voice/specifiques",
        method="POST",
        language="fr-FR",
        speech_timeout="auto",
        timeout=15
    )
    gather.say(
        "Très bien, " + session["type_evenement"] + ". "
        "Avez-vous des demandes spécifiques ? "
        "Par exemple : des plats particuliers, des allergies alimentaires, "
        "un thème culinaire africain ou européen, ou toute autre précision. "
        "Parlez après le signal.",
        language="fr-FR",
        voice="Polly.Léa"
    )
    response.append(gather)
    response.say("Je n'ai pas entendu. Merci de rappeler.", language="fr-FR", voice="Polly.Léa")
    return response


def voice_specifiques(response, speech_result, call_sid):
    """Traite les demandes spécifiques et demande l'heure."""
    session = voice_sessions.get(call_sid, {})
    session["demandes_specifiques"] = speech_result if speech_result else "Aucune demande spécifique"

    gather = Gather(
        input="speech",
        action="/voice/heure",
        method="POST",
        language="fr-FR",
        speech_timeout="auto",
        timeout=10
    )
    gather.say(
        "Noté. " + session["demandes_specifiques"] + ". "
        "À quelle heure souhaitez-vous que le service commence ? "
        "Par exemple : à midi, ou à dix-neuf heures.",
        language="fr-FR",
        voice="Polly.Léa"
    )
    response.append(gather)
    response.say("Je n'ai pas entendu. Merci de rappeler.", language="fr-FR", voice="Polly.Léa")
    return response


def voice_heure(response, speech_result, call_sid):
    """Traite l'heure et donne la confirmation finale."""
    session = voice_sessions.get(call_sid, {})
    session["heure"] = speech_result if speech_result else "À définir"

    # Préparer la commande pour l'enregistrement
    session["commande"] = [{
        "nom": "Service Traiteur - " + session.get("type_evenement", "Événement"),
        "prix": 0,
        "quantite": 1,
        "accompagnement": session.get("demandes_specifiques", ""),
    }]

    # Récapitulatif vocal
    recap = (
        "Voici le récapitulatif de votre demande traiteur. "
        "Date : " + session.get("date", "") + ". "
        "Heure : " + session.get("heure", "") + ". "
        "Nombre de personnes : " + str(session.get("nb_personnes", "")) + ". "
        "Type d'événement : " + session.get("type_evenement", "") + ". "
        "Demandes spécifiques : " + session.get("demandes_specifiques", "") + ". "
    )

    # Sauvegarder dans Excel
    try:
        resa_num = add_reservation(session)
        save_status = "Votre demande a été enregistrée sous le numéro " + str(resa_num) + ". "
    except Exception as e:
        print("Excel error:", e)
        save_status = "Votre demande a été enregistrée. "

    # Créer l'événement Google Calendar
    try:
        create_reservation_event(session)
    except Exception as e:
        print("Calendar error:", e)

    response.say(
        recap +
        save_status +
        "Notre équipe vous contactera dans les plus brefs délais pour confirmer les détails et le devis. "
        "Merci de faire confiance au Restaurant Le Talier. "
        "Nous serons ravis de contribuer à la réussite de votre événement. Au revoir !",
        language="fr-FR",
        voice="Polly.Léa"
    )
    response.hangup()

    # Nettoyer la session
    if call_sid in voice_sessions:
        del voice_sessions[call_sid]

    return response


def register_voice_routes(app):
    """Enregistre toutes les routes vocales dans l'application Flask."""

    @app.route("/voice/accueil", methods=["GET", "POST"])
    def voice_accueil_route():
        response = VoiceResponse()
        return str(voice_accueil(response))

    @app.route("/voice/date", methods=["POST"])
    def voice_date_route():
        speech_result = request.form.get("SpeechResult", "")
        call_sid = request.form.get("CallSid", "")
        caller = request.form.get("Caller", "")
        response = VoiceResponse()
        return str(voice_date(response, speech_result, call_sid, caller))

    @app.route("/voice/personnes", methods=["POST"])
    def voice_personnes_route():
        speech_result = request.form.get("SpeechResult", "")
        call_sid = request.form.get("CallSid", "")
        response = VoiceResponse()
        return str(voice_personnes(response, speech_result, call_sid))

    @app.route("/voice/evenement", methods=["POST"])
    def voice_evenement_route():
        speech_result = request.form.get("SpeechResult", "")
        call_sid = request.form.get("CallSid", "")
        response = VoiceResponse()
        return str(voice_evenement(response, speech_result, call_sid))

    @app.route("/voice/specifiques", methods=["POST"])
    def voice_specifiques_route():
        speech_result = request.form.get("SpeechResult", "")
        call_sid = request.form.get("CallSid", "")
        response = VoiceResponse()
        return str(voice_specifiques(response, speech_result, call_sid))

    @app.route("/voice/heure", methods=["POST"])
    def voice_heure_route():
        speech_result = request.form.get("SpeechResult", "")
        call_sid = request.form.get("CallSid", "")
        response = VoiceResponse()
        return str(voice_heure(response, speech_result, call_sid))
