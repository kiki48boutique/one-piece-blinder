import csv
import json
import os

dossier = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(dossier, "cardmarket_prices.json")
csv_path = os.path.join(dossier, "cardmarket_singles.csv")

print("--- DIAGNOSTIC CARDMARKET ---")

# TEST 1 : JSON
if os.path.exists(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        contenu = f.read()
        if "priceGuides" in contenu and not contenu.strip().startswith("{"):
            contenu = "{" + contenu[contenu.find('"priceGuides"'):]
            if not contenu.strip().endswith("}"): contenu += "}"
        try:
            data = json.loads(contenu)
            print(f"✅ JSON lu avec succès : {len(data.get('priceGuides', []))} prix trouvés.")
        except Exception as e:
            print(f"❌ Erreur de lecture du JSON : {e}")
else:
    print("❌ Fichier cardmarket_prices.json INTROUVABLE.")

# TEST 2 : CSV
if os.path.exists(csv_path):
    with open(csv_path, "r", encoding="utf-8") as f:
        # On lit juste la première ligne pour voir les noms des colonnes
        premiere_ligne = f.readline().strip()
        print(f"✅ CSV trouvé. Voici les colonnes : {premiere_ligne}")
else:
    print("❌ Fichier cardmarket_singles.csv INTROUVABLE (Peut-être l'avez-vous nommé 'guide_product.csv' ?)")