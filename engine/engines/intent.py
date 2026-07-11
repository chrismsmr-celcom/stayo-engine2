"""
Intent Engine — Compréhension de la requête voyageur
"""

import json
import os
import httpx
from typing import Dict, Any, Optional

# Clé API DeepSeek (optionnelle)
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


async def understand_intent(query: str, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Analyse la requête pour extraire l'intention du voyageur
    
    Args:
        query: Requête textuelle de l'utilisateur
        overrides: Paramètres de surcharge (trip_type, budget, etc.)
    
    Returns:
        Dict contenant:
            - trip_type: business, romantic, family, backpacker, leisure
            - destination: nom de la ville
            - budget: budget estimé
            - currency: devise
            - lat: latitude estimée
            - lng: longitude estimée
            - must_have: liste des équipements souhaités
            - checkin: date d'arrivée (YYYY-MM-DD)
            - checkout: date de départ (YYYY-MM-DD)
            - adults: nombre d'adultes
    """
    
    # ===== 1. Utiliser les overrides s'ils existent =====
    if overrides:
        result = {
            "trip_type": overrides.get("trip_type", "leisure"),
            "destination": overrides.get("destination", "Paris"),
            "budget": overrides.get("budget", 300),
            "currency": overrides.get("currency", "EUR"),
            "lat": overrides.get("lat", 48.8566),
            "lng": overrides.get("lng", 2.3522),
            "must_have": [],
            "checkin": overrides.get("checkin", "2026-07-15"),
            "checkout": overrides.get("checkout", "2026-07-20"),
            "adults": overrides.get("adults", 2),
            "raw_query": query
        }
        
        # Ajuster les must_have selon le type de voyage
        if result["trip_type"] == "romantic":
            result["must_have"] = ["spa", "vue", "restaurant gastronomique"]
        elif result["trip_type"] == "business":
            result["must_have"] = ["wifi haut débit", "business center", "calme"]
        elif result["trip_type"] == "family":
            result["must_have"] = ["piscine", "chambre familiale", "club enfants"]
        elif result["trip_type"] == "backpacker":
            result["must_have"] = ["wifi gratuit", "bagagerie", "ambiance sociale"]
        else:  # leisure
            result["must_have"] = ["wifi", "petit-déjeuner", "climatisation"]
            
        return result
    
    # ===== 2. Utiliser DeepSeek si disponible =====
    if DEEPSEEK_KEY:
        try:
            return await _analyze_with_deepseek(query)
        except Exception as e:
            print(f"Erreur DeepSeek: {e}, fallback sur l'analyse basique")
    
    # ===== 3. Fallback : Analyse basique =====
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
                            "adults": nombre (entier)
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
        
        # Extraire le JSON de la réponse
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["raw_query"] = query
            return result
        
        raise Exception("Aucun JSON trouvé dans la réponse")


def _analyze_basic(query: str) -> Dict[str, Any]:
    """Analyse basique sans API externe"""
    result = {
        "trip_type": "leisure",
        "destination": "Paris",
        "budget": 300,
        "currency": "EUR",
        "lat": 48.8566,
        "lng": 2.3522,
        "must_have": ["wifi", "petit-déjeuner", "climatisation"],
        "checkin": "2026-07-15",
        "checkout": "2026-07-20",
        "adults": 2,
        "raw_query": query
    }
    
    # Détection basique du type de voyage
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["affaires", "business", "conférence", "réunion", "travail"]):
        result["trip_type"] = "business"
        result["must_have"] = ["wifi haut débit", "business center", "calme"]
        
    elif any(word in query_lower for word in ["romantique", "couple", "amoureux", "lune de miel"]):
        result["trip_type"] = "romantic"
        result["must_have"] = ["spa", "vue", "restaurant gastronomique"]
        
    elif any(word in query_lower for word in ["famille", "enfant", "enfants", "familial"]):
        result["trip_type"] = "family"
        result["must_have"] = ["piscine", "chambre familiale", "club enfants"]
        
    elif any(word in query_lower for word in ["backpacker", "auberge", "jeunesse", "pas cher"]):
        result["trip_type"] = "backpacker"
        result["budget"] = 50
        result["must_have"] = ["wifi gratuit", "bagagerie", "ambiance sociale"]
    
    # Détection de la destination
    cities = {
        "paris": (48.8566, 2.3522),
        "londres": (51.5074, -0.1278),
        "new york": (40.7128, -74.0060),
        "barcelone": (41.3851, 2.1734),
        "rome": (41.9028, 12.4964),
        "berlin": (52.5200, 13.4050),
        "amsterdam": (52.3676, 4.9041),
        "bruxelles": (50.8503, 4.3517),
        "marseille": (43.2965, 5.3698),
        "lyon": (45.7640, 4.8357)
    }
    
    for city, (lat, lng) in cities.items():
        if city in query_lower:
            result["destination"] = city.capitalize()
            result["lat"] = lat
            result["lng"] = lng
            break
    
    # Détection du budget
    import re
    budget_matches = re.findall(r'(\d+)[\s-]*€', query_lower)
    if budget_matches:
        result["budget"] = int(budget_matches[0])
    
    # Détection des dates
    date_matches = re.findall(r'(\d{1,2})\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})', query_lower)
    if date_matches:
        months = {"janvier": "01", "février": "02", "mars": "03", "avril": "04", "mai": "05", "juin": "06",
                  "juillet": "07", "août": "08", "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"}
        day, month, year = date_matches[0]
        result["checkin"] = f"{year}-{months[month]}-{day.zfill(2)}"
    
    return result


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
        "familial": ["chambre familiale", "club enfants", "babysitting"]
    }
    
    text_lower = text.lower()
    found = []
    for amenity, keywords in amenities_keywords.items():
        if any(kw in text_lower for kw in keywords):
            found.append(amenity)
    
    return found
    from engine.core.trip import Trip


async def parse_intent(query: str, traveler_id: str = None) -> Trip:
    """
    Transforme une requête utilisateur en objet Trip.
    """
    intent = await understand_intent(query)

    trip = Trip(
        raw_query=query,
        traveler_id=traveler_id
    )

    # Context
    trip.context.trip_type = intent.get("trip_type")
    trip.context.destination = intent.get("destination")

    trip.context.event_lat = intent.get("lat")
    trip.context.event_lng = intent.get("lng")

    trip.context.budget = intent.get("budget")
    trip.context.currency = intent.get("currency")

    trip.context.checkin = intent.get("checkin")
    trip.context.checkout = intent.get("checkout")

    trip.context.adults = intent.get("adults")

    trip.context.must_have = intent.get("must_have", [])

    return trip
