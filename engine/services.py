"""
services.py - Connecteurs API externes
DeepSeek LLM + Géocodage Nominatim
"""

import os
import json
import httpx
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


async def call_deepseek_llm(query: str) -> str:
    """
    Appel résilient à DeepSeek Chat en mode JSON strict
    Timeout: 8 secondes max
    """
    current_year = datetime.now().year
    
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": f"""Tu es un agent de voyage expert en géolocalisation. Extrais les données au format JSON.

📅 Année actuelle: {current_year}

🌍 RÈGLES:
1. Identifie le lieu PRÉCIS (ville, quartier, monument, avenue)
2. Pour un quartier (Bercy, La Défense) → retourne la ville ET le quartier
3. Pour un monument (Tour Eiffel, Colisée) → retourne la ville ET le monument

📌 FORMAT JSON OBLIGATOIRE:
{{
  "trip_type": "business|romantic|family|backpacker|luxury|leisure",
  "destination": "Nom de la ville",
  "area": "Nom du quartier (si applicable)",
  "budget": nombre entier,
  "currency": "EUR",
  "must_have": ["équipement1", "équipement2"],
  "nice_to_have": ["équipement3", "équipement4"],
  "adults": nombre entier,
  "children": nombre entier,
  "rooms": nombre entier,
  "vibe": "luxe|confort|budget|design|familial|romantique",
  "checkin": "YYYY-MM-DD",
  "checkout": "YYYY-MM-DD",
  "place_description": "Description courte du lieu"
}}

Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire."""
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
            logger.error(f"DeepSeek API error: {response.status_code}")
            raise Exception(f"API Status {response.status_code}")
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Vérification que c'est bien du JSON
        try:
            json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"DeepSeek n'a pas retourné de JSON valide: {content[:200]}")
            raise Exception("Invalid JSON response from DeepSeek")
        
        return content


async def fetch_geocoding(destination: str, area: Optional[str] = None) -> Tuple[float, float]:
    """
    Résolution des coordonnées géographiques réelles via Nominatim (OpenStreetMap)
    Fallback sur Paris si échec
    """
    search_query = f"{area}, {destination}" if area else destination
    
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": search_query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "fr,gb,it,es,de,us,ca"  # Priorité
                },
                headers={
                    "User-Agent": "STAYO-Travel-Engine/4.0"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]["lat"])
                    lng = float(data[0]["lon"])
                    logger.info(f"📍 Géocodage réussi: {search_query} → ({lat}, {lng})")
                    return lat, lng
                else:
                    logger.warning(f"⚠️ Aucun résultat pour {search_query}")
            
    except httpx.TimeoutException:
        logger.warning(f"⏱️ Timeout géocodage pour {search_query}")
    except Exception as e:
        logger.error(f"❌ Échec géocodage pour {search_query}: {e}")
    
    # Fallback Paris par défaut
    logger.info(f"📍 Fallback géocodage: Paris (48.8566, 2.3522)")
    return 48.8566, 2.3522