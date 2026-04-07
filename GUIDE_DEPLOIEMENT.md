# 🍽️ Guide de Déploiement — Bot WhatsApp Le Talier

## Ce que fait le bot

Ce bot WhatsApp automatise l'accueil client du restaurant **Le Talier** :

- 📋 **Menu complet** avec prix et disponibilités
- 📅 **Réservation** (date, heure, nom, nb personnes)
- 🛍️ **Commande** (sur place ou à emporter)
- 📊 **Récapitulatif** → sauvegarde Excel automatique
- 🗓️ **Google Calendar** → événement créé à chaque réservation

---

## 📁 Structure des fichiers

```
le-talier-bot/
├── bot.py                    ← Application principale (Flask + Twilio)
├── menu_data.py              ← Menu et infos restaurant
├── excel_tracker.py          ← Sauvegarde Excel des réservations
├── google_calendar.py        ← Intégration Google Calendar
├── reservations_le_talier.xlsx  ← Fichier de suivi (créé automatiquement)
├── requirements.txt          ← Dépendances Python
├── .env.example              ← Modèle de configuration
└── GUIDE_DEPLOIEMENT.md      ← Ce guide
```

---

## 🚀 Installation étape par étape

### Étape 1 — Prérequis

- Python 3.10 ou supérieur installé
- Un compte **Twilio** (gratuit pour commencer)
- Un compte **Google** avec accès à Google Calendar

### Étape 2 — Installer les dépendances

```bash
cd le-talier-bot
pip install -r requirements.txt
```

### Étape 3 — Configurer Twilio (WhatsApp)

1. Créer un compte sur [twilio.com](https://www.twilio.com)
2. Aller dans **Messaging → Try it out → Send a WhatsApp message**
3. Scanner le QR code avec le numéro WhatsApp du restaurant (Sandbox)
4. Récupérer votre **Account SID** et **Auth Token**
5. Copier `.env.example` en `.env` et remplir les valeurs :

```bash
cp .env.example .env
```

### Étape 4 — Configurer Google Calendar

1. Aller sur [console.cloud.google.com](https://console.cloud.google.com)
2. Créer un projet (ex: "Le Talier Bot")
3. Activer l'API : **Bibliothèque → Google Calendar API → Activer**
4. Créer des identifiants : **Identifiants → Créer → ID client OAuth 2.0**
   - Type : **Application de bureau**
5. Télécharger le fichier `credentials.json` dans le dossier `le-talier-bot/`
6. Au premier démarrage, une fenêtre s'ouvre pour autoriser l'accès → cliquer "Autoriser"
7. Un fichier `token.json` est généré automatiquement (à garder secret !)

### Étape 5 — Démarrer le bot en local

```bash
python bot.py
```

Le bot démarre sur `http://localhost:5000`

### Étape 6 — Exposer le bot sur Internet (ngrok)

Twilio a besoin d'une URL publique pour envoyer les messages au bot.

1. Installer ngrok : [ngrok.com](https://ngrok.com)
2. Lancer :
```bash
ngrok http 5000
```
3. Copier l'URL HTTPS fournie (ex: `https://abc123.ngrok.io`)

### Étape 7 — Connecter Twilio au bot

1. Dans la console Twilio → **Messaging → Settings → WhatsApp Sandbox Settings**
2. Dans le champ **"When a message comes in"** :
   - Coller l'URL ngrok + `/webhook`
   - Exemple : `https://abc123.ngrok.io/webhook`
   - Méthode : **POST**
3. Cliquer **Save**

### Étape 8 — Tester !

Envoyer `Bonjour` sur WhatsApp au numéro Twilio sandbox.

---

## 🌍 Déploiement en production (serveur permanent)

Pour que le bot fonctionne 24h/24 sans dépendre de votre ordinateur :

### Option A — Railway (gratuit, recommandé)

1. Créer un compte sur [railway.app](https://railway.app)
2. Nouveau projet → **Deploy from GitHub**
3. Pousser le dossier `le-talier-bot` sur GitHub
4. Ajouter les variables d'environnement dans Railway
5. Railway fournit une URL permanente → à mettre dans Twilio

### Option B — Render (gratuit)

1. Compte sur [render.com](https://render.com)
2. Nouveau service **Web Service** → lier votre dépôt
3. Start command : `gunicorn bot:app`
4. URL permanente fournie automatiquement

### Option C — Serveur VPS (avancé)

```bash
gunicorn bot:app --bind 0.0.0.0:5000 --workers 2
```

---

## 📲 Passer en production WhatsApp (numéro réel)

Pour utiliser le **vrai numéro WhatsApp** du restaurant :

1. Dans Twilio → **Messaging → Senders → WhatsApp Senders**
2. Cliquer **"Request Access"** pour l'API WhatsApp Business
3. Fournir les informations du restaurant
4. Délai d'approbation : 1 à 3 jours ouvrés
5. Une fois approuvé, remplacer le numéro sandbox dans `.env`

---

## 📊 Consulter les réservations

Le fichier `reservations_le_talier.xlsx` est mis à jour automatiquement à chaque nouvelle réservation confirmée. Il contient :

- Feuille **Réservations** : liste complète avec toutes les infos
- Feuille **Statistiques** : totaux automatiques (CA, couverts, etc.)

---

## 🔄 Scénario de conversation complet

```
Client → Bonjour
Bot    → Bienvenue au Restaurant Le Talier !
         1-Menu | 2-Réserver | 3-Commander | 4-Infos

Client → 2
Bot    → Date souhaitée ? (JJ/MM/AAAA)

Client → 08/04/2026
Bot    → Heure ? (11h-18h)

Client → 12:30
Bot    → Votre nom ?

Client → Marie Koné
Bot    → Pour combien de personnes ?

Client → 3
Bot    → Souhaitez-vous pré-commander ? 1-Oui | 2-Non

Client → 1
Bot    → [Menu affiché] Tapez l'ID du plat

Client → S5
Bot    → Sauce Arachide ✓. Choisissez l'accompagnement (liste)

Client → 3
Bot    → Quantité ?

Client → 2
Bot    → 2x Sauce Arachide ajoutés. 1-Autre plat | 2-Terminer

Client → 2
Bot    → [Récapitulatif complet]. OUI pour confirmer ?

Client → OUI
Bot    → ✅ Réservation confirmée ! N°2
         📊 Enregistré dans Excel
         📅 Ajouté à Google Calendar
```

---

## ⚙️ Personnaliser le bot

### Modifier le menu

Ouvrir `menu_data.py` et éditer la variable `MENU`.

### Changer les horaires

Dans `menu_data.py` → `RESTAURANT_INFO["horaires"]`
Dans `bot.py` → `if 11 <= h <= 17` (validation de l'heure)

### Ajouter un service traiteur

Dans le menu principal de `bot.py`, ajouter un cas `msg == "5"` pour le traiteur.

---

## 🆘 Support & problèmes courants

| Problème | Solution |
|---|---|
| Bot ne répond pas | Vérifier que l'URL webhook est correcte dans Twilio |
| Excel non créé | Vérifier les droits d'écriture dans le dossier |
| Calendar error | Vérifier que `credentials.json` est présent et valide |
| Timeout Twilio | Réduire le temps de traitement (< 15 secondes) |

---

*Bot développé pour le Restaurant Le Talier — Spécialités africaines & européennes*
