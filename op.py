import json
import os
import uuid
from datetime import timedelta
from flask import Flask, jsonify, render_template, request, session
from supabase import create_client
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURATION SUPABASE ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kbjdxxrryvvnahcnsjys.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtiamR4eHJyeXZ2bmFoY25zanlzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwOTY2NTQsImV4cCI6MjEwMTY3MjY1NH0.duiZjw8DWDWnuhgP9lgRFBvCDm9JoheOuaKlutoI37E")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "votre_cle_secrete_ultra_securisee")
app.permanent_session_lifetime = timedelta(days=30) # Sessions valides 30 jours


def get_current_user():
    """Récupère le pseudo de l'utilisateur connecté via session, cookies ou device_sessions"""
    try:
        # 1. Vérifier la session Flask
        for key in ["username", "pseudo", "user", "user_id"]:
            if session.get(key):
                return session.get(key)

        # 2. Vérifier les cookies directs
        for key in ["op_username", "username", "pseudo", "user"]:
            if request.cookies.get(key):
                return request.cookies.get(key)

        # 3. Vérifier via l'identifiant d'appareil (device_sessions dans Supabase)
        device_id = request.headers.get("X-Device-ID") or request.cookies.get("op_device_id")
        if device_id:
            res = supabase.table("device_sessions").select("*").eq("device_id", device_id).execute()
            if res.data and len(res.data) > 0:
                sess = res.data[0]
                return sess.get("username") or sess.get("pseudo") or sess.get("user_id") or sess.get("user")

        return None
    except Exception as e:
        print(f"Erreur get_current_user: {e}")
        return None


# --- GESTION DU COOKIE APPAREIL UNIQUE ---
@app.after_request
def set_device_cookie(response):
    """Génère un identifiant d'appareil unique si aucun n'existe dans les cookies."""
    if not request.cookies.get('op_device_id'):
        new_device_id = str(uuid.uuid4())
        # Dépose le cookie valide 10 ans sur le navigateur
        response.set_cookie('op_device_id', new_device_id, max_age=315360000, httponly=True, samesite='Lax')
    return response


# --- RECONNEXION AUTOMATIQUE ---
@app.before_request
def auto_login_from_device():
    session.permanent = True
    if 'user_id' in session:
        return

    device_id = request.cookies.get('op_device_id')
    if not device_id:
        return

    try:
        res = supabase.table('device_sessions').select('user_id').eq('device_id', device_id).execute()
        if res.data and len(res.data) > 0:
            session['user_id'] = res.data[0]['user_id']
    except Exception as e:
        print(f"Erreur Reconnexion Auto: {e}")


# --- AUTHENTIFICATION (INSCRIPTION & CONNEXION) ---
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        pseudo = data.get('pseudo')
        password = data.get('password')

        if not pseudo or not password:
            return jsonify({'status': 'error', 'message': 'Le pseudo et le mot de passe sont requis.'}), 400

        check = supabase.table('utilisateurs').select('pseudo').eq('pseudo', pseudo).execute()
        if check.data:
            return jsonify({'status': 'error', 'message': 'Ce pseudo est déjà pris. Choisis-en un autre !'}), 409

        hashed_pw = generate_password_hash(password)

        supabase.table('utilisateurs').insert({
            'pseudo': pseudo,
            'mot_de_passe': hashed_pw
        }).execute()

        dev_id = get_device_id_raw()
        supabase.table('user_collections').update({'user_id': pseudo}).eq('device_id', dev_id).is_('user_id', 'null').execute()
        supabase.table('user_wishlists').update({'user_id': pseudo}).eq('device_id', dev_id).is_('user_id', 'null').execute()
        supabase.table('user_decks').update({'user_id': pseudo}).eq('device_id', dev_id).is_('user_id', 'null').execute()

        session['user_id'] = pseudo

        if dev_id:
            supabase.table('device_sessions').upsert({
                'device_id': dev_id,
                'user_id': pseudo
            }).execute()

        return jsonify({'status': 'success', 'message': f'Compte créé avec succès ! Bienvenue {pseudo}.'})

    except Exception as e:
        print(f"Erreur Register: {e}")
        return jsonify({'status': 'error', 'message': 'Erreur lors de la création du compte.'}), 500

