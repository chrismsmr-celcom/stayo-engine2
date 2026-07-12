"""
engine.py - Point d'entrée principal de l'Intent Engine
"""

import json
import logging
from typing import Optional, Dict, Any

from .models import IntentSchema
from .services import call_deepseek_llm, fetch_geocoding
from .fallback import run_basic_analysis

logger = logging.getLogger(__name__)


async def parse_intent(query: str, traveler_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Point d'entrée principal de l'Intent Engine.
    """
    # ===== Étape 1 : Tentative d'analyse LLM =====
    try:
        raw_json_output = await call_deepseek_llm(query)
        parsed_data = json.loads(raw_json_output)
        logger.info(f"🧠 DeepSeek: {parsed_data.get('destination')} / {parsed_data.get('area')}")
        
        # ===== Étape 2 : Récupérer les coordonnées =====
        destination = parsed_data.get("destination", "Paris")
        area = parsed_data.get("area")
        
        # ✅ D'abord, utiliser les coordonnées de DeepSeek si disponibles
        lat = parsed_data.get("latitude")
        lng = parsed_data.get("longitude")
        
        # ✅ Sinon, faire un géocodage externe
        if lat is None or lng is None:
            lat, lng = await fetch_geocoding(
                destination=destination,
                area=area
            )
        else:
            logger.info(f"📍 Coordonnées DeepSeek: ({lat}, {lng})")
        
        parsed_data["lat"] = lat
        parsed_data["lng"] = lng
        parsed_data["raw_query"] = query
        
        # ✅ Correction : budget à 0
        if parsed_data.get("budget", 0) <= 0:
            parsed_data["budget"] = 250
            logger.warning("⚠️ Budget à 0 détecté, remplacé par 250")
        
        # ===== Étape 3 : Validation Pydantic =====
        validated_intent = IntentSchema(**parsed_data)
        logger.info(f"✅ Intent validé: {validated_intent.trip_type} - {validated_intent.destination}")
        return validated_intent.model_dump()
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON invalide de DeepSeek: {e}")
    except Exception as e:
        logger.error(f"❌ Erreur dans le flux principal: {e}")
    
    # ===== Étape 4 : Plan B - Fallback local =====
    logger.info("🔄 Bascule vers le mode dégradé (fallback)")
    fallback_data = run_basic_analysis(query)
    fallback_data["raw_query"] = query
    
    if fallback_data.get("budget", 0) <= 0:
        fallback_data["budget"] = 250
    
    validated_fallback = IntentSchema(**fallback_data)
    return validated_fallback.model_dump()
