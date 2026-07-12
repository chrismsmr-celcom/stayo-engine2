"""
STAYO Recommendation Engine
Orchestrateur principal - Version 2.1
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
        logger.info(f"🎯 Intent détecté: {trip.intent.trip_type}, must_have: {trip.intent.must_have}")
        
        # ===== 2. Appliquer les overrides =====
        if overrides:
            if overrides.get("trip_type"):
                trip.intent.trip_type = overrides["trip_type"]
            if overrides.get("budget"):
                trip.context.budget = overrides["budget"]
            if overrides.get("currency"):
                trip.context.currency = overrides["currency"]
            if overrides.get("checkin"):
                trip.context.checkin = overrides["checkin"]
            if overrides.get("checkout"):
                trip.context.checkout = overrides["checkout"]
            if overrides.get("adults"):
                trip.context.adults = overrides["adults"]
            if overrides.get("lat"):
                trip.context.event_lat = overrides["lat"]
            if overrides.get("lng"):
                trip.context.event_lng = overrides["lng"]
        
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
            return _empty(trip)
        
        # ===== 4. Enrichir avec les distances =====
        hotels = await enrich_distances(hotels, trip)
        
        # ===== 5. Calculer les scores (avec filtrage) =====
        scored = await score_hotels(hotels, trip)
        
        if not scored:
            return _empty(trip, "Aucun hôtel disponible avec des prix dans votre budget")
        
        trip.scored_hotels = scored
        
        # ===== 6. Sélectionner les 5 meilleurs =====
        trip.recommendations = scored[:5]
        
        # ===== 7. Générer les explications =====
        trip.explanations = explain_recommendations(
            trip.recommendations,
            trip
        )
        
        # ===== 8. Suggérer des activités =====
        trip.suggested_activities = suggest_activities(trip)
        
        trip.processing_time_ms = round(
            (time.perf_counter() - start) * 1000,
            2
        )
        
        return trip.to_dict()
        
    except Exception as e:
        logger.exception(f"❌ Recommendation Engine Error: {e}")
        raise


def _empty(trip: Trip, message: str = "No hotel found."):
    data = trip.to_dict()
    data["recommendations"] = []
    data["message"] = message
    return data