@app.route('/login', methods=['POST'])
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        pseudo = data.get('pseudo') or data.get('user_id')
        password = data.get('password')

        if not pseudo or not password:
            return jsonify({'status': 'error', 'message': 'Pseudo et mot de passe requis.'}), 400

        reponse = supabase.table('utilisateurs').select('mot_de_passe').eq('pseudo', pseudo).execute()

        if not reponse.data:
            return jsonify({'status': 'error', 'message': 'Ce pseudo n\'existe pas.'}), 401

        hash_enregistre = reponse.data[0]['mot_de_passe']

        if check_password_hash(hash_enregistre, password):
            session['user_id'] = pseudo

            dev_id = get_device_id_raw()
            if dev_id:
                supabase.table('device_sessions').upsert({
                    'device_id': dev_id,
                    'user_id': pseudo
                }).execute()

            return jsonify({'status': 'success', 'message': f'Ravi de te revoir, {pseudo} !'})
        else:
            return jsonify({'status': 'error', 'message': 'Mot de passe incorrect.'}), 401

    except Exception as e:
        print(f"Erreur Login: {e}")
        return jsonify({'status': 'error', 'message': 'Erreur lors de la connexion.'}), 500

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    try:
        dev_id = request.cookies.get('op_device_id')
        if dev_id:
            supabase.table('device_sessions').delete().eq('device_id', dev_id).execute()

        session.pop('user_id', None)
        # Reinitialise le deck actif local
        sauvegarder_deck_actif_appareil(None, {"leader": None, "cards": []})
        return jsonify({'status': 'success', 'message': 'Déconnecté'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# --- IDENTIFICATION INTELLIGENTE (USER_ID ou DEVICE_ID) ---
def get_device_id_raw():
    device_id = request.cookies.get('op_device_id')
    if not device_id:
        device_id = request.headers.get('X-Device-ID')
    if not device_id:
        device_id = 'default_device'
    return device_id

def get_user_identity():
    if 'user_id' in session and session['user_id']:
        return {'type': 'user_id', 'id': session['user_id']}

    return {'type': 'device_id', 'id': get_device_id_raw()}


# --- UTILITAIRES APPAREIL & CACHE LOCAL ---
def get_device_id():
    identity = get_user_identity()
    return identity['id']

def get_device_json_path(prefixe_fichier):
    device_id = get_device_id()
    os.makedirs('donnees_utilisateurs', exist_ok=True)
    return f"donnees_utilisateurs/{prefixe_fichier}_{device_id}.json"

def lire_json_appareil(prefixe_fichier, valeur_par_defaut):
    fichier = get_device_json_path(prefixe_fichier)
    if os.path.exists(fichier):
        with open(fichier, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return valeur_par_defaut
    return valeur_par_defaut

def sauvegarder_json_appareil(prefixe_fichier, donnees):
    fichier = get_device_json_path(prefixe_fichier)
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4)


# --- FONCTIONS NATIVES & SESSIONS ---
def charger_donnees():
    dossier_actuel = os.path.dirname(os.path.abspath(__file__))
    chemin_json = os.path.join(dossier_actuel, "cartes.json")
    with open(chemin_json, "r", encoding="utf-8") as f:
        return chemin_json, json.load(f)

def charger_deck_actif_appareil():
    return lire_json_appareil('deck_actif', {"nom": None, "deck": {"leader": None, "cards": []}})

def sauvegarder_deck_actif_appareil(nom, deck):
    sauvegarder_json_appareil('deck_actif', {"nom": nom, "deck": deck})


# --- FONCTIONS SUPABASE (COLLECTION, WISHLIST & DECKS) ---
def charger_collection_supabase():
    identity = get_user_identity()
    col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

    try:
        reponse = supabase.table('user_collections') \
            .select('card_number, quantite') \
            .eq(col, identity['id']) \
            .execute()
        return {row['card_number']: row['quantite'] for row in reponse.data} if reponse.data else {}
    except Exception as e:
        print(f"Erreur Supabase Collection: {e}")
        return {}

def appliquer_quantites_collection(donnees_json):
    dict_collection = charger_collection_supabase()
    for carte in donnees_json:
        id_carte = carte.get("card_number", "")
        carte["quantite"] = dict_collection.get(id_carte, 0)

def appliquer_wishlist(donnees_json):
    identity = get_user_identity()
    col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

    try:
        reponse = supabase.table('user_wishlists') \
            .select('card_number') \
            .eq(col, identity['id']) \
            .execute()
        cards_in_wishlist = {row['card_number'] for row in reponse.data} if reponse.data else set()
    except Exception as e:
        print(f"Erreur Supabase Wishlist: {e}")
        cards_in_wishlist = set()

    for carte in donnees_json:
        id_carte = carte.get("card_number", "")
        carte["in_wishlist"] = id_carte in cards_in_wishlist

def charger_decks():
    identity = get_user_identity()
    col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

    try:
        reponse = supabase.table('user_decks') \
            .select('nom_deck, structure_deck') \
            .eq(col, identity['id']) \
            .execute()
        tous_les_decks = {row['nom_deck']: row['structure_deck'] for row in reponse.data} if reponse.data else {}
    except Exception as e:
        print(f"Erreur Supabase Decks: {e}")
        tous_les_decks = {}
    return "", tous_les_decks


# --- FORMATAGE ET TRI DES CARTES ---
def trier_cartes(liste_cartes):
    def cle_de_tri(carte):
        rarete = str(carte.get("rarity", "")).strip().upper()
        est_special = 1 if rarete in ["SP", "TR", "SPECIAL", "TREASURE RARE"] else 0
        num_complet = str(carte.get("card_number", "")).strip().upper()

        chiffres = 999
        if "-" in num_complet:
            try:
                suffixe = num_complet.split("-")[1]
                suffixe_propre = suffixe.split("_")[0]
                chiffres_extraits = "".join([c for c in suffixe_propre if c.isdigit()])
                if chiffres_extraits:
                    chiffres = int(chiffres_extraits)
            except:
                pass

        est_alt = bool(carte.get("is_alternative", False))
        return (est_special, chiffres, est_alt)

    liste_cartes.sort(key=cle_de_tri)
    return liste_cartes

def formater_carte_image(carte):
    if "quantite" not in carte: carte["quantite"] = 0
    try: carte["prix"] = float(carte.get("prix", 0.0))
    except: carte["prix"] = 0.0

    card_number = carte.get("card_number", "")
    a_un_suffixe_alt = any(f"_p{i}" in card_number for i in range(1, 10))

    if a_un_suffixe_alt:
        carte["image_url"] = f"/static/{card_number}.jpg"
    elif carte.get("is_alternative"):
        carte["image_url"] = f"/static/{card_number}_p1.jpg"
    else:
        carte["image_url"] = f"/static/{card_number}.jpg"

    couleur_brute = carte.get("color", "unknown")
    if isinstance(couleur_brute, list):
        couleur_propre = "-".join([str(c).lower().strip() for c in couleur_brute])
    else:
        couleur_propre = str(couleur_brute).lower().replace("/", "-").replace(" ", "").strip()

    carte["couleur_propre"] = couleur_propre
    return carte

def calculer_prix_deck_actuel(deck_memoire=None):
    try:
        if deck_memoire is None:
            etat = charger_deck_actif_appareil()
            deck_memoire = etat["deck"]

        _, donnees_json = charger_donnees()
        dict_prix = {c["card_number"]: float(c.get("prix", 0.0)) for c in donnees_json}

        prix_total = 0.0
        if deck_memoire.get("leader"):
            id_leader = deck_memoire["leader"]["card_number"]
            prix_total += dict_prix.get(id_leader, 0.0)

        for c in deck_memoire.get("cards", []):
            prix_unitaire = dict_prix.get(c["card_number"], 0.0)
            prix_total += prix_unitaire * c["quantite_deck"]

        return round(prix_total, 2)
    except:
        return 0.0


# --- ROUTES PRINCIPALES ---
@app.route("/")
def index():
    try:
        _, donnees_json = charger_donnees()
        appliquer_quantites_collection(donnees_json)

        series_stats = {}

        for carte in donnees_json:
            serie_code = str(carte.get("serie", "")).upper().replace("-", "").strip()
            if not serie_code:
                num_complet = str(carte.get("card_number", "")).upper()
                serie_code = num_complet.split("-")[0].replace("-", "") if "-" in num_complet else "AUTRE"

            if serie_code not in series_stats:
                series_stats[serie_code] = {"total": 0, "possedees": 0, "pourcentage": 0}

            series_stats[serie_code]["total"] += 1
            if carte.get("quantite", 0) > 0:
                series_stats[serie_code]["possedees"] += 1

        for code, stats in series_stats.items():
            tot = stats["total"]
            pos = stats["possedees"]
            stats["pourcentage"] = round((pos / tot) * 100) if tot > 0 else 0

        return render_template("accueil.html", series_stats=series_stats)
    except Exception as e:
        return f"Erreur lors du chargement de l'accueil : {e}"

@app.route("/atelier_de_deck")
def atelier_de_deck():
    return render_template("deck.html")

@app.route("/decks")
def voir_les_decks():
    try:
        _, donnees_json = charger_donnees()
        _, tous_les_decks = charger_decks()

        appliquer_quantites_collection(donnees_json)

        for carte in donnees_json:
            formater_carte_image(carte)

        return render_template("index.html", cartes_python=donnees_json, total_prix=0, nom_de_la_serie="Mon Atelier des Decks", decks_sauvegardes=tous_les_decks)
    except Exception as e:
        return f"Erreur : {e}"

@app.route("/cartes/<mode>")
def voir_cartes(mode):
    try:
        _, donnees_json = charger_donnees()
        _, tous_les_decks = charger_decks()

        appliquer_quantites_collection(donnees_json)
        appliquer_wishlist(donnees_json)

        liste_filtree = []
        for carte in donnees_json:
            formater_carte_image(carte)
            if mode == "toutes":
                liste_filtree.append(carte)
            elif mode == "possedees" and carte["quantite"] > 0:
                liste_filtree.append(carte)
            elif mode == "wishlist" and carte.get("in_wishlist", False):
                liste_filtree.append(carte)

        liste_filtree = trier_cartes(liste_filtree)
        total_prix = sum(c["quantite"] * c["prix"] for c in liste_filtree)

        titre = "Toutes les Cartes"
        if mode == "possedees": titre = "Ma Collection (Cartes possédées)"
        elif mode == "wishlist": titre = "Ma Wishlist (Cartes recherchées)"

        return render_template("index.html", cartes_python=liste_filtree, total_prix=total_prix, nom_de_la_serie=titre, decks_sauvegardes=tous_les_decks)
    except Exception as e:
        return f"Erreur : {e}"

@app.route("/serie/<nom_serie>")
def voir_serie(nom_serie):
    try:
        _, donnees_json = charger_donnees()
        _, tous_les_decks = charger_decks()

        appliquer_quantites_collection(donnees_json)

        liste_cartes_filtrees = []
        target_serie = nom_serie.upper()

        for carte in donnees_json:
            serie_carte = str(carte.get("serie", "")).upper()
            num_complet = str(carte.get("card_number", "")).upper()
            vrai_prefixe = num_complet.split("-")[0] if "-" in num_complet else ""

            if serie_carte == target_serie or vrai_prefixe == target_serie:
                formater_carte_image(carte)
                liste_cartes_filtrees.append(carte)

        liste_cartes_filtrees = trier_cartes(liste_cartes_filtrees)
        valeur_totale = sum(c["quantite"] * c.get("prix", 0.0) for c in liste_cartes_filtrees)
        return render_template("index.html", cartes_python=liste_cartes_filtrees, total_prix=valeur_totale, nom_de_la_serie=nom_serie, decks_sauvegardes=tous_les_decks)
    except Exception as e:
        return f"Erreur : {e}"


# --- ROUTE MODIFIER QUANTITÉ (COLLECTION) ---
@app.route('/modifier_quantite', methods=['POST'])
def modifier_quantite():
    try:
        data = request.get_json()
        identity = get_user_identity()
        card_number = data.get('card_number')
        action = data.get('action')

        col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

        reponse = supabase.table('user_collections') \
            .select('id, quantite') \
            .eq(col, identity['id']) \
            .eq('card_number', card_number) \
            .execute()

        if reponse.data:
            row_id = reponse.data[0]['id']
            qty_actuelle = reponse.data[0].get('quantite', 0)
            nouvelle_qty = max(0, qty_actuelle + 1 if action == 'plus' else qty_actuelle - 1)

            supabase.table('user_collections').update({
                'quantite': nouvelle_qty
            }).eq('id', row_id).execute()
        else:
            nouvelle_qty = 1 if action == 'plus' else 0
            if nouvelle_qty > 0:
                insert_data = {'card_number': card_number, 'quantite': nouvelle_qty}
                insert_data[col] = identity['id']

                supabase.table('user_collections').insert(insert_data).execute()

        _, donnees_json = charger_donnees()
        collection_a_jour = charger_collection_supabase()

        nouveau_total = 0.0
        for carte in donnees_json:
            qte = collection_a_jour.get(carte.get("card_number"), 0)
            if qte > 0:
                try:
                    prix = float(carte.get("prix", 0.0))
                except:
                    prix = 0.0
                nouveau_total += qte * prix

        return jsonify({
            'status': 'success',
            'nouvelle_quantite': nouvelle_qty,
            'nouveau_total_prix': nouveau_total
        })
    except Exception as e:
        print(f"Erreur modifier_quantite: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# --- ROUTE TOGGLE WISHLIST ---
@app.route("/api/toggle_wishlist", methods=["POST"])
def toggle_wishlist():
    try:
        donnees = request.get_json()
        identity = get_user_identity()
        card_number = donnees.get("card_number")

        col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

        check = supabase.table('user_wishlists') \
            .select('id') \
            .eq(col, identity['id']) \
            .eq('card_number', card_number) \
            .execute()

        if check.data:
            supabase.table('user_wishlists') \
                .delete() \
                .eq(col, identity['id']) \
                .eq('card_number', card_number) \
                .execute()
            statut = "retire"
        else:
            insert_data = {'card_number': card_number}
            insert_data[col] = identity['id']

            supabase.table('user_wishlists') \
                .insert(insert_data) \
                .execute()
            statut = "ajoute"

        return jsonify({"status": "success", "action": statut})
    except Exception as e:
        print(f"Erreur toggle_wishlist: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ROUTES DECKS (SUPABASE) ---
@app.route("/api/get_deck", methods=["GET"])
def api_get_deck():
    etat = charger_deck_actif_appareil()
    return jsonify(etat["deck"])

@app.route("/api/remove_from_deck", methods=["POST"])
def api_remove_from_deck():
    try:
        etat = charger_deck_actif_appareil()
        deck_memoire = etat["deck"]
        deck_nom = etat["nom"]

        donnees = request.get_json()
        id_carte = donnees.get("card_number")
        is_leader = donnees.get("is_leader", False)

        if is_leader:
            deck_memoire["leader"] = None
        else:
            for card in deck_memoire["cards"]:
                if card["card_number"] == id_carte:
                    if card["quantite_deck"] > 1:
                        card["quantite_deck"] -= 1
                    else:
                        deck_memoire["cards"].remove(card)
                    break

        sauvegarder_deck_actif_appareil(deck_nom, deck_memoire)

        if deck_nom:
            identity = get_user_identity()
            col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

            upsert_data = {
                'nom_deck': deck_nom,
                'structure_deck': deck_memoire,
            }
            upsert_data[col] = identity['id']

            supabase.table('user_decks').upsert(
                upsert_data,
                on_conflict=f"{col}, nom_deck"
            ).execute()

        return jsonify({"status": "success", "prix_total_deck": calculer_prix_deck_actuel(deck_memoire)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/save_deck', methods=['POST'])
@app.route('/sauvegarder_deck', methods=['POST'])
@app.route('/ta_route_de_sauvegarde_de_deck', methods=['POST'])
def sauvegarder_deck():
    try:
        data = request.get_json()
        identity = get_user_identity()
        col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

        nom_deck = data.get('nom_deck') or data.get('nom')
        structure = data.get('structure_deck') or data.get('deck')

        if not nom_deck:
            return jsonify({'status': 'error', 'message': 'Nom du deck manquant'}), 400

        sauvegarder_deck_actif_appareil(nom_deck, structure)

        check = supabase.table('user_decks') \
            .select('id') \
            .eq(col, identity['id']) \
            .eq('nom_deck', nom_deck) \
            .execute()

        if check.data:
            row_id = check.data[0]['id']
            supabase.table('user_decks').update({
                'structure_deck': structure
            }).eq('id', row_id).execute()
        else:
            insert_data = {
                'nom_deck': nom_deck,
                'structure_deck': structure,
            }
            insert_data[col] = identity['id']

            supabase.table('user_decks').insert(insert_data).execute()

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route("/supprimer_deck", methods=["POST"])
def supprimer_deck():
    try:
        donnees = request.get_json()
        nom_deck_a_supprimer = donnees.get("nom")
        identity = get_user_identity()
        col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

        supabase.table('user_decks').delete() \
            .eq(col, identity['id']) \
            .eq('nom_deck', nom_deck_a_supprimer) \
            .execute()

        etat = charger_deck_actif_appareil()
        if etat["nom"] == nom_deck_a_supprimer:
            sauvegarder_deck_actif_appareil(None, {"leader": None, "cards": []})

        return jsonify({"status": "success", "message": f"🗑️ Le deck '{nom_deck_a_supprimer}' a bien été supprimé !"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/load_specific_deck", methods=["POST"])
def api_load_specific_deck():
    try:
        donnees = request.get_json()
        nom_deck = donnees.get("nom")

        if not nom_deck:
            sauvegarder_deck_actif_appareil(None, {"leader": None, "cards": []})
            return jsonify({"status": "success", "nom_deck": None, "prix_total_deck": 0.0})

        _, tous_les_decks = charger_decks()

        if nom_deck in tous_les_decks:
            deck_memoire = tous_les_decks[nom_deck]
            sauvegarder_deck_actif_appareil(nom_deck, deck_memoire)
            return jsonify({"status": "success", "nom_deck": nom_deck, "prix_total_deck": calculer_prix_deck_actuel(deck_memoire)})
        return jsonify({"status": "error", "message": "Deck introuvable"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/add_to_deck", methods=["POST"])
def api_add_to_deck():
    try:
        etat = charger_deck_actif_appareil()
        deck_memoire = etat["deck"]
        deck_nom = etat["nom"]

        donnees = request.get_json()
        id_carte = donnees.get("card_number")
        nom_carte = donnees.get("name")
        is_leader = donnees.get("is_leader", False)
        is_alt = donnees.get("is_alternative", False)

        a_un_suffixe = any(f"_p{i}" in id_carte for i in range(1, 10))

        if a_un_suffixe:
            img_url = f"/static/{id_carte}.jpg"
        elif is_alt:
            img_url = f"/static/{id_carte}_p1.jpg"
        else:
            img_url = f"/static/{id_carte}.jpg"

        if is_leader:
            deck_memoire["leader"] = {
                "card_number": id_carte,
                "name": nom_carte,
                "image_url": img_url
            }
        else:
            carte_existante = next((c for c in deck_memoire["cards"] if c["card_number"] == id_carte), None)

            if carte_existante:
                if carte_existante["quantite_deck"] < 4:
                    carte_existante["quantite_deck"] += 1
                else:
                    return jsonify({"status": "error", "message": "Limite de 4 exemplaires atteinte !"})
            else:
                deck_memoire["cards"].append({
                    "card_number": id_carte,
                    "name": nom_carte,
                    "image_url": img_url,
                    "quantite_deck": 1
                })

        sauvegarder_deck_actif_appareil(deck_nom, deck_memoire)

        if deck_nom:
            identity = get_user_identity()
            col = 'user_id' if identity['type'] == 'user_id' else 'device_id'

            upsert_data = {
                'nom_deck': deck_nom,
                'structure_deck': deck_memoire,
            }
            upsert_data[col] = identity['id']

            supabase.table('user_decks').upsert(
                upsert_data,
                on_conflict=f"{col}, nom_deck"
            ).execute()

        return jsonify({"status": "success", "deck_actif": deck_nom, "prix_total_deck": calculer_prix_deck_actuel(deck_memoire)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get_deck_status", methods=["GET"])
def api_get_deck_status():
    etat = charger_deck_actif_appareil()
    return jsonify({
        "nom_deck": etat["nom"],
        "deck": etat["deck"],
        "prix_total_deck": calculer_prix_deck_actuel(etat["deck"])
    })

@app.route("/api/get_all_saved_deks_json")
def api_get_all_saved_decks_json():
    _, tous_les_decks = charger_decks()
    return jsonify(tous_les_decks)


# --- ROUTES DIVERSES ---
@app.route("/maj-sp")
def mettre_a_jour_sp():
    try:
        nom_du_fichier_json = 'cartes.json'
        if not os.path.exists(nom_du_fichier_json):
            return f"Erreur : Le fichier '{nom_du_fichier_json}' est introuvable."

        with open(nom_du_fichier_json, 'r', encoding='utf-8') as f:
            donnees = json.load(f)

        compteur = 0
        for carte in donnees:
            if carte.get("card_number") == "OP05-093":
                carte["card_number"] = "OP09-OP05-093"
                carte["serie"] = "OP09"
                compteur += 1

        if compteur > 0:
            with open(nom_du_fichier_json, 'w', encoding='utf-8') as f:
                json.dump(donnees, f, indent=4, ensure_ascii=False)
            return f"Succès ! {compteur} carte(s) mise(s) à jour."
        return "Carte introuvable."
    except Exception as e:
        return f"Erreur : {e}"

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js')

@app.route("/api/friends/add", methods=["POST"])
def add_friend():
    try:
        mon_pseudo = get_current_user()
        pseudo_ami = request.json.get("pseudo", "").strip()

        if not mon_pseudo:
            return jsonify({"status": "error", "message": "Vous devez être connecté."}), 401
        if not pseudo_ami:
            return jsonify({"status": "error", "message": "Veuillez entrer un pseudo."}), 400
        if mon_pseudo.lower() == pseudo_ami.lower():
            return jsonify({"status": "error", "message": "Vous ne pouvez pas vous ajouter vous-même."}), 400

        # Vérifier si une relation/demande existe déjà
        existant = supabase.table('amis').select('*').or_(
            f"and(user_id.eq.{mon_pseudo},friend_id.eq.{pseudo_ami}),and(user_id.eq.{pseudo_ami},friend_id.eq.{mon_pseudo})"
        ).execute()

        if existant.data:
            return jsonify({"status": "error", "message": "Une demande ou une amitié existe déjà avec cet utilisateur."}), 400

        # Insérer la demande
        supabase.table('amis').insert({
            "user_id": mon_pseudo,
            "friend_id": pseudo_ami,
            "statut": "en_attente"
        }).execute()

        return jsonify({"status": "success", "message": f"Demande d'ami envoyée à {pseudo_ami} !"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/friends/list", methods=["GET"])
def list_friends():
    try:
        mon_pseudo = get_current_user()
        if not mon_pseudo:
            return jsonify([])

        reponse = supabase.table('amis').select('*').eq('statut', 'accepte').or_(
            f"user_id.eq.{mon_pseudo},friend_id.eq.{mon_pseudo}"
        ).execute()

        pseudos_amis = []
        for row in reponse.data:
            ami_pseudo = row['friend_id'] if row['user_id'] == mon_pseudo else row['user_id']
            pseudos_amis.append(ami_pseudo)

        if not pseudos_amis:
            return jsonify([])

        _, donnees_json = charger_donnees()
        dict_prix = {c["card_number"]: float(c.get("prix") or 0.0) for c in donnees_json}

        collections = supabase.table('user_collections').select('user_id, card_number, quantite').in_('user_id', pseudos_amis).execute()

        valeurs_par_ami = {p: 0.0 for p in pseudos_amis}
        if collections.data:
            for row in collections.data:
                u_id = row['user_id']
                qte = row['quantite']
                prix = dict_prix.get(row['card_number'], 0.0)
                if u_id in valeurs_par_ami:
                    valeurs_par_ami[u_id] += qte * prix

        resultat = [
            {"pseudo": p, "valeur_collection": round(valeurs_par_ami[p], 2)}
            for p in pseudos_amis
        ]
        return jsonify(resultat)
    except Exception as e:
        return jsonify([])


@app.route("/api/friends/requests", methods=["GET"])
def list_friend_requests():
    """Récupère les demandes reçues ET envoyées en attente"""
    try:
        mon_pseudo = get_current_user()
        if not mon_pseudo:
            return jsonify({"recues": [], "envoyees": []})

        # Demandes reçues (qui m'attendent)
        recues_resp = supabase.table('amis').select('user_id').eq('friend_id', mon_pseudo).eq('statut', 'en_attente').execute()
        recues = [r['user_id'] for r in recues_resp.data] if recues_resp.data else []

        # Demandes envoyées (que j'ai transmises)
        envoyees_resp = supabase.table('amis').select('friend_id').eq('user_id', mon_pseudo).eq('statut', 'en_attente').execute()
        envoyees = [r['friend_id'] for r in envoyees_resp.data] if envoyees_resp.data else []

        return jsonify({"recues": recues, "envoyees": envoyees})
    except Exception as e:
        return jsonify({"recues": [], "envoyees": []})


@app.route("/api/friends/accept", methods=["POST"])
def accept_friend():
    try:
        mon_pseudo = get_current_user()
        if not mon_pseudo:
            return jsonify({"status": "error", "message": "Non connecté"}), 401

        demandeur = request.json.get("pseudo")
        supabase.table('amis').update({"statut": "accepte"}).eq("user_id", demandeur).eq("friend_id", mon_pseudo).execute()
        return jsonify({"status": "success", "message": f"Vous êtes désormais ami avec {demandeur} !"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/friends/decline", methods=["POST"])
def decline_friend():
    try:
        mon_pseudo = get_current_user()
        if not mon_pseudo:
            return jsonify({"status": "error", "message": "Non connecté"}), 401

        demandeur = request.json.get("pseudo")
        supabase.table('amis').delete().eq("user_id", demandeur).eq("friend_id", mon_pseudo).execute()
        return jsonify({"status": "success", "message": "Demande refusée."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/friends/remove", methods=["POST"])
def remove_friend():
    """Supprimer un ami de sa liste ou annuler une demande d'ami"""
    try:
        mon_pseudo = get_current_user()
        if not mon_pseudo:
            return jsonify({"status": "error", "message": "Non connecté"}), 401

        ami_pseudo = request.json.get("pseudo")
        if not ami_pseudo:
            return jsonify({"status": "error", "message": "Pseudo manquant"}), 400

        # Supprimer la relation dans les deux sens possibles
        supabase.table('amis').delete().or_(
            f"and(user_id.eq.{mon_pseudo},friend_id.eq.{ami_pseudo}),and(user_id.eq.{ami_pseudo},friend_id.eq.{mon_pseudo})"
        ).execute()

        return jsonify({"status": "success", "message": f"{ami_pseudo} a été retiré de vos amis."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ROUTE : VOIR LA COLLECTION D'UN AMI ---
@app.route("/ami/<pseudo>/collection")
def voir_collection_ami(pseudo):
    try:
        _, donnees_json = charger_donnees()
        _, tous_les_decks = charger_decks() # <-- Charger les decks

        reponse = supabase.table('user_collections').select('card_number, quantite').eq('user_id', pseudo).execute()
        dict_col = {row['card_number']: row['quantite'] for row in reponse.data} if reponse.data else {}

        liste_cartes = []
        for carte in donnees_json:
            qte = dict_col.get(carte.get("card_number"), 0)
            if qte > 0:
                c_copy = carte.copy()
                c_copy["quantite"] = qte
                formater_carte_image(c_copy)
                liste_cartes.append(c_copy)

        liste_cartes = trier_cartes(liste_cartes)
        total_prix = sum(c["quantite"] * c.get("prix", 0.0) for c in liste_cartes)

        return render_template(
            "index.html",
            cartes_python=liste_cartes,
            total_prix=total_prix,
            nom_de_la_serie=f"Collection de {pseudo}",
            decks_sauvegardes=tous_les_decks, # <-- Transmis au template
            mode_lecture_seule=True
        )
    except Exception as e:
        return f"Erreur : {e}"

if __name__ == "__main__":
    app.run(debug=True, port=5000)