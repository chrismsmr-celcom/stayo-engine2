"""
STAYO Hotel Engine V2

Responsabilité :
- Connexion LiteAPI
- Recherche hôtels
- Prix
- Normalisation
- Préparation IA
"""

import os
import json
import asyncio
import httpx
import logging

from engine.engines.hotel_features import extract_features

logger = logging.getLogger(__name__)

LITEAPI_KEY = os.getenv("LITEAPI_KEY")
LITEAPI_BASE = "https://api.liteapi.travel/v3.0"


async def fetch_hotels(
    lat,
    lng,
    checkin,
    checkout,
    adults,
    currency,
    radius=5000,
    limit=200
):
    """
    Récupère les hôtels depuis LiteAPI avec leurs prix.
    
    Returns:
        list: Liste des hôtels normalisés avec prix et caractéristiques
    """
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Rechercher les hôtels
        hotels = await _search_hotels(client, lat, lng, radius, limit)
        if not hotels:
            return []
        
        # 2. Récupérer les prix
        prices = await _fetch_prices(client, hotels, checkin, checkout, adults, currency)
        
        # 3. Normaliser et enrichir
        normalized = []
        for hotel in hotels:
            if not hotel.get("latitude"):
                continue
            
            # Structure de base
            item = {
                "id": hotel.get("id"),
                "name": hotel.get("name", "Hotel"),
                "lat": float(hotel["latitude"]),
                "lng": float(hotel["longitude"]),
                "address": hotel.get("address", ""),
                "city": hotel.get("city", ""),
                "country": hotel.get("country", ""),
                "thumbnail": hotel.get("thumbnail") or hotel.get("main_photo"),
                "rating": float(hotel.get("rating", 0)),
                "reviewCount": hotel.get("reviewCount", 0),
                "stars": hotel.get("stars", 0),
                "price": prices.get(hotel["id"]),
                "currency": currency,
                "hotelFacilities": hotel.get("hotelFacilities", []),
            }
            
            # Extraire les caractéristiques IA
            item["features"] = extract_features(item)
            normalized.append(item)
        
        logger.info(f"{len(normalized)} hôtels récupérés")
        return normalized


# --------------------------------------------------
# SEARCH HOTELS
# --------------------------------------------------

async def _search_hotels(client, lat, lng, radius, limit):
    """
    Recherche les hôtels autour d'un point GPS.
    """
    try:
        response = await client.get(
            f"{LITEAPI_BASE}/data/hotels",
            params={
                "latitude": lat,
                "longitude": lng,
                "radius": min(radius, 50000),
                "limit": limit,
                "language": "fr"
            },
            headers={"X-API-Key": LITEAPI_KEY}
        )
        
        if response.status_code != 200:
            logger.error(f"LiteAPI hotel search error: {response.status_code}")
            return []
        
        data = response.json()
        hotels = data.get("data", [])
        logger.info(f"{len(hotels)} hôtels trouvés")
        return hotels
        
    except Exception as e:
        logger.error(f"Hotel search exception: {e}")
        return []


# --------------------------------------------------
# FETCH PRICES
# --------------------------------------------------

async def _fetch_prices(client, hotels, checkin, checkout, adults, currency):
    prices = {}
    ids = [h["id"] for h in hotels[:100] if h.get("id")]
    
    if not ids:
        return prices
    
    try:
        response = await client.post(
            f"{LITEAPI_BASE}/hotels/rates",
            json={
                "hotelIds": ids,
                "checkin": checkin,
                "checkout": checkout,
                "currency": currency,
                "guestNationality": "FR",
                "occupancies": [{"adults": adults}],
                "maxRatesPerHotel": 1,
                "limit": 100,
                "timeout": 8
            },
            headers={"X-API-Key": LITEAPI_KEY}
        )
        
        if response.status_code != 200:
            print(f"LiteAPI rates error: {response.status_code}")
            return prices
        
        data = response.json()
        
        # ✅ AJOUT : Log de la réponse complète
        print(f"LiteAPI rates response: {json.dumps(data, indent=2)[:2000]}")
        
        for hotel in data.get("data", []):
            hotel_id = hotel.get("hotelId")
            amount = _extract_price(hotel)
            
            # ✅ AJOUT : Log pour chaque hôtel
            print(f"Hotel {hotel_id}: amount={amount}, raw={hotel}")
            
            if amount and hotel_id:
                prices[hotel_id] = round(float(amount))
        
    except Exception as e:
        print(f"Price error: {e}")
    
    return prices


# --------------------------------------------------
# PRICE EXTRACTOR (Version corrigée)
# --------------------------------------------------

def _extract_price(hotel_rate_data: dict):
    """
    Extrait le prix d'une réponse de LiteAPI /hotels/rates
    Compatible avec les nouvelles structures de données.
    """
    if not hotel_rate_data:
        return None
    
    # === Méthode 1: via roomTypes (structure standard) ===
    room_types = hotel_rate_data.get("roomTypes", [])
    if room_types:
        first_room = room_types[0]
        
        # 1.1: offerRetailRate (structure directe)
        offer_rate = first_room.get("offerRetailRate", {})
        amount = offer_rate.get("amount")
        if amount:
            return amount
        
        # 1.2: via rates array (structure avec plusieurs taux)
        rates = first_room.get("rates", [])
        if rates:
            first_rate = rates[0]
            
            # 1.2.1: retailRate.total (structure standard actuelle)
            retail = first_rate.get("retailRate", {})
            total = retail.get("total", [])
            if total and isinstance(total, list):
                amount = total[0].get("amount")
                if amount:
                    return amount
            
            # 1.2.2: retailRate direct (certaines versions)
            amount = retail.get("amount")
            if amount:
                return amount
            
            # 1.2.3: rate.total (ancienne structure)
            rate_total = first_rate.get("total", [])
            if rate_total and isinstance(rate_total, list):
                amount = rate_total[0].get("amount")
                if amount:
                    return amount
            
            # 1.2.4: price direct dans la rate
            amount = first_rate.get("price")
            if amount:
                return amount
    
    # === Méthode 2: structure alternative (flat) ===
    amount = hotel_rate_data.get("amount")
    if amount:
        return amount
    
    # === Méthode 3: structure avec total direct ===
    total = hotel_rate_data.get("total")
    if isinstance(total, dict):
        amount = total.get("amount")
        if amount:
            return amount
    
    # === Méthode 4: structure avec retailRate au niveau racine ===
    retail = hotel_rate_data.get("retailRate", {})
    amount = retail.get("amount")
    if amount:
        return amount
    
    total = retail.get("total", [])
    if total and isinstance(total, list):
        amount = total[0].get("amount")
        if amount:
            return amount
    
    # === Méthode 5: recherche dans toutes les clés ===
    for key, value in hotel_rate_data.items():
        if isinstance(value, dict):
            amount = value.get("amount")
            if amount:
                return amount
        elif key in ["amount", "price", "total_amount", "totalPrice"]:
            if value:
                return value
    
    return None
