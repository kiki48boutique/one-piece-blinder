import json
import os
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

def get_device_json_path(prefixe_fichier):
    # 1. Lit en priorité le cookie généré par le navigateur
    device_id = request.cookies.get('op_device_id')

    # 2. Sinon, lit l'en-tête HTTP (requêtes fetch/JS)
    if not device_id:
        device_id = request.headers.get('X-Device-ID')

    # 3. Valeur par défaut si rien n'est trouvé
    if not device_id:
        device_id = 'defaut'

    os.makedirs('donnees_utilisateurs', exist_ok=True)
    return f"donnees_utilisateurs/{prefixe_fichier}_{device_id}.json"

def lire_json_appareil(prefixe_fichier, valeur_par_defaut):
    fichier = get_device_json_path(prefixe_fichier)
    if os.path.exists(fichier):
        with open(fichier, 'r', encoding='utf-8') as f:
            return json.load(f)
    return valeur_par_defaut

def sauvegarder_json_appareil(prefixe_fichier, donnees):
    fichier = get_device_json_path(prefixe_fichier)
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4)

# 🎯 VARIABLES GLOBALES CENTRALISÉES (Sans doublons dans le reste du code)
DECK_ACTUEL_NOM = None  # Nom du deck actif globalement
DECK_ACTUEL_MEMOIRE = {
    "leader": None,
    "cards": []
}

def charger_donnees():
    dossier_actuel = os.path.dirname(os.path.abspath(__file__))
    chemin_json = os.path.join(dossier_actuel, "cartes.json")
    with open(chemin_json, "r", encoding="utf-8") as f:
        return chemin_json, json.load(f)

def charger_decks():
    dossier_actuel = os.path.dirname(os.path.abspath(__file__))
    chemin_decks = os.path.join(dossier_actuel, "decks.json")
    if os.path.exists(chemin_decks):
        with open(chemin_decks, "r", encoding="utf-8") as f:
            try: return chemin_decks, json.load(f)
            except: return chemin_decks, {}
    return chemin_decks, {}

def charger_collection():
    # Renvoie un tuple (chemin, dictionnaire) pour rester cohérent avec les autres fonctions
    return get_device_json_path('collection'), lire_json_appareil('collection', {})

def appliquer_quantites_collection(donnees_json):
    """Injecte à la volée les quantités possédées depuis la collection de l'appareil"""
    _, dict_collection = charger_collection()
    for carte in donnees_json:
        id_carte = carte.get("card_number", "")
        is_alt = carte.get("is_alternative", False)
        cle = f"{id_carte}_alt" if is_alt else id_carte
        carte["quantite"] = dict_collection.get(cle, 0)

def trier_cartes(liste_cartes):
    def cle_de_tri(carte):
        # 1. Détection de la rareté SP ou TR
        rarete = str(carte.get("rarity", "")).strip().upper()
        est_special = 1 if rarete in ["SP", "TR", "SPECIAL", "TREASURE RARE"] else 0

        # 2. Nettoyage du numéro de carte (ex: "OP04-119" -> prefixe="OP04", suffixe="119")
        num_complet = str(carte.get("card_number", "")).strip().upper()

        # On extrait la partie numérique après le tiret pour trier les SP par leur vrai numéro
        chiffres = 999
        if "-" in num_complet:
            try:
                suffixe = num_complet.split("-")[1] # Ex: "004_P2"

                # CORRECTION : On ne garde que ce qui est avant le "_" (on isole "004")
                suffixe_propre = suffixe.split("_")[0]

                # On extrait les chiffres uniquement sur cette partie propre
                chiffres_extraits = "".join([c for c in suffixe_propre if c.isdigit()])
                if chiffres_extraits:
                    chiffres = int(chiffres_extraits)
            except:
                pass

        # 3. Version alternative
        est_alt = bool(carte.get("is_alternative", False))

        # Le tri se fait d'abord par : Est-ce une SP/TR ? (0=Non, 1=Oui)
        # Ensuite par son numéro chiffré nettoyé (4 au lieu de 42 !)
        # Enfin par sa version (classique avant alternative)
        return (est_special, chiffres, est_alt)

    liste_cartes.sort(key=cle_de_tri)
    return liste_cartes

