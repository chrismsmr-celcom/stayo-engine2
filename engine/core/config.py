"""
Configuration centralisée STAYO Core.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
LITEAPI_KEY = os.getenv("LITEAPI_KEY", "prod_3a27a498-2b18-43a8-a91e-f3f241c889a7")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
OPENROUTESERVICE_KEY = os.getenv("OPENROUTESERVICE_KEY", "")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY", "")

# URLs
LITEAPI_BASE = "https://api.liteapi.travel/v3.0"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/foot-walking"

# Cache
CACHE_TTL_SECONDS = 15 * 60  # 15 minutes

# Scoring weights par type de voyage
WEIGHTS = {
    "business": {"location": 3, "price": 1.5, "quality": 1, "amenities": 2.5, "transport": 2.5, "lifestyle": 2},
    "romantic": {"location": 1, "price": 1, "quality": 2.5, "amenities": 2, "transport": 1, "lifestyle": 3},
    "family": {"location": 2, "price": 2, "quality": 1.5, "amenities": 2.5, "transport": 1.5, "lifestyle": 2.5},
    "backpacker": {"location": 1.5, "price": 3.5, "quality": 0.5, "amenities": 0.5, "transport": 2, "lifestyle": 1},
    "leisure": {"location": 2, "price": 2, "quality": 2, "amenities": 1.5, "transport": 1.5, "lifestyle": 2}
}

# Activités suggérées par type
ACTIVITIES = {
    "business": ["coworking", "restaurant d'affaires", "bar lounge", "salle de sport"],
    "romantic": ["spa", "diner romantique", "croisiere", "visite guidee privee", "degustation de vin"],
    "family": ["parc d'attractions", "zoo", "aquarium", "restaurant familial", "musee pour enfants"],
    "backpacker": ["visite gratuite", "street food", "auberge de jeunesse", "marche local"],
    "leisure": ["musee", "visite guidee", "shopping", "restaurant local", "parc"]
}