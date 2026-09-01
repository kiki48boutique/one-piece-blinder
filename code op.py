import json
import os
from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)

# 🎯 VARIABLES GLOBALES CENTRALISÉES
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
    dossier_actuel = os.path.dirname(os.path.abspath(__file__))
    chemin_collection = os.path.join(dossier_actuel, "collection.json")
    if os.path.exists(chemin_collection):
        with open(chemin_collection, "r", encoding="utf-8") as f:
            try: return chemin_collection, json.load(f)
            except: return chemin_collection, {}

    dict_migration = {}
    try:
        chemin_json = os.path.join(dossier_actuel, "cartes.json")
        if os.path.exists(chemin_json):
            with open(chemin_json, "r", encoding="utf-8") as f:
                for c in json.load(f):
                    q = c.get("quantite", 0)
                    if q > 0:
                        cle = f"{c['card_number']}_alt" if c.get("is_alternative") else c['card_number']
                        dict_migration[cle] = q
        with open(chemin_collection, "w", encoding="utf-8") as f:
            json.dump(dict_migration, f, indent=4, ensure_ascii=False)
    except:
        pass
    return chemin_collection, dict_migration

def appliquer_quantites_collection(donnees_json):
    """Injecte à la volée les quantités possédées depuis collection.json"""
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

def calculer_prix_deck_actuel():
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

        chemin_collection, dict_collection = charger_collection()

        cle_carte = f"{id_carte}_alt" if is_alt else id_carte
        quantite_actuelle = dict_collection.get(cle_carte, 0)

        if action == "plus":
            quantite_actuelle += 1
        elif action == "moins" and quantite_actuelle > 0:
            quantite_actuelle -= 1

        dict_collection[cle_carte] = quantite_actuelle

        with open(chemin_collection, "w", encoding="utf-8") as f:
            json.dump(dict_collection, f, indent=4, ensure_ascii=False)

        _, donnees_json = charger_donnees()
        appliquer_quantites_collection(donnees_json)

        valeur_totale = 0.0
        for carte in donnees_json:
            if titre_contexte in ["Toutes les Cartes", "Ma Collection (Cartes possédées)"]:
                valeur_totale += carte["quantite"] * carte.get("prix", 0.0)
            elif carte.get("serie", "").upper() == titre_contexte.upper():
                valeur_totale += carte["quantite"] * carte.get("prix", 0.0)

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

        a_un_suffixe = any(f"_p{i}" in id_carte for i in range(1, 10))

        if a_un_suffixe:
            img_url = f"/static/{id_carte}.jpg"
        elif is_alt:
            img_url = f"/static/{id_carte}_p1.jpg"
        else:
            img_url = f"/static/{id_carte}.jpg"

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

@app.route("/api/get_all_saved_decks_json")
def api_get_all_saved_decks_json():
    _, tous_les_decks = charger_decks()
    return jsonify(tous_les_decks)

@app.route("/maj-sp")
def mettre_a_jour_sp():
    try:
        chemin_json, donnees = charger_donnees()

        compteur = 0
        for carte in donnees:
            if carte.get("card_number") == "OP05-093":
                carte["card_number"] = "OP09-OP05-093"
                carte["serie"] = "OP09"
                compteur += 1

        if compteur > 0:
            with open(chemin_json, 'w', encoding='utf-8') as f:
                json.dump(donnees, f, indent=4, ensure_ascii=False)
            return f"Succès ! {compteur} carte(s) SP mise(s) à jour dans le JSON."
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