"""
Intent Engine — Compréhension de la requête voyageur
Version 3.0 - VRAIE intelligence
"""

import json
import os
import re
import httpx
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# ============================================================
# BASE DE CONNAISSANCES
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

CITY_KNOWLEDGE = {
    "paris": {
        "budget_min": 150,
        "budget_avg": 250,
        "family_areas": ["15ème", "16ème", "banlieue"],
        "business_areas": ["8ème", "9ème", "La Défense"],
        "romantic_areas": ["Saint-Germain", "Montmartre", "Marais"],
        "backpacker_areas": ["10ème", "11ème", "Belleville"],
        "lat": 48.8566,
        "lng": 2.3522
    },
    "londres": {
        "budget_min": 200,
        "budget_avg": 350,
        "family_areas": ["Kensington", "Camden", "Greenwich"],
        "business_areas": ["City", "Canary Wharf", "Westminster"],
        "romantic_areas": ["Notting Hill", "Covent Garden", "South Bank"],
        "backpacker_areas": ["Shoreditch", "Brixton", "Camden"],
        "lat": 51.5074,
        "lng": -0.1278
    },
    "venise": {
        "budget_min": 180,
        "budget_avg": 300,
        "family_areas": ["Cannaregio", "Castello"],
        "business_areas": ["San Marco", "Piazzale Roma"],
        "romantic_areas": ["San Marco", "Dorsoduro", "Giudecca"],
        "backpacker_areas": ["Cannaregio", "Santa Croce"],
        "lat": 45.4408,
        "lng": 12.3155
    }
}


async def parse_intent(query: str, traveler_id: str = None) -> Dict[str, Any]:
    """Analyse la requête avec intelligence"""
    
    # ===== 1. Essayer DeepSeek (IA) =====
    if DEEPSEEK_KEY:
        try:
            result = await _analyze_with_deepseek(query)
            if result:
                logger.info(f"🧠 DeepSeek: {result}")
                return _enrich_with_knowledge(result, query)
        except Exception as e:
            logger.warning(f"DeepSeek error: {e}")
    
    # ===== 2. Fallback: analyse avancée =====
    return _analyze_advanced(query)


async def _analyze_with_deepseek(query: str) -> Dict[str, Any]:
    """Analyse avec DeepSeek - prompt amélioré"""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": """Tu es un agent de voyage expert. Analyse la requête et retourne un JSON.

RÈGLES OBLIGATOIRES:
1. trip_type: business|romantic|family|backpacker|luxury|leisure
2. destination: ville principale
3. budget: montant en euros (estimation réaliste)
4. must_have: liste des équipements ESSENTIELS (max 5)
5. nice_to_have: liste des équipements SOUHAITABLES (max 5)
6. adults: nombre d'adultes (défaut: 2)
7. children: nombre d'enfants (défaut: 0)
8. rooms: nombre de chambres nécessaires
9. vibe: luxe|confort|budget|design|familial|romantique
10. date_range: [checkin, checkout] au format YYYY-MM-DD

EXEMPLE:
Requête: "Famille nombreuse à Paris 350€ du 25 au 30 juillet"
Réponse:
{
  "trip_type": "family",
  "destination": "Paris",
  "budget": 350,
  "must_have": ["piscine", "chambre familiale", "petit déjeuner", "parking"],
  "nice_to_have": ["club enfants", "restaurant", "cuisine"],
  "adults": 2,
  "children": 4,
  "rooms": 2,
  "vibe": "familial",
  "date_range": ["2026-07-25", "2026-07-30"]
}