def formater_carte_image(carte):
    if "quantite" not in carte: carte["quantite"] = 0
    try: carte["prix"] = float(carte.get("prix", 0.0))
    except: carte["prix"] = 0.0

    card_number = carte.get("card_number", "")

    # Vérifie si le numéro contient déjà explicitement un suffixe alternatif (_p1, _p2, ..., _p6)
    a_un_suffixe_alt = any(f"_p{i}" in card_number for i in range(1, 8))

    if a_un_suffixe_alt:
        # Si le numéro contient déjà _p1, _p2, etc., on l'utilise tel quel pour l'image
        carte["image_url"] = f"/static/{card_number}.jpg"
    elif carte.get("is_alternative"):
        # Si la carte est marquée comme alternative mais n'a pas de suffixe dans son numéro, on met _p1 par défaut
        carte["image_url"] = f"/static/{card_number}_p1.jpg"
    else:
        # Carte classique
        carte["image_url"] = f"/static/{card_number}.jpg"

    couleur_brute = carte.get("color", "unknown")
    if isinstance(couleur_brute, list):
        couleur_propre = "-".join([str(c).lower().strip() for c in couleur_brute])
    else:
        couleur_propre = str(couleur_brute).lower().replace("/", "-").replace(" ", "").strip()

    carte["couleur_propre"] = couleur_propre
    return carte

def calculer_prix_deck_actuel():
    """Calcul en direct basé sur les prix de cartes.json pour éviter les désynchronisations"""
    try:
        _, donnees_json = charger_donnees()
        dict_prix = {c["card_number"]: float(c.get("prix", 0.0)) for c in donnees_json}

        prix_total = 0.0
        if DECK_ACTUEL_MEMOIRE.get("leader"):
            id_leader = DECK_ACTUEL_MEMOIRE["leader"]["card_number"]
            prix_total += dict_prix.get(id_leader, 0.0)

        for c in DECK_ACTUEL_MEMOIRE.get("cards", []):
            prix_unitaire = dict_prix.get(c["card_number"], 0.0)
            prix_total += prix_unitaire * c["quantite_deck"]

        return round(prix_total, 2)
    except:
        return 0.0

@app.route("/")
def index():
    return render_template("accueil.html")

@app.route("/atelier_de_deck")
def atelier_de_deck():
    return render_template("deck.html")

@app.route("/decks")
def voir_les_decks():
    try:
        _, donnees_json = charger_donnees()
        _, tous_les_decks = charger_decks()

        appliquer_quantites_collection(donnees_json) # 🌟 Injection des quantités sauvées

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

        appliquer_quantites_collection(donnees_json) # 🌟 Injection des quantités sauvées

        liste_filtree = []
        for carte in donnees_json:
            formater_carte_image(carte)
            if mode == "toutes":
                liste_filtree.append(carte)
            elif mode == "possedees" and carte["quantite"] > 0:
                liste_filtree.append(carte)

        liste_filtree = trier_cartes(liste_filtree)
        total_prix = sum(c["quantite"] * c["prix"] for c in liste_filtree)
        titre = "Toutes les Cartes" if mode == "toutes" else "Ma Collection (Cartes possédées)"

        return render_template("index.html", cartes_python=liste_filtree, total_prix=total_prix, nom_de_la_serie=titre, decks_sauvegardes=tous_les_decks)
    except Exception as e:
        return f"Erreur : {e}"

@app.route("/serie/<nom_serie>")
def voir_serie(nom_serie):
    try:
        _, donnees_json = charger_donnees()
        _, tous_les_decks = charger_decks()

        appliquer_quantites_collection(donnees_json) # 🌟 Injection des quantités sauvées

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
    return jsonify(DECK_ACTUEL_MEMOIRE)

