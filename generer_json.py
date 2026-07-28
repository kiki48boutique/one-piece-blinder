import json
import os
import re

# Fusion définitive et corrigée de toute la collection OP01 (001 à 121)
donnees_brutes_completes = """
OP01-001Roronoa ZoroLeaderLeader
OP01-002Trafalgar LawLeaderLeader
OP01-003Monkey D. LuffyLeaderLeader
OP01-004UsoppRare (R)Character
OP01-005UtaRare (R)Character
OP01-006OtamaUncommon (UC)Character
OP01-007CaribouCommon (C)Character
OP01-008CavendishCommon (C)Character
OP01-009CarrotCommon (C)Character
OP01-010KomachiyoCommon (C)Character
OP01-011GordonUncommon (UC)Character
OP01-012SaiCommon (C)Character
OP01-013SanjiRare (R)Character
OP01-014JinbeUncommon (UC)Character
OP01-015Tony Tony ChopperUncommon (UC)Character
OP01-016NamiRare (R)Character
OP01-017Nico RobinRare (R)Character
OP01-018HajrudinCommon (C)Character
OP01-019BartolomeoCommon (C)Character
OP01-020HyogoroCommon (C)Character
OP01-021FrankyUncommon (UC)Character
OP01-022BrookUncommon (UC)Character
OP01-023MarcoCommon (C)Character
OP01-024Monkey D. LuffySuper Rare (SR)Character
OP01-025Roronoa ZoroSuper Rare (SR)Character
OP01-026Gum-Gum Fire-Fist Pistol Red HawkRare (R)Event
OP01-027Round TableCommon (C)Event
OP01-028Green Star RafflesiaCommon (C)Event
OP01-029Radical Beam!!Uncommon (UC)Event
OP01-030In Two Years (R)Event
OP01-031Kozuki OdenLeader (L)Leader
OP01-032Ashura DojiCommon (C)Character
OP01-033IzoUncommon (UC)Character
OP01-034InuarashiRare (R)Character
OP01-035OkikuUncommon (UC)Character
OP01-036OtsuruCommon (C)Character
OP01-037KawamatsuCommon (C)Character
OP01-038KanjuroCommon (C)Character
OP01-039KillerCommon (C)Character
OP01-040Kin'emonSuper Rare (SR)Character
OP01-041Kozuki MomonosukeUncommon (UC)Character
OP01-042KomurasakiCommon (C)Character
OP01-043ShinobuCommon (C)Character
OP01-044ShachiCommon (C)Character
OP01-045Jean BartCommon (C)Character
OP01-046DenjiroUncommon (UC)Character
OP01-047Trafalgar LawSuper Rare (SR)Character
OP01-048NekomamushiRare (R)Character
OP01-049BepoUncommon (UC)Character
OP01-050PenguinCommon (C)Character
OP01-051Eustass "Captain" KidSuper Rare (SR)Character
OP01-052RaizoCommon (C)Character
OP01-053WireCommon (C)Character
OP01-054X. DrakeUncommon (UC)Character
OP01-055You Can Be My Samurai!!Rare (R)Event
OP01-056Demon FaceCommon (C)Event
OP01-057Paradise WaterfallUncommon (UC)Event
OP01-058Punk GibsonRare (R)Event
OP01-059BE-BENG!!Common (C)Event
OP01-060Donquixote DoflamingoLeader (L)Leader
OP01-061KaidoLeader (L)Leader
OP01-062CrocodileLeader (L)Leader
OP01-063AlvidaCommon (C)Character
OP01-064Mr. 1 (Daz Bonez)Uncommon (UC)Character
OP01-065Mr. 2 Bon Clay (Bentham)Rare (R)Character
OP01-066Mr. 3 (Galdino)Common (C)Character
OP01-067CrocodileSuper Rare (SR)Character
OP01-068Gecko MoriaUncommon (UC)Character
OP01-069Caesar ClownCommon (C)Character
OP01-070Dracule MihawkSuper Rare (SR)Character
OP01-071SengokuCommon (C)Character
OP01-072TsuruCommon (C)Character
OP01-073Donquixote DoflamingoRare (R)Character
OP01-074Bartholomew KumaRare (R)Character
OP01-075PacifistaCommon (C)Character
OP01-076Bell-mèreUncommon (UC)Character
OP01-077PeronaUncommon (UC)Character
OP01-078Boa HancockSuper Rare (SR)Character
OP01-079Miss All SundayUncommon (UC)Character
OP01-080Miss Doublefinger (Zala)CCharacter
OP01-081MochaCCharacter
OP01-082MonetUCCharacter
OP01-083Mr. 1 (Daz Bonez)CCharacter
OP01-084Mr. 2 Bon Kurei (Bentham)RCharacter
OP01-085Mr. 3 (Galdino)CCharacter
OP01-086OverheatREvent
OP01-087Officer AgentsCEvent
OP01-088Desert SpadaUCEvent
OP01-089Crescent CutlassCEvent
OP01-090Baroque WorksUCEvent
OP01-091KingRLeaderLeader
OP01-092UrashimaCCharacter
OP01-093UltiUCCharacter
OP01-094KaidoSRCharacter
OP01-095KyoshiroCCharacter
OP01-096KingSRCharacter
OP01-097QueenRCharacter
OP01-098Kurozumi OrochiCCharacter
OP01-099Kurozumi SemimaruCCharacter
OP01-100Kurozumi HigurashiCCharacter
OP01-101SasakiCCharacter
OP01-102JackUCCharacter
OP01-103Scratchmen ApooCCharacter
OP01-104SpeedCCharacter
OP01-105Bao HuangCCharacter
OP01-106Basil HawkinsCCharacter
OP01-107BabanukiCCharacter
OP01-108Hitokiri KamazoUCCharacter
OP01-109Who's-WhoCCharacter
OP01-110FukurokujuCCharacter
OP01-111Black MariaUCCharacter
OP01-112Page OneUCCharacter
OP01-113HoledemCCharacter
OP01-114X.DrakeRCharacter
OP01-115Elephant's MarchCEvent
OP01-116Artificial Devil FruitCEvent
OP01-117Sheep's HornUCEvent
OP01-118Ulti-MortarREvent
OP01-119Thunder BaguaREvent
OP01-120ShanksSECCharacter
OP01-121YamatoSECCharacter
"""

traduction_rarete = {
    "Leader": "L", "Leader (L)": "L", "L": "L",
    "Super Rare (SR)": "SR", "SR": "SR",
    "Rare (R)": "R", "R": "R",
    "Uncommon (UC)": "UC", "UC": "UC",
    "Common (C)": "C", "C": "C",
    "Secret Rare (SEC)": "SEC", "SEC": "SEC"
}

base_cartes = []
numeros_ajoutes = set()

# Recherche et extraction regex de chaque carte
blocs = re.findall(r'(OP01-\d{3})(.*?)(?=OP01-\d{3}|$)', donnees_brutes_completes.replace('\n', ''))

for card_id, contenu in blocs:
    if card_id in numeros_ajoutes:
        continue

    # Extraction du Type
    type_carte = "Character"
    for t in ["Leader", "Character", "Event", "Stage"]:
        if contenu.endswith(t):
            type_carte = t
            contenu = contenu[:-len(t)]
            break

    # Extraction de la Rareté
    rarete_brute = "C"
    for r in sorted(traduction_rarete.keys(), key=len, reverse=True):
        if contenu.endswith(r):
            rarete_brute = r
            contenu = contenu[:-len(r)]
            break

    nom_personnage = contenu.strip()
    rarete_code = traduction_rarete.get(rarete_brute, "C")

    # Correction forcée demandée pour la 90
    index_num = int(card_id.split("-")[1])
    if index_num == 90:
        type_carte = "Event"

    # Attribution de la couleur officielle de la section
    elif 2 <= index_num <= 3:
        couleur = "Rouge/Vert"
    elif 4 <= index_num <= 30:
        couleur = "Rouge"
    elif 31 <= index_num <= 59:
        couleur = "Vert"
    elif 61 <= index_num <= 62:
        couleur = "Bleu/Violet"
    elif 63 <= index_num <= 90:
        couleur = "Bleu"
    elif index_num ==120:
        couleur = "Rouge"
    elif index_num ==121:
        couleur = "Vert"
    elif index_num ==60:
        couleur = "Blue"
    else:
        couleur = "Violet"

    base_cartes.append({
        "card_number": card_id,
        "name": nom_personnage,
        "rarity": rarete_code,
        "type": type_carte,
        "color": couleur,
        "serie": "OP01",
        "is_alternative": False,
        "quantite": 0,
        "prix": 1.50
    })
    numeros_ajoutes.add(card_id)

# Liste complète et vérifiée des versions alternatives (Alt Art) d'OP01
list_vrais_numeros_alt = [1, 2, 3, 8, 13, 16, 24, 25, 31, 34, 40, 47,48,51,60, 61, 62, 64,67, 70,73,77, 78, 91, 93, 94, 96,97,102,109, 120, 121]


# Génération des lignes de cartes alternatives (Alt)
for num_alt in list_vrais_numeros_alt:
    target_id = f"OP01-{num_alt:03d}"
    carte_reg = next((c for c in base_cartes if c["card_number"] == target_id and not c["is_alternative"]), None)
    if carte_reg:
        base_cartes.append({
            "card_number": carte_reg["card_number"],
            "name": carte_reg["name"],
            "rarity": carte_reg["rarity"],
            "type": carte_reg["type"],
            "color": carte_reg["color"],
            "serie": "OP01",
            "is_alternative": True,
            "quantite": 0,
            "prix": 25.00
        })

# --- AJOUT POUR LA SEC ALT 2 (SHANKS MANGA OP01-120_p2) ---
target_shanks = next((c for c in base_cartes if c["card_number"] == "OP01-120" and not c["is_alternative"]), None)
if target_shanks:
    base_cartes.append({
        "card_number": "OP01-120_p2",  # Identifiant unique pour différencier dans la base
        "name": target_shanks["name"],
        "rarity": target_shanks["rarity"],
        "type": target_shanks["type"],
        "color": target_shanks["color"],
        "serie": "OP01",
        "is_alternative": True,
        "quantite": 0,
        "prix": 800.00  # Prix d'une carte Manga SEC !
    })
# -----------------------------------------------------------

# Sauvegarde finale du fichier JSON (Ton code existant en dessous...)
dossier = os.path.dirname(os.path.abspath(__file__))
# Sauvegarde finale du fichier JSON
dossier = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(dossier, "cartes.json"), "w", encoding="utf-8") as f:
    json.dump(base_cartes, f, indent=4, ensure_ascii=False)

print(f"🚀 Succès ! Le fichier cartes.json contient désormais l'ensemble des {len(base_cartes)} cartes d'OP01.")