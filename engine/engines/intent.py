"""
Intent Engine — Compréhension de la requête voyageur
Version 2.0 - Analyse avancée
"""

import json
import os
import re
import httpx
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


async def parse_intent(query: str, traveler_id: str = None) -> Dict[str, Any]:
    """
    Analyse la requête pour extraire l'intention du voyageur
    """
    # D'abord, essayer DeepSeek
    if DEEPSEEK_KEY:
        try:
            result = await _analyze_with_deepseek(query)
            if result:
                logger.info(f"DeepSeek analysis: {result}")
                return result
        except Exception as e:
            logger.warning(f"DeepSeek error: {e}, fallback sur analyse basique")
    
    # Fallback : analyse basique avancée
    return _analyze_basic(query)


async def _analyze_with_deepseek(query: str) -> Dict[str, Any]:
    """Analyse la requête avec DeepSeek API"""
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
                        "content": """Tu es un assistant spécialisé dans l'analyse de requêtes touristiques.
                        Extrais les informations suivantes au format JSON:
                        {
                            "trip_type": "business|romantic|family|backpacker|leisure",
                            "destination": "nom de la ville",
                            "budget": budget estimé (nombre, en euros),
                            "currency": "EUR|USD|GBP",
                            "lat": latitude (nombre),
                            "lng": longitude (nombre),
                            "must_have": ["liste", "des", "équipements", "souhaités"],
                            "checkin": "YYYY-MM-DD",
                            "checkout": "YYYY-MM-DD",
                            "adults": nombre (entier),
                            "children": nombre (entier),
                            "rooms": nombre de chambres (entier),
                            "vibe": "luxe|budget|confort|design|familial"
                        }
                        Réponds UNIQUEMENT avec le JSON, sans autre texte."""
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"DeepSeek API error: {response.status_code}")
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["raw_query"] = query
            return result
        
        raise Exception("Aucun JSON trouvé dans la réponse")