@app.route("/api/remove_from_deck", methods=["POST"])
def api_remove_from_deck():
    try:
        donnees = request.get_json()
        id_carte = donnees.get("card_number")
        is_leader = donnees.get("is_leader", False)

        if is_leader:
            DECK_ACTUEL_MEMOIRE["leader"] = None
        else:
            for card in DECK_ACTUEL_MEMOIRE["cards"]:
                if card["card_number"] == id_carte:
                    if card["quantite_deck"] > 1:
                        card["quantite_deck"] -= 1
                    else:
                        DECK_ACTUEL_MEMOIRE["cards"].remove(card)
                    break

        if DECK_ACTUEL_NOM:
            chemin_decks, tous_les_decks = charger_decks()
            tous_les_decks[DECK_ACTUEL_NOM] = DECK_ACTUEL_MEMOIRE
            with open(chemin_decks, "w", encoding="utf-8") as f:
                json.dump(tous_les_decks, f, indent=4, ensure_ascii=False)

        return jsonify({"status": "success", "prix_total_deck": calculer_prix_deck_actuel()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/sauvegarder_deck", methods=["POST"])
def sauvegarder_deck():
    try:
        donnees = request.get_json()
        nom_deck = donnees.get("nom")
        structure_deck = donnees.get("deck")
        chemin_decks, tous_les_decks = charger_decks()
        tous_les_decks[nom_deck] = structure_deck
        with open(chemin_decks, "w", encoding="utf-8") as f:
            json.dump(tous_les_decks, f, indent=4, ensure_ascii=False)
        return jsonify({"status": "success", "message": f"💾 Deck '{nom_deck}' enregistré avec succès !"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/modifier_quantite", methods=["POST"])
def modifier_quantite():
    try:
        donnees_recues = request.get_json()
        id_carte = donnees_recues.get("card_number")
        action = donnees_recues.get("action")
        titre_contexte = donnees_recues.get("contexte", "")
        is_alt = donnees_recues.get("is_alternative", False)

        # Extraction sécurisée avec le tuple (chemin, dict)
        chemin_collection, dict_collection = charger_collection()

        cle_carte = f"{id_carte}_alt" if is_alt else id_carte
        quantite_actuelle = dict_collection.get(cle_carte, 0)

        if action == "plus":
            quantite_actuelle += 1
        elif action == "moins" and quantite_actuelle > 0:
            quantite_actuelle -= 1

        dict_collection[cle_carte] = quantite_actuelle
        sauvegarder_json_appareil('collection', dict_collection)

        _, donnees_json = charger_donnees()
        appliquer_quantites_collection(donnees_json)

        valeur_totale = sum(
            carte["quantite"] * carte.get("prix", 0.0)
            for carte in donnees_json
            if titre_contexte in ["Toutes les Cartes", "Ma Collection (Cartes possédées)"]
            or carte.get("serie", "").upper() == titre_contexte.upper()
        )

        return jsonify({"status": "success", "nouvelle_quantite": quantite_actuelle, "nouveau_total_prix": round(valeur_totale, 2)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/supprimer_deck", methods=["POST"])
def supprimer_deck():
    try:
        donnees = request.get_json()
        nom_deck_a_supprimer = donnees.get("nom")
        chemin_decks, tous_les_decks = charger_decks()

        if nom_deck_a_supprimer in tous_les_decks:
            del tous_les_decks[nom_deck_a_supprimer]
            with open(chemin_decks, "w", encoding="utf-8") as f:
                json.dump(tous_les_decks, f, indent=4, ensure_ascii=False)
            return jsonify({"status": "success", "message": f"🗑️ Le deck '{nom_deck_a_supprimer}' a bien été supprimé !"})
        else:
            return jsonify({"status": "error", "message": "Deck introuvable."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/load_specific_deck", methods=["POST"])
def api_load_specific_deck():
    try:
        global DECK_ACTUEL_MEMOIRE, DECK_ACTUEL_NOM
        donnees = request.get_json()
        nom_deck = donnees.get("nom")

        if not nom_deck:
            DECK_ACTUEL_NOM = None
            DECK_ACTUEL_MEMOIRE = {"leader": None, "cards": []}
            return jsonify({"status": "success", "nom_deck": None, "prix_total_deck": 0.0})

        chemin_decks, tous_les_decks = charger_decks()

        if nom_deck in tous_les_decks:
            DECK_ACTUEL_MEMOIRE = tous_les_decks[nom_deck]
            DECK_ACTUEL_NOM = nom_deck
            return jsonify({"status": "success", "nom_deck": nom_deck, "prix_total_deck": calculer_prix_deck_actuel()})
        return jsonify({"status": "error", "message": "Deck introuvable"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/add_to_deck", methods=["POST"])
def api_add_to_deck():
    try:
        global DECK_ACTUEL_MEMOIRE, DECK_ACTUEL_NOM
        donnees = request.get_json()
        id_carte = donnees.get("card_number")
        nom_carte = donnees.get("name")
        is_leader = donnees.get("is_leader", False)
        is_alt = donnees.get("is_alternative", False)

        # --- CORRECTION DE L'URL DE L'IMAGE POUR LE DECK ---
        # On passe à range(1, 10) pour inclure _p7, _p8, _p9, etc.
        a_un_suffixe = any(f"_p{i}" in id_carte for i in range(1, 10))

        if a_un_suffixe:
            img_url = f"/static/{id_carte}.jpg"
        elif is_alt:
            img_url = f"/static/{id_carte}_p1.jpg"
        else:
            img_url = f"/static/{id_carte}.jpg"
        # ---------------------------------------------------

        if is_leader:
            DECK_ACTUEL_MEMOIRE["leader"] = {
                "card_number": id_carte,
                "name": nom_carte,
                "image_url": img_url
            }
        else:
            carte_existante = next((c for c in DECK_ACTUEL_MEMOIRE["cards"] if c["card_number"] == id_carte), None)

            if carte_existante:
                if carte_existante["quantite_deck"] < 4:
                    carte_existante["quantite_deck"] += 1
                else:
                    return jsonify({"status": "error", "message": "Limite de 4 exemplaires atteinte !"})
            else:
                DECK_ACTUEL_MEMOIRE["cards"].append({
                    "card_number": id_carte,
                    "name": nom_carte,
                    "image_url": img_url,
                    "quantite_deck": 1
                })

        if DECK_ACTUEL_NOM:
            chemin_decks, tous_les_decks = charger_decks()
            tous_les_decks[DECK_ACTUEL_NOM] = DECK_ACTUEL_MEMOIRE
            with open(chemin_decks, "w", encoding="utf-8") as f:
                json.dump(tous_les_decks, f, indent=4, ensure_ascii=False)

        return jsonify({"status": "success", "deck_actif": DECK_ACTUEL_NOM, "prix_total_deck": calculer_prix_deck_actuel()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get_deck_status", methods=["GET"])
def api_get_deck_status():
    return jsonify({
        "nom_deck": DECK_ACTUEL_NOM,
        "deck": DECK_ACTUEL_MEMOIRE,
        "prix_total_deck": calculer_prix_deck_actuel()
    })

@app.route("/api/get_all_saved_deks_json")
def api_get_all_saved_decks_json():
    _, tous_les_decks = charger_decks()
    return jsonify(tous_les_decks)

# ... Tout le reste de ton code app.py (tes fonctions, tes routes, etc.) ...

@app.route("/maj-sp")
def mettre_a_jour_sp():
    try:
        import json
        import os

        # 1. On définit le chemin vers ton fichier JSON (adapte 'cartes.json' si nécessaire)
        nom_du_fichier_json = 'cartes.json'

        if not os.path.exists(nom_du_fichier_json):
            return f"Erreur : Le fichier '{nom_du_fichier_json}' est introuvable à la racine."

        # 2. Lecture du fichier
        with open(nom_du_fichier_json, 'r', encoding='utf-8') as f:
            donnees = json.load(f)

        compteur = 0
        # 3. Modification de la carte SP cible
        for carte in donnees:
            if carte.get("card_number") == "OP05-093":
                carte["card_number"] = "OP09-OP05-093"
                carte["serie"] = "OP09"  # On la force dans OP09 pour la cibler
                compteur += 1

        # 4. Sauvegarde s'il y a eu un changement
        if compteur > 0:
            with open(nom_du_fichier_json, 'w', encoding='utf-8') as f:
                json.dump(donnees, f, indent=4, ensure_ascii=False)
            return f"Succès ! {compteur} carte(s) SP mise(s) à jour dans le JSON. Tu peux retourner sur ton classeur."
        else:
            return "La carte 'OP05-093' n'a pas été trouvée ou a déjà été modifiée."

    except Exception as e:
        return f"Une erreur est survenue lors de la mise à jour : {e}"


@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js')

if __name__ == "__main__":
    app.run(debug=False, port=5000)