import json
import os
from flask import Flask, jsonify, render_template, request
from supabase import create_client

# Valeurs de secours pour ton PC local si les variables d'environnement n'existent pas
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kbjdxxrryvvnahcnsjys.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "COLLER_TA_CLE_ANON_PUBLIC_ICI")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)


def get_device_json_path(prefixe_fichier):
    device_id = request.cookies.get('op_device_id')
    if not device_id:
        device_id = request.headers.get('X-Device-ID')
    if not device_id:
        device_id = 'defaut'

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

def charger_donnees():
    dossier_actuel = os.path.dirname(os.path.abspath(__file__))
    chemin_json = os.path.join(dossier_actuel, "cartes.json")
    with open(chemin_json, "r", encoding="utf-8") as f:
        return chemin_json, json.load(f)

def charger_decks():
    return get_device_json_path('decks'), lire_json_appareil('decks', {})

def charger_collection():
    return get_device_json_path('collection'), lire_json_appareil('collection', {})

def charger_wishlist():
    return get_device_json_path('wishlist'), lire_json_appareil('wishlist', [])

def sauvegarder_wishlist(liste_wishlist):
    sauvegarder_json_appareil('wishlist', liste_wishlist)

def appliquer_wishlist(donnees_json):
    _, liste_wishlist = charger_wishlist()
    for carte in donnees_json:
        carte["in_wishlist"] = carte.get("card_number") in liste_wishlist

def charger_deck_actif_appareil():
    return lire_json_appareil('deck_actif', {"nom": None, "deck": {"leader": None, "cards": []}})

def sauvegarder_deck_actif_appareil(nom, deck):
    sauvegarder_json_appareil('deck_actif', {"nom": nom, "deck": deck})

def appliquer_quantites_collection(donnees_json):
    _, dict_collection = charger_collection()
    for carte in donnees_json:
        id_carte = carte.get("card_number", "")
        is_alt = carte.get("is_alternative", False)
        cle = f"{id_carte}_alt" if is_alt else id_carte
        carte["quantite"] = dict_collection.get(cle, 0)

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

# 🌟 ROUTE ACCUEIL AVEC CALCUL DYNAMIQUE DE VOS SÉRIES
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
            _, tous_les_decks = charger_decks()
            tous_les_decks[deck_nom] = deck_memoire
            sauvegarder_json_appareil('decks', tous_les_decks)

        return jsonify({"status": "success", "prix_total_deck": calculer_prix_deck_actuel(deck_memoire)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/sauvegarder_deck", methods=["POST"])
def sauvegarder_deck():
    try:
        donnees = request.get_json()
        nom_deck = donnees.get("nom")
        structure_deck = donnees.get("deck")

        _, tous_les_decks = charger_decks()
        tous_les_decks[nom_deck] = structure_deck

        sauvegarder_json_appareil('decks', tous_les_decks)
        sauvegarder_deck_actif_appareil(nom_deck, structure_deck)

        return jsonify({"status": "success", "message": f"💾 Deck '{nom_deck}' enregistré avec succès !"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/modifier_quantite', methods=['POST'])
def modifier_quantite():
    data = request.get_json()
    device_id = request.headers.get('X-Device-ID', 'default_device')
    card_number = data.get('card_number')
    action = data.get('action') # 'plus' ou 'moins'

    # 1. Récupérer la quantité actuelle pour CET appareil
    reponse = supabase.table('user_collections') \
        .select('quantite') \
        .eq('device_id', device_id) \
        .eq('card_number', card_number) \
        .execute()

    qty_actuelle = reponse.data[0]['quantite'] if reponse.data else 0
    nouvelle_qty = max(0, qty_actuelle + 1 if action == 'plus' else qty_actuelle - 1)

    # 2. Sauvegarder dans Supabase
    supabase.table('user_collections').upsert({
        'device_id': device_id,
        'card_number': card_number,
        'quantite': nouvelle_qty
    }).execute()

    return jsonify({'status': 'success', 'nouvelle_quantite': nouvelle_qty})

@app.route("/supprimer_deck", methods=["POST"])
def supprimer_deck():
    try:
        donnees = request.get_json()
        nom_deck_a_supprimer = donnees.get("nom")
        _, tous_les_decks = charger_decks()

        if nom_deck_a_supprimer in tous_les_decks:
            del tous_les_decks[nom_deck_a_supprimer]
            sauvegarder_json_appareil('decks', tous_les_decks)

            etat = charger_deck_actif_appareil()
            if etat["nom"] == nom_deck_a_supprimer:
                sauvegarder_deck_actif_appareil(None, {"leader": None, "cards": []})

            return jsonify({"status": "success", "message": f"🗑️ Le deck '{nom_deck_a_supprimer}' a bien été supprimé !"})
        else:
            return jsonify({"status": "error", "message": "Deck introuvable."}), 404
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
            _, tous_les_decks = charger_decks()
            tous_les_decks[deck_nom] = deck_memoire
            sauvegarder_json_appareil('decks', tous_les_decks)

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

@app.route("/api/toggle_wishlist", methods=["POST"])
def toggle_wishlist():
    try:
        donnees = request.get_json()
        id_carte = donnees.get("card_number")

        _, liste_wishlist = charger_wishlist()

        if id_carte in liste_wishlist:
            liste_wishlist.remove(id_carte)
            statut = "retire"
        else:
            liste_wishlist.append(id_carte)
            statut = "ajoute"

        sauvegarder_wishlist(liste_wishlist)
        return jsonify({"status": "success", "action": statut})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, port=5000)