def _analyze_basic(query: str) -> Dict[str, Any]:
    """Analyse basique avancée sans API externe"""
    query_lower = query.lower()
    
    # ===== Détection du type de voyage =====
    trip_type = "leisure"
    vibe = "confort"
    
    # Mots-clés par type
    business_keywords = ["business", "affaires", "conférence", "réunion", "travail", "client", "pro"]
    romantic_keywords = ["romantique", "couple", "amoureux", "lune de miel", "anniversaire", "week-end", "escapade"]
    family_keywords = ["famille", "enfant", "enfants", "familial", "bébé", "maman", "papa", "chambre", "appartement"]
    backpacker_keywords = ["backpacker", "auberge", "jeunesse", "pas cher", "budget", "solo"]
    
    if any(word in query_lower for word in business_keywords):
        trip_type = "business"
        vibe = "luxe"
    elif any(word in query_lower for word in romantic_keywords):
        trip_type = "romantic"
        vibe = "confort"
    elif any(word in query_lower for word in family_keywords):
        trip_type = "family"
        vibe = "familial"
    elif any(word in query_lower for word in backpacker_keywords):
        trip_type = "backpacker"
        vibe = "budget"
    
    # ===== Détection du nombre de personnes =====
    adults = 2
    children = 0
    rooms = 1
    
    # Recherche des nombres
    adult_matches = re.findall(r'(\d+)\s*(adulte|adultes|personne|personnes|pax)', query_lower)
    if adult_matches:
        adults = int(adult_matches[0][0])
    
    child_matches = re.findall(r'(\d+)\s*(enfant|enfants|ans)', query_lower)
    if child_matches:
        children = sum(int(m[0]) for m in child_matches)
        # Si des enfants sont détectés, c'est une famille
        if children > 0 and trip_type != "family":
            trip_type = "family"
    
    # Détection du nombre de chambres
    room_matches = re.findall(r'(\d+)\s*(chambre|chambres)', query_lower)
    if room_matches:
        rooms = int(room_matches[0][0])
    
    # Ajustement du nombre de chambres pour les familles
    if trip_type == "family" and rooms == 1 and children > 0:
        rooms = 2  # Par défaut 2 chambres pour une famille
    
    # ===== Détection du budget =====
    budget = None
    budget_matches = re.findall(r'(\d+)\s*[€$£]', query_lower)
    if budget_matches:
        budget = int(budget_matches[0])
    elif "pas cher" in query_lower or "budget" in query_lower:
        budget = 100  # Budget serré
    elif "luxe" in query_lower or "luxury" in query_lower:
        budget = 500
    
    # ===== Détection des dates =====
    checkin = None
    checkout = None
    
    date_match = re.search(r'(\d{1,2})\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})', query_lower)
    if date_match:
        months = {"janvier": "01", "février": "02", "mars": "03", "avril": "04", "mai": "05", "juin": "06",
                  "juillet": "07", "août": "08", "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"}
        day, month, year = date_match.groups()
        checkin = f"{year}-{months[month]}-{day.zfill(2)}"
        
        # Recherche de la date de checkout
        checkout_match = re.search(r'au\s+(\d{1,2})\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)', query_lower)
        if checkout_match:
            day_out, month_out = checkout_match.groups()
            checkout = f"{year}-{months[month_out]}-{day_out.zfill(2)}"
        else:
            # Par défaut : +1 nuit
            from datetime import datetime, timedelta
            checkin_date = datetime.strptime(checkin, "%Y-%m-%d")
            checkout_date = checkin_date + timedelta(days=1)
            checkout = checkout_date.strftime("%Y-%m-%d")
    
    # ===== Détection de la destination =====
    destination = "Paris"
    lat = 48.8566
    lng = 2.3522
    
    cities = {
        "paris": (48.8566, 2.3522),
        "londres": (51.5074, -0.1278),
        "new york": (40.7128, -74.0060),
        "barcelone": (41.3851, 2.1734),
        "rome": (41.9028, 12.4964),
        "berlin": (52.5200, 13.4050),
        "venise": (45.4408, 12.3155),
        "amsterdam": (52.3676, 4.9041),
        "bruxelles": (50.8503, 4.3517),
        "marseille": (43.2965, 5.3698),
        "lyon": (45.7640, 4.8357),
        "nice": (43.7102, 7.2620),
        "bordeaux": (44.8378, -0.5792),
        "toulouse": (43.6047, 1.4442),
        "strasbourg": (48.5734, 7.7521),
        "nantes": (47.2184, -1.5536),
        "montpellier": (43.6108, 3.8767),
        "lille": (50.6292, 3.0573),
        "rennes": (48.1173, -1.6778),
        "reims": (49.2583, 4.0317),
        "saint denis": (48.9362, 2.3574),
        "creteil": (48.7907, 2.4528),
        "versailles": (48.8014, 2.1301)
    }
    
    for city, (c_lat, c_lng) in cities.items():
        if city in query_lower:
            destination = city.capitalize()
            lat = c_lat
            lng = c_lng
            break
    
    # ===== Détermination des must_have =====
    must_have = []
    
    # Équipements généraux
    if "wifi" in query_lower:
        must_have.append("wifi")
    if "parking" in query_lower:
        must_have.append("parking")
    if "piscine" in query_lower or "pool" in query_lower:
        must_have.append("piscine")
    if "spa" in query_lower:
        must_have.append("spa")
    if "restaurant" in query_lower:
        must_have.append("restaurant")
    if "petit déjeuner" in query_lower or "breakfast" in query_lower:
        must_have.append("petit déjeuner")
    
    # Équipements spécifiques au type de voyage
    if trip_type == "business":
        must_have.extend(["wifi haut débit", "business center", "salle de réunion"])
    elif trip_type == "romantic":
        must_have.extend(["chambre double", "vue"])
    elif trip_type == "family":
        must_have.extend(["chambre familiale", "parking"])
        if children > 0:
            must_have.append("club enfants")
    
    # ===== Construction du résultat =====
    return {
        "trip_type": trip_type,
        "destination": destination,
        "budget": budget or (500 if trip_type == "business" else 250 if trip_type == "romantic" else 200 if trip_type == "family" else 150),
        "currency": "EUR",
        "lat": lat,
        "lng": lng,
        "must_have": must_have,
        "checkin": checkin or "",
        "checkout": checkout or "",
        "adults": adults,
        "children": children,
        "rooms": rooms,
        "vibe": vibe,
        "raw_query": query
    }


def extract_amenities(text: str) -> list:
    """Extrait les équipements souhaités d'un texte"""
    amenities_keywords = {
        "wifi": ["wifi", "internet", "connexion"],
        "piscine": ["piscine", "pool", "bassin"],
        "spa": ["spa", "bien-être", "massage", "sauna"],
        "restaurant": ["restaurant", "gastronomique", "dîner"],
        "parking": ["parking", "stationnement", "garage"],
        "vue": ["vue", "balcon", "terrasse", "panorama"],
        "calme": ["calme", "silencieux", "tranquille"],
        "climatisation": ["climatisation", "air conditionné", "clim"],
        "petit-déjeuner": ["petit-déjeuner", "breakfast", "brunch"],
        "business": ["business center", "salle de réunion", "coworking"],
        "familial": ["chambre familiale", "club enfants", "babysitting"],
        "luxe": ["concierge", "butler", "suite", "premium", "vip"]
    }
    
    text_lower = text.lower()
    found = []
    for amenity, keywords in amenities_keywords.items():
        if any(kw in text_lower for kw in keywords):
            found.append(amenity)
    
    return found
