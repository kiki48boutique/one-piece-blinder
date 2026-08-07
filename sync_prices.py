import csv  # <-- AJOUTÉ ICI
import json
import os
import re
import urllib.request

# Dictionnaires de traduction globaux
TRADUCTION_RARETE = {
    "Leader": "L", "L": "L", "Super Rare": "SR", "SR": "SR", "Rare": "R", "R": "R",
    "Uncommon": "UC", "UC": "UC", "Common": "C", "C": "C", "Secret Rare": "SEC",
    "SEC": "SEC", "Special": "SP", "SP": "SP", "Treasure Rare": "TR", "TR": "TR"
}

TRADUCTION_TYPE = {"Leader": "Leader", "Character": "Character", "Event": "Event", "Stage": "Stage"}

TRADUCTION_COULEUR = {
    "Red": "Rouge", "Green": "Vert", "Blue": "Bleu", "Purple": "Violet", "Black": "Noir", "Yellow": "Jaune",
    "Green;Red": "Rouge/Vert", "Red;Green": "Rouge/Vert", "Blue;Purple": "Bleu/Violet", "Purple;Blue": "Bleu/Violet",
    "Green;Blue": "Vert/Bleu", "Blue;Green": "Vert/Bleu", "Black;Yellow": "Noir/Jaune", "Yellow;Black": "Noir/Jaune",
    "Red;Blue": "Rouge/Bleu", "Blue;Red": "Rouge/Bleu", "Red;Purple": "Rouge/Violet", "Purple;Red": "Rouge/Violet",
    "Green;Purple": "Vert/Violet", "Purple;Green": "Vert/Violet", "Green;Black": "Vert/Noir", "Black;Green": "Vert/Noir",
    "Blue;Black": "Bleu/Noir", "Black;Blue": "Bleu/Noir", "Blue;Yellow": "Bleu/Jaune", "Yellow;Blue": "Bleu/Jaune",
    "Purple;Yellow": "Violet/Jaune", "Yellow;Purple": "Violet/Jaune", "Green;Yellow": "Vert/Jaune", "Yellow;Green": "Vert/Jaune",
    "Black;Red": "Noir/Rouge", "Red;Black": "Noir/Rouge"
}

def normaliser_numero_carte(numero):
    if not numero: return ""
    numero = str(numero).strip().upper()
    if "-" in numero:
        prefixe, suffixe = numero.split("-", 1)
        try:
            chiffres = "".join([c for c in suffixe if c.isdigit()])
            if chiffres: return f"{prefixe}-{int(chiffres):03d}"
        except ValueError: pass
    else:
        chiffres = "".join([c for c in numero if c.isdigit()])
        if chiffres:
            return f"{int(chiffres):03d}"
    return numero

def synchroniser_toutes_les_series():
    dossier_actuel = os.path.dirname(os.path.abspath(__file__))
    chemin_json = os.path.join(dossier_actuel, "cartes.json")

    # --- SAUVEGARDE DES ANCIENNES DONNÉES (PRIX ET VARIATION) ---
    anciennes_cartes = {}
    if os.path.exists(chemin_json):
        try:
            with open(chemin_json, "r", encoding="utf-8") as f_ancien:
                donnees_anciennes = json.load(f_ancien)
                for c in donnees_anciennes:
                    cle = (c["card_number"], c.get("is_alternative", False))
                    anciennes_cartes[cle] = {
                        "prix": c.get("prix", 0.0),
                        "pourcentage": c.get("pourcentage_prix", 0.0),
                        "tendance": c.get("tendance_prix", "stable")
                    }
        except Exception as e:
            print(f"⚠️ Impossible de lire l'ancien fichier cartes.json : {e}")

    # Liste des séries
    CONFIG_SERIES = [
        ("Romance Dawn", "3188", "OP01"), ("Paramount War", "17698", "OP02"), ("Pillars of Strength", "22890", "OP03"),
        ("Kingdoms of Intrigue","23024","OP04"), ("Awakening of the New Era", "23213", "OP05"), ("Wings of the Captain", "23272", "OP06"),
        ("500 Years in the Future", "23387","OP07"), ("Two Legends", "23462", "OP08"), ("Emperors in the New World", "23589", "OP09"),
        ("Royal Blood", "23766","OP10"), ("A Fist of Divine Speed", "24241", "OP11"), ("Legacy of the Master", "24302", "OP12"),
        ("Carry on his Will", "24303", "OP13"), ("The Azure Sea's Seven", "24537", "OP14"), ("Adventure on Kami's Island", "24637", "OP15"),
        ("The Time of Battle", "24664", "OP16"), ("Extra Booster Memorial Collection", "23333", "EB01"),
        ("Extra Booster Anime 25th Collection", "23834", "EB02"), ("Extra Booster One Piece Heroines Edition", "24545", "EB03"),
        ("Premium Booster -The Best-", "23496", "PRB01"), ("Premium Booster -The Best-VOL 2", "24305", "PRB02"),
        ("Starter Deck 1 Straw Hat Crew", "3189", "ST01"),
        ("Starter Deck 2 Worst Generation", "3191", "ST02"),
        ("Starter Deck 3 The Seven Warlords of The Sea", "3192", "ST03"),
        ("Starter Deck 4 Animal Kingdom Pirates", "3190", "ST04"),
        ("Starter Deck 5 Film Edition", "17687", "ST05"),
        ("Starter Deck 6 Absolute Justice", "17699", "ST06"),
        ("Starter Deck 7 Big Mom Pirates", "22930", "ST07"),
        ("Starter Deck 8 Monkey.D.Luffy", "22956", "ST08"),
        ("Starter Deck 9 Yamato", "22957", "ST09"),
        ("Ultra Deck The Three Captains", "23243", "ST10"),
        ("Starter Deck 11 Uta", "23250", "ST11"),
        ("Starter Deck 12 Zoro and Sanji", "23348", "ST12"),
        ("Ultra Deck The Three Brothers", "23349", "ST13"),
        ("Starter Deck 14 3D2Y", "23489", "ST14"),
        ("Starter Deck 15 RED Edward.Newgate", "23490", "ST15"),
        ("Starter Deck 16 GREEN Uta", "23491", "ST16"),
        ("Starter Deck 17 BLUE Donquixote Doflamingo", "23492", "ST17"),
        ("Starter Deck 18 PURPLE Monkey.D.Luffy", "23493", "ST18"),
        ("Starter Deck 19 BLACK Smoker", "23494", "ST19"),
        ("Starter Deck 20 YELLOW Charlotte Katakuri", "23495", "ST20"),
        ("Starter Deck EX Gear 5", "23991", "ST21"),
        ("Starter Deck 22 Ace & Newgate", "24304", "ST22"),
        ("Starter Deck 23 RED Shanks", "24282", "ST23"),
        ("Starter Deck 24 GREEN Jewelry Bonney", "24283", "ST24"),
        ("Starter Deck 25 BLUE Buggy", "24284", "ST25"),
        ("Starter Deck 26 PURPLE BLACK Monkey.D.Luffy", "24285", "ST26"),
        ("Starter Deck 27 BLACK Marshall.D.Teach", "24286", "ST27"),
        ("Starter Deck 28 GREEN YELLOW Yamato", "24287", "ST28"),
        ("Starter Deck 29 Egghead", "24575", "ST29"),
        ("Starter Deck EX Luffy & Ace", "24678", "ST30"),
        ("One Piece Promotion Cards", "17675", "P"),
        ("One Piece Demo Deck Cards", "23907", "D"),
        ("Learn Together Deck Set", "24306", "LD")
    ]

    MAPPING_SERIES_DECK = {
        "StarterDeck1StrawHatCrewProductsAndPrices.csv": "ST01",
        "StarterDeck2WorstGenerationProductsAndPrices.csv": "ST02",
        "StarterDeck3TheSevenWarlordsofTheSeaProductsAndPrices.csv": "ST03",
        "StarterDeck4AnimalKingdomPiratesProductsAndPrices.csv": "ST04",
        "StarterDeck5FilmEditionProductsAndPrices.csv": "ST05",
        "StarterDeck6AbsoluteJusticeProductsAndPrices.csv": "ST06",
        "StarterDeck7BigMomPiratesProductsAndPrices.csv": "ST07",
        "StarterDeck8Monkey.D.LuffyProductsAndPrices.csv": "ST08",
        "StarterDeck9YamatoProductsAndPrices.csv": "ST09",
        "UltraDeckTheThreeCaptainsProductsAndPrices.csv": "ST10",
        "StarterDeck11UtaProductsAndPrices.csv": "ST11",
        "StarterDeck12ZoroandSanjiProductsAndPrices.csv": "ST12",
        "UltraDeckTheThreeBrothersProductsAndPrices.csv": "ST13",
        "StarterDeck143D2YProductsAndPrices.csv": "ST14",
        "StarterDeck15REDEdward.NewgateProductsAndPrices.csv": "ST15",
        "StarterDeck16GREENUtaProductsAndPrices.csv": "ST16",
        "StarterDeck17BLUEDonquixoteDoflamingoProductsAndPrices.csv": "ST17",
        "StarterDeck18PURPLEMonkey.D.LuffyProductsAndPrices.csv": "ST18",
        "StarterDeck19BLACKSmokerProductsAndPrices.csv": "ST19",
        "StarterDeck20YELLOWCharlotteKatakuriProductsAndPrices.csv": "ST20",
        "StarterDeckEXGear5ProductsAndPrices.csv": "ST21",
        "StarterDeck22Ace&NewgateProductsAndPrices.csv": "ST22",
        "StarterDeck23REDShanksProductsAndPrices.csv": "ST23",
        "StarterDeck24GREENJewelryBonneyProductsAndPrices.csv": "ST24",
        "StarterDeck25BLUEBuggyProductsAndPrices.csv": "ST25",
        "StarterDeck26PURPLEBLACKMonkey.D.LuffyProductsAndPrices.csv": "ST26",
        "StarterDeck27BLACKMarshall.D.TeachProductsAndPrices.csv": "ST27",
        "StarterDeck28GREENYELLOWYamatoProductsAndPrices.csv": "ST28",
        "StarterDeck29EggheadProductsAndPrices.csv": "ST29",
        "StarterDeckEXLuffy&AceProductsAndPrices.csv": "ST30",
        "OnePiecePromotionCardsProductsAndPrices.csv" : "P",
        "OnePieceDemoDeckCardsProductsAndPrices.csv" : "D",
        "LearnTogetherDeckSetProductsAndPrices.csv" : "LD"
    }

    SERIES_PROMO_AUTOMATIQUE = ["P","D","LD"]

    EXCLUSIONS_PAR_SERIE = {
        "D": [
            "D-OP01-001", "D-OP01-005", "D-OP01-011", "D-OP01-016", "D-OP01-021", "D-OP02-015",
            "D-P-001", "D-P-022", "D-P-080", "D-ST01-005", "D-ST01-006", "D-ST01-011",
            "D-ST01-014", "D-ST01-015", "D-ST01-017"
        ]
    }

    toutes_les_cartes_extraites = {}

    for nom_serie, id_tcg, code_serie in CONFIG_SERIES:
        nom_fichier_csv = f"{nom_serie.replace(' ', '')}ProductsAndPrices.csv"
        chemin_csv = os.path.join(dossier_actuel, nom_fichier_csv)
        url_csv = f"https://tcgcsv.com/tcgplayer/68/{id_tcg}/ProductsAndPrices.csv"

        try:
            requete = urllib.request.Request(url_csv, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(requete) as reponse:
                with open(chemin_csv, "wb") as f_csv: f_csv.write(reponse.read())
        except Exception:
            if not os.path.exists(chemin_csv): continue

        with open(chemin_csv, mode="r", encoding="utf-8", newline="") as f:
            for ligne in csv.DictReader(f):
                num_brut = ligne.get("extNumber")
                nom_produit = ligne.get("name", "").strip()

                if not num_brut and code_serie == "P":
                    match = re.search(r'(?:P|OP|ST|EB|PRB)\d*-\d+', nom_produit, re.IGNORECASE)
                    if match:
                        num_brut = match.group(0)

                if code_serie == "P" or code_serie == "LD":
                    mots_exclus = ["Booster Box", "Booster Case", "Display Box", "Sealed Case"]
                elif code_serie == "D":
                    mots_exclus = ["Promo"]
                else:
                    mots_exclus = ["Booster", "Box", "Case", "Pack", "Deck"]

                if not num_brut or any(x.lower() in nom_produit.lower() for x in mots_exclus):
                    continue

                num_normalise = normaliser_numero_carte(num_brut)
                serie_exacte = MAPPING_SERIES_DECK.get(nom_fichier_csv, code_serie)

                if code_serie.startswith("PRB") and not num_normalise.startswith(code_serie):
                    num_normalise = f"{code_serie}-{num_normalise}"
                elif serie_exacte.startswith("ST") and not num_normalise.startswith(serie_exacte):
                    num_normalise = f"{serie_exacte}-{num_normalise}"
                elif serie_exacte == "P" and not num_normalise.startswith("P-"):
                    num_normalise = f"P-{num_normalise}"
                elif serie_exacte == "LD" and not num_normalise.startswith("LD-"):
                    num_normalise = f"LD-{num_normalise}"
                elif serie_exacte == "D" and not num_normalise.startswith("D-"):
                    num_normalise = f"D-{num_normalise}"

                if code_serie in EXCLUSIONS_PAR_SERIE and num_normalise in EXCLUSIONS_PAR_SERIE[code_serie]:
                    continue

                est_alt = any(x in nom_produit for x in ["(Parallel)", "(Manga)", "Alternate Art", "(Special Art)", "(Treasure Rare)", "(Silver)", "(Gold)", "(SP)", "(Pirate Foil)", "(Full Art)", "(Jolly Roger Foil)"])
                rarete_brute = ligne.get("extRarity", "P" if code_serie == "P" else "C").strip()
                rarete_code = TRADUCTION_RARETE.get(rarete_brute, "P" if code_serie == "P" else "C")
                nom_produit_maj = nom_produit.upper()

                is_wanted = "BOUNTY" in nom_produit_maj or "WANTED" in nom_produit_maj
                is_sp_or_tr = "(SP)" in nom_produit_maj or "(TR)" in nom_produit_maj or "SPECIAL ART" in nom_produit_maj or "TREASURE RARE" in nom_produit_maj or rarete_code in ["SP", "TR"]

                if is_wanted or is_sp_or_tr:
                    nom_propre = nom_produit
                    rarete_code = "TR" if ("(TR)" in nom_produit_maj or "TREASURE" in nom_produit_maj) else "SP"
                    if not num_normalise.startswith(serie_exacte):
                        num_normalise = f"{serie_exacte}-{num_normalise}"
                elif code_serie in SERIES_PROMO_AUTOMATIQUE:
                    nom_propre = nom_produit
                else:
                    nom_propre = nom_produit.split("(")[0].strip()

                cle_carte = num_normalise
                if "RED SUPER ALTERNATE ART" in nom_produit_maj: cle_carte = f"{num_normalise}_p6"
                elif "SUPER ALTERNATE ART" in nom_produit_maj or "(MANGA)" in nom_produit_maj or "SPECIAL ART" in nom_produit_maj: cle_carte = f"{num_normalise}_p2"
                elif "(PARALLEL)" in nom_produit_maj : cle_carte = f"{num_normalise}_p1"
                elif "ALTERNATE ART" in nom_produit_maj and code_serie == "OP13": cle_carte = f"{num_normalise}_p7"
                elif "ALTERNATE ART" in nom_produit_maj: cle_carte = f"{num_normalise}_p1"
                elif is_wanted: cle_carte = f"{num_normalise}_p3"
                elif "(SILVER)" in nom_produit_maj: cle_carte = f"{num_normalise}_p4"
                elif "(GOLD)" in nom_produit_maj: cle_carte = f"{num_normalise}_p5"
                elif "(SP)" in nom_produit_maj: cle_carte = f"{num_normalise}_p6"
                elif "PIRATE FOIL" in nom_produit_maj: cle_carte = f"{num_normalise}_p4"
                elif "(FULL ART)" in nom_produit_maj: cle_carte = f"{num_normalise}_p2"
                elif "JOLLY ROGER FOIL" in nom_produit_maj: cle_carte = f"{num_normalise}_p3"

                if code_serie in SERIES_PROMO_AUTOMATIQUE:
                    compteur = 1
                    cle_temp = cle_carte
                    while (cle_temp, est_alt) in toutes_les_cartes_extraites:
                        compteur += 1
                        cle_temp = f"{cle_carte}_p{compteur}"
                    cle_carte = cle_temp

# --- CALCUL PRIX, TENDANCE ET POURCENTAGE ---
                try:
                    m_price = float(ligne.get("marketPrice")) if ligne.get("marketPrice") else None
                    mid_price = float(ligne.get("MidPrice")) if ligne.get("MidPrice") else None
                except:
                    m_price = None
                    mid_price = None

                prix_brut = m_price if (m_price and m_price > 0) else mid_price

                # Récupération de l'historique de la carte s'il existe
                donnees_anc = anciennes_cartes.get((cle_carte, est_alt), {})
                ancien_prix = donnees_anc.get("prix", 0.0)
                # ancien_pourcentage = donnees_anc.get("pourcentage", 0.0)
                # ancienne_tendance = donnees_anc.get("tendance", "stable")

                if prix_brut and prix_brut > 0:
                    prix_final = round(prix_brut * 0.88, 2)
                    disponible = True

                    if ancien_prix > 0:
                        if prix_final > ancien_prix:
                            pourcentage = round(((prix_final - ancien_prix) / ancien_prix) * 100, 1)
                            tendance = "hausse"
                        elif prix_final < ancien_prix:
                            pourcentage = round(((prix_final - ancien_prix) / ancien_prix) * 100, 1)
                            tendance = "baisse"
                        else:
                            pourcentage = 0
                            tendance = "stable"
                    else:
                        pourcentage = 0.0
                        tendance = "stable"
                else:
                    # 🔴 MODIFICATION ICI : si la carte n'est pas dispo
                    prix_final = ancien_prix
                    disponible = False
                    pourcentage = "-"
                    tendance = "pas dispo"

                toutes_les_cartes_extraites[(cle_carte, est_alt)] = {
                    "card_number": cle_carte,
                    "name": nom_propre,
                    "rarity": rarete_code,
                    "type": TRADUCTION_TYPE.get(ligne.get("extCardType", "Character").strip(), "Character"),
                    "color": TRADUCTION_COULEUR.get(ligne.get("extColor", "Red").strip(), "Rouge"),
                    "serie": serie_exacte,
                    "is_alternative": est_alt,
                    "quantite": 0,
                    "prix": prix_final,
                    "disponible": disponible,
                    "tendance_prix": tendance,
                    "pourcentage_prix": pourcentage
                }

    chemin_ajouts = os.path.join(dossier_actuel, "ajouts_manuels.json")
    if os.path.exists(chemin_ajouts):
        try:
            with open(chemin_ajouts, "r", encoding="utf-8") as f_ajouts:
                cartes_manuelles = json.load(f_ajouts)
                for carte in cartes_manuelles:
                    cle = (carte["card_number"], carte.get("is_alternative", False))
                    if "disponible" not in carte: carte["disponible"] = True
                    if "tendance_prix" not in carte: carte["tendance_prix"] = "stable"
                    if "pourcentage_prix" not in carte: carte["pourcentage_prix"] = 0.0
                    toutes_les_cartes_extraites[cle] = carte
            print(f"\n✍️  {len(cartes_manuelles)} cartes ajoutées/mises à jour manuellement depuis ajouts_manuels.json")
        except Exception as e:
            print(f"\n⚠️  Erreur lors de la lecture de ajouts_manuels.json : {e}")

    catalogue_global = list(toutes_les_cartes_extraites.values())
    catalogue_global.sort(key=lambda x: (x["serie"], x["card_number"], x["is_alternative"]))

    with open(chemin_json, "w", encoding="utf-8") as f:
        json.dump(catalogue_global, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Succès ! {len(catalogue_global)} cartes synchronisées.")

if __name__ == "__main__":
    synchroniser_toutes_les_series()