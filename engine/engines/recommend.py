"""
STAYO Recommendation Engine
Orchestrateur principal - Version 3.0
"""

import time
import logging
from engine.core.trip import Trip
from engine.engines.intent import parse_intent
from engine.engines.hotel import fetch_hotels
from engine.engines.geo import enrich_distances
from engine.engines.scoring import score_hotels
from engine.engines.explain import explain_recommendations
from engine.engines.activities import suggest_activities

logger = logging.getLogger(__name__)


async def recommend(
    query: str,
    traveler_id: str = None,
    overrides: dict = None
):
    start = time.perf_counter()
    
    try:
        # ===== 1. Comprendre l'intention =====
        trip = await parse_intent(query, traveler_id)
        
        # Log détaillé
        logger.info(f"🎯 TRIP DÉTECTÉ:")
        logger.info(f"   - Type: {trip.intent.trip_type}")
        logger.info(f"   - Destination: {trip.intent.destination}")
        logger.info(f"   - Budget: {trip.intent.budget}")
        logger.info(f"   - Adultes: {trip.intent.adults}")
        logger.info(f"   - Enfants: {trip.intent.children}")
        logger.info(f"   - Chambres: {trip.intent.rooms}")
        logger.info(f"   - Must have: {trip.intent.must_have}")
        logger.info(f"   - Vibe: {trip.intent.vibe}")
        
        # ===== 2. Appliquer les overrides =====
        if overrides:
            for key, value in overrides.items():
                if value is not None:
                    setattr(trip.intent, key, value) if hasattr(trip.intent, key) else None
        
        # ===== 3. Récupérer les hôtels =====
        hotels = await fetch_hotels(
            lat=trip.context.event_lat,
            lng=trip.context.event_lng,
            checkin=trip.context.checkin,
            checkout=trip.context.checkout,
            adults=trip.context.adults,
            currency=trip.context.currency
        )
        
        trip.hotels = hotels
        trip.total_found = len(hotels)
        
        if not hotels:
            return _empty(trip, "Aucun hôtel trouvé dans cette zone")
        
        # ===== 4. Enrichir avec les distances =====
        hotels = await enrich_distances(hotels, trip)
        
        # ===== 5. Calculer les scores =====
        scored = await score_hotels(hotels, trip)
        
        if not scored:
            return _empty(trip, "Aucun hôtel disponible avec des prix dans votre budget")
        
        # ===== 6. Sélection des recommandations avec DIVERSITÉ =====
        recommendations = _select_diverse_recommendations(scored, trip)
        
        trip.scored_hotels = scored
        trip.recommendations = recommendations
        
        # ===== 7. Générer les explications =====
        trip.explanations = explain_recommendations(recommendations, trip)
        
        # ===== 8. Suggérer des activités =====
        trip.suggested_activities = suggest_activities(trip)
        
        trip.processing_time_ms = round(
            (time.perf_counter() - start) * 1000,
            2
        )
        
        logger.info(f"✅ {len(recommendations)} recommandations proposées")
        return trip.to_dict()
        
    except Exception as e:
        logger.exception(f"❌ Recommendation Engine Error: {e}")
        raise


def _select_diverse_recommendations(scored: list, trip) -> list:
    """
    Sélectionne des recommandations DIVERSIFIÉES
    pour éviter les répétitions
    """
    if not scored:
        return []
    
    trip_type = trip.intent.trip_type if hasattr(trip.intent, 'trip_type') else "leisure"
    vibe = trip.intent.vibe if hasattr(trip.intent, 'vibe') else "confort"
    budget = trip.context.budget if hasattr(trip.context, 'budget') else 250
    
    recommendations = []
    
    # ===== 1. D'abord, le MEILLEUR hôtel (score le plus élevé) =====
    if scored:
        recommendations.append(scored[0])
        scored.pop(0)
    
    # ===== 2. Ensuite, diversité par prix =====
    # Un hôtel moins cher
    cheap_hotels = [h for h in scored if h.get("price", 0) < budget * 0.7]
    if cheap_hotels and len(recommendations) < 5:
        recommendations.append(cheap_hotels[0])
        scored.remove(cheap_hotels[0])
    
    # Un hôtel dans le budget
    mid_hotels = [h for h in scored if budget * 0.7 <= h.get("price", 0) <= budget]
    if mid_hotels and len(recommendations) < 5:
        recommendations.append(mid_hotels[0])
        scored.remove(mid_hotels[0])
    
    # ===== 3. Diversité par distance =====
    # Un hôtel proche (distance < 10 min)
    close_hotels = [h for h in scored if h.get("distance_event_minutes", 99) < 10]
    if close_hotels and len(recommendations) < 5:
        recommendations.append(close_hotels[0])
        scored.remove(close_hotels[0])
    
    # ===== 4. Diversité par type =====
    # Pour les familles, proposer un appartement / résidence
    if trip_type == "family":
        apartment_hotels = [h for h in scored if "appart" in h.get("name", "").lower() or "suite" in h.get("name", "").lower()]
        if apartment_hotels and len(recommendations) < 5:
            recommendations.append(apartment_hotels[0])
            scored.remove(apartment_hotels[0])
    
    # Pour les romantiques, proposer un hôtel avec spa
    if trip_type == "romantic":
        spa_hotels = [h for h in scored if "spa" in str(h.get("hotelFacilities", [])).lower()]
        if spa_hotels and len(recommendations) < 5:
            recommendations.append(spa_hotels[0])
            scored.remove(spa_hotels[0])
    
    # ===== 5. Compléter avec les meilleurs restants =====
    while len(recommendations) < 5 and scored:
        recommendations.append(scored[0])
        scored.pop(0)
    
    return recommendations[:5]


def _empty(trip: Trip, message: str = "No hotel found."):
    data = trip.to_dict()
    data["recommendations"] = []
    data["message"] = message
    return data