Réponds UNIQUEMENT avec le JSON."""
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 800
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"DeepSeek error: {response.status_code}")
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["raw_query"] = query
            return result
        
        raise Exception("No JSON found")


def _analyze_advanced(query: str) -> Dict[str, Any]:
    """Analyse avancée sans API"""
    query_lower = query.lower()
    
    # ===== 1. Détection du persona =====
    detected_persona = "leisure"
    confidence = 0
    
    for persona, config in PERSONAS.items():
        for keyword in config["keywords"]:
            if keyword in query_lower:
                detected_persona = persona
                confidence += 1
                break
    
    # Si plusieurs personas détectés, prendre le plus pertinent
    if confidence > 1:
        # Priorité: family > business > romantic > luxury > backpacker
        priority = ["family", "business", "romantic", "luxury", "backpacker"]
        for p in priority:
            if p in query_lower:
                detected_persona = p
                break
    
    # ===== 2. Détection des nombres =====
    adults = 2
    children = 0
    rooms = 1
    
    # Adultes
    adult_patterns = [
        r'(\d+)\s*(adulte|adultes)',
        r'(\d+)\s*(personne|personnes|pax)'
    ]
    for pattern in adult_patterns:
        match = re.search(pattern, query_lower)
        if match:
            adults = int(match.group(1))
            break
    
    # Enfants
    child_patterns = [
        r'(\d+)\s*(enfant|enfants)',
        r'(\d+)\s*(ans)\s*(?!adulte)',
        r'(\d+)\s*(bébé|bébés|nouveau-né)'
    ]
    child_ages = []
    for pattern in child_patterns:
        matches = re.findall(pattern, query_lower)
        for match in matches:
            if isinstance(match, tuple):
                children += int(match[0])
                child_ages.append(int(match[0]))
            else:
                children += int(match)
    
    # Chambres
    room_match = re.search(r'(\d+)\s*(chambre|chambres)', query_lower)
    if room_match:
        rooms = int(room_match.group(1))
    
    # ===== 3. Détection du budget =====
    budget = None
    budget_patterns = [
        r'(\d+)\s*[€$£]',
        r'(\d+)\s*(euros|euro|dollars|dollar)',
        r'budget\s*de\s*(\d+)',
        r'(\d+)\s*(euros?|€)'
    ]
    for pattern in budget_patterns:
        match = re.search(pattern, query_lower)
        if match:
            budget = int(match.group(1))
            break
    
    # ===== 4. Détection de la destination =====
    destination = "Paris"
    city_data = CITY_KNOWLEDGE["paris"]
    
    for city, data in CITY_KNOWLEDGE.items():
        if city in query_lower:
            destination = city.capitalize()
            city_data = data
            break
    
    # ===== 5. Détection des dates =====
    checkin, checkout = _extract_dates(query_lower)
    
    # ===== 6. Détermination des must_have =====
    persona_config = PERSONAS.get(detected_persona, PERSONAS["leisure"])
    must_have = persona_config["must_have"].copy()
    nice_to_have = persona_config["nice_to_have"].copy()
    
    # Ajouter les équipements spécifiques mentionnés
    amenities_keywords = {
        "wifi": ["wifi", "internet", "connexion"],
        "piscine": ["piscine", "pool", "bassin"],
        "spa": ["spa", "bien-être", "massage", "sauna", "jacuzzi"],
        "restaurant": ["restaurant", "gastronomique", "dîner", "brasserie"],
        "parking": ["parking", "stationnement", "garage"],
        "vue": ["vue", "balcon", "terrasse", "panorama"],
        "calme": ["calme", "silencieux", "tranquille"],
        "climatisation": ["climatisation", "air conditionné", "clim"],
        "petit déjeuner": ["petit-déjeuner", "breakfast", "brunch", "pdj"],
        "business center": ["business center", "salle de réunion", "coworking"],
        "club enfants": ["club enfants", "kids club", "children"],
        "cuisine": ["cuisine", "kitchen", "appartement"],
        "concierge": ["concierge", "butler", "service"]
    }
    
    for amenity, keywords in amenities_keywords.items():
        if any(kw in query_lower for kw in keywords):
            if amenity not in must_have:
                must_have.append(amenity)
    
    # ===== 7. Ajustement pour les familles =====
    if detected_persona == "family" and rooms == 1 and children > 0:
        rooms = 2  # Par défaut 2 chambres pour une famille
    
    # ===== 8. Construction du résultat =====
    result = {
        "trip_type": detected_persona,
        "destination": destination,
        "budget": budget or (city_data.get("budget_avg", 250) * PERSONAS.get(detected_persona, PERSONAS["leisure"]).get("budget_multiplier", 1)),
        "currency": "EUR",
        "lat": city_data.get("lat", 48.8566),
        "lng": city_data.get("lng", 2.3522),
        "must_have": must_have,
        "nice_to_have": nice_to_have,
        "adults": adults,
        "children": children,
        "rooms": rooms,
        "vibe": persona_config.get("vibe", "confort"),
        "checkin": checkin or "",
        "checkout": checkout or "",
        "raw_query": query,
        "persona_confidence": confidence
    }
    
    logger.info(f"🧠 Analyse avancée: {result}")
    return result


def _extract_dates(query: str):
    """Extrait les dates d'une requête"""
    checkin = None
    checkout = None
    
    months = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
    }
    
    # Format: "du 25 au 30 juillet 2026"
    match = re.search(r'du\s+(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})?\s+au\s+(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})?', query)
    if match:
        day_in, month_in, year_in, day_out, month_out, year_out = match.groups()
        year_in = year_in or "2026"
        year_out = year_out or year_in
        checkin = f"{year_in}-{months[month_in]}-{day_in.zfill(2)}"
        checkout = f"{year_out}-{months[month_out]}-{day_out.zfill(2)}"
        return checkin, checkout
    
    # Format: "25 au 30 juillet"
    match = re.search(r'(\d{1,2})\s+au\s+(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})?', query)
    if match:
        day_in, day_out, month, year = match.groups()
        year = year or "2026"
        checkin = f"{year}-{months[month]}-{day_in.zfill(2)}"
        checkout = f"{year}-{months[month]}-{day_out.zfill(2)}"
        return checkin, checkout
    
    # Format: "25-30 juillet"
    match = re.search(r'(\d{1,2})[-–](\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})?', query)
    if match:
        day_in, day_out, month, year = match.groups()
        year = year or "2026"
        checkin = f"{year}-{months[month]}-{day_in.zfill(2)}"
        checkout = f"{year}-{months[month]}-{day_out.zfill(2)}"
        return checkin, checkout
    
    return None, None


def _enrich_with_knowledge(result: Dict, query: str) -> Dict:
    """Enrichit le résultat avec la base de connaissances"""
    destination = result.get("destination", "Paris").lower()
    city_data = CITY_KNOWLEDGE.get(destination, CITY_KNOWLEDGE["paris"])
    
    # Ajouter les coordonnées
    if "lat" not in result:
        result["lat"] = city_data.get("lat", 48.8566)
    if "lng" not in result:
        result["lng"] = city_data.get("lng", 2.3522)
    
    # Ajouter les zones recommandées
    trip_type = result.get("trip_type", "leisure")
    if trip_type == "family":
        result["recommended_areas"] = city_data.get("family_areas", [])
    elif trip_type == "business":
        result["recommended_areas"] = city_data.get("business_areas", [])
    elif trip_type == "romantic":
        result["recommended_areas"] = city_data.get("romantic_areas", [])
    elif trip_type == "backpacker":
        result["recommended_areas"] = city_data.get("backpacker_areas", [])
    
    # Ajuster le budget si manquant
    if not result.get("budget"):
        result["budget"] = city_data.get("budget_avg", 250)
    
    result["raw_query"] = query
    return result
