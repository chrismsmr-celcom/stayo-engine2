# engine/fallback.py - Version corrigée

import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List


# ============================================================
# PERSONAS (copie locale pour fallback)
# ============================================================

PERSONAS = {
    "business": {
        "must_have": ["wifi haut débit", "business center", "salle de réunion", "calme"],
        "nice_to_have": ["restaurant", "bar", "parking"],
        "budget_multiplier": 1.5,
        "keywords": ["business", "affaires", "conférence", "réunion", "travail", "client", "pro", "wifi"],
        "vibe": "professionnel"
    },
    "romantic": {
        "must_have": ["chambre double", "vue", "restaurant"],
        "nice_to_have": ["spa", "bar", "balcon", "room service"],
        "budget_multiplier": 1.2,
        "keywords": ["romantique", "couple", "amoureux", "lune de miel", "anniversaire", "week-end", "escapade", "ma femme", "ma copine", "mon mari", "mon copain"],
        "vibe": "romantique"
    },
    "family": {
        "must_have": ["chambre familiale", "parking", "petit déjeuner"],
        "nice_to_have": ["piscine", "club enfants", "restaurant", "cuisine", "living room"],
        "budget_multiplier": 0.8,
        "keywords": ["famille", "enfant", "enfants", "familial", "bébé", "maman", "papa", "frère", "sœur", "parents"],
        "vibe": "familial"
    },
    "backpacker": {
        "must_have": ["wifi gratuit", "bagagerie", "cuisine partagée"],
        "nice_to_have": ["ambiance sociale", "bar", "terrasse"],
        "budget_multiplier": 0.5,
        "keywords": ["backpacker", "auberge", "jeunesse", "pas cher", "budget", "solo", "voyageur solo"],
        "vibe": "décontracté"
    },
    "luxury": {
        "must_have": ["concierge", "suite", "restaurant gastronomique"],
        "nice_to_have": ["spa", "piscine", "vue", "butler", "limousine"],
        "budget_multiplier": 2.5,
        "keywords": ["luxe", "luxury", "5 étoiles", "palace", "premium", "vip", "suite"],
        "vibe": "luxueux"
    }
}


# ============================================================
# FONCTIONS D'EXTRACTION
# ============================================================

def extract_amenities(text: str) -> List[str]:
    """Extrait les équipements souhaités d'un texte"""
    amenities_keywords = {
        "wifi": ["wifi", "internet", "connexion"],
        "piscine": ["piscine", "pool", "bassin"],
        "spa": ["spa", "bien-être", "massage", "sauna", "jacuzzi"],
        "restaurant": ["restaurant", "gastronomique", "dîner", "brasserie"],
        "parking": ["parking", "stationnement", "garage"],
        "vue": ["vue", "balcon", "terrasse", "panorama"],
        "calme": ["calme", "silencieux", "tranquille"],
        "climatisation": ["climatisation", "air conditionné", "clim"],
        "petit-déjeuner": ["petit-déjeuner", "breakfast", "brunch", "pdj"],
        "business center": ["business center", "salle de réunion", "coworking"],
        "club enfants": ["club enfants", "kids club", "children"],
        "cuisine": ["cuisine", "kitchen", "appartement"],
        "concierge": ["concierge", "butler", "service"]
    }
    
    text_lower = text.lower()
    return [
        amenity 
        for amenity, keywords in amenities_keywords.items() 
        if any(kw in text_lower for kw in keywords)
    ]


def extract_dates_fallback(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Extrait les dates d'une requête sans API"""
    current_year = str(datetime.now().year)
    
    months = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
    }
    
    # Format: "du 25 au 30 juillet 2026"
    match = re.search(r'du\s+(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})?\s+au\s+(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})?', query)
    if match:
        d1, m1, y1, d2, m2, y2 = match.groups()
        y1 = y1 or current_year
        y2 = y2 or y1 or current_year
        if m1 in months and m2 in months:
            return f"{y1}-{months[m1]}-{d1.zfill(2)}", f"{y2}-{months[m2]}-{d2.zfill(2)}"
    
    # Format: "25 au 30 juillet"
    match = re.search(r'(\d{1,2})\s+au\s+(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})?', query)
    if match:
        d1, d2, month, year = match.groups()
        year = year or current_year
        if month in months:
            return f"{year}-{months[month]}-{d1.zfill(2)}", f"{year}-{months[month]}-{d2.zfill(2)}"
    
    return None, None


# ✅ CORRECTION : run_basic_analysis ne prend qu'un seul argument
def run_basic_analysis(query: str) -> Dict[str, Any]:
    """
    Plan de secours local (100% offline)
    Aucune dépendance réseau externe
    """
    query_lower = query.lower()
    
    # Détection du persona
    detected_persona = "leisure"
    for persona, config in PERSONAS.items():
        if any(kw in query_lower for kw in config["keywords"]):
            detected_persona = persona
            break
    
    p_config = PERSONAS.get(detected_persona, PERSONAS["leisure"])
    
    # Extraction des données
    checkin, checkout = extract_dates_fallback(query_lower)
    custom_amenities = extract_amenities(query)
    
    # Détection des nombres
    adults = 2
    adult_match = re.search(r'(\d+)\s*(adulte|adultes|personne|personnes|pax)', query_lower)
    if adult_match:
        adults = int(adult_match.group(1))
    
    children = 0
    child_matches = re.findall(r'(\d+)\s*(enfant|enfants|ans)', query_lower)
    if child_matches:
        children = sum(int(m[0]) for m in child_matches)
    
    rooms = 1
    room_match = re.search(r'(\d+)\s*(chambre|chambres)', query_lower)
    if room_match:
        rooms = int(room_match.group(1))
    
    # Budget
    budget = None
    budget_match = re.search(r'(\d+)\s*[€$£]', query_lower)
    if budget_match:
        budget = int(budget_match.group(1))
    
    # Destination (fallback limité)
    destination = "Paris"
    area = None
    
    known_places = {
        "bercy": "Paris", "defense": "Paris", "montmartre": "Paris",
        "tour eiffel": "Paris", "champs elysees": "Paris", "louvre": "Paris",
        "notre dame": "Paris", "bastille": "Paris", "opera": "Paris",
        "saint germain": "Paris", "marais": "Paris"
    }
    
    for place, city in known_places.items():
        if place in query_lower:
            destination = city
            area = place.capitalize()
            break
    
    # Construction du résultat
    default_budget = 250 * p_config.get("budget_multiplier", 1)
    must_have = list(set(p_config["must_have"] + custom_amenities))
    
    return {
        "trip_type": detected_persona,
        "destination": destination,
        "area": area,
        "budget": budget or round(default_budget),
        "currency": "EUR",
        "must_have": must_have,
        "nice_to_have": p_config["nice_to_have"].copy(),
        "adults": adults,
        "children": children,
        "rooms": rooms,
        "vibe": p_config.get("vibe", "confort"),
        "checkin": checkin or "",
        "checkout": checkout or "",
        "place_description": f"{area or destination} - Mode Dégradé"
    }
