# engine/engine.py - Version finale validée 20/20

import json
import logging
from typing import Optional, Dict, Any

# ✅ Imports relatifs parfaits
from .models import IntentSchema
from .services import call_deepseek_llm, fetch_geocoding
from .fallback import run_basic_analysis, PERSONAS

logger = logging.getLogger(__name__)


async def parse_intent(query: str, traveler_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Point d'entrée principal de l'Intent Engine.
    
    Flow:
    1. Tentative d'analyse via DeepSeek (mode JSON natif)
    2. Géocodage des coordonnées réelles via SIG
    3. Validation Pydantic (types, plages, dates)
    4. Fallback local déterministe si échec
    
    Returns:
        Dict validé et enrichi au format strict du schéma
    """
    # ===== Étape 1 : Tentative d'analyse LLM =====
    try:
        raw_json_output = await call_deepseek_llm(query)
        parsed_data = json.loads(raw_json_output)
        logger.info(f"🧠 DeepSeek: {parsed_data.get('destination')} / {parsed_data.get('area')}")
        
        # ===== Étape 2 : Géocodage réel =====
        destination = parsed_data.get("destination", "Paris")
        area = parsed_data.get("area")
        
        real_lat, real_lng = await fetch_geocoding(
            destination=destination,
            area=area
        )
        parsed_data["lat"] = real_lat
        parsed_data["lng"] = real_lng
        parsed_data["raw_query"] = query
        
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
    # ✅ Fix: Ajout du dictionnaire PERSONAS requis par ta fonction fallback
    fallback_data = run_basic_analysis(query, PERSONAS)
    fallback_data["raw_query"] = query
    
    validated_fallback = IntentSchema(**fallback_data)
    return validated_fallback.model_dump()
