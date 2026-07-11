"""
Recommendation Engine — Orchestrateur STAYO Core.
"""

import time
from engine.core.trip import Trip
from engine.engines.intent import parse_intent
from engine.engines.hotel import fetch_hotels
from engine.engines.geo import enrich_distances
from engine.engines.scoring import score_hotels
from engine.engines.explain import explain_recommendations
from engine.engines.activities import suggest_activities


async def recommend(query: str, traveler_id: str = None) -> dict:
    start = time.time()
    trip = Trip(raw_query=query, traveler_id=traveler_id)
    
    # 1. Intent Engine — Comprendre
    trip = await parse_intent(query)
    
    # 2. Hotel Engine — Récupérer
    hotels = await fetch_hotels(
        trip.context.event_lat or 48.8566,
        trip.context.event_lng or 2.3522,
        trip.context.checkin,
        trip.context.checkout,
        trip.context.adults,
        trip.context.currency
    )
    trip.hotels = hotels
    trip.total_found = len(hotels)
    
    if not hotels:
        return _empty_response(trip)
    
    # 3. Geo Engine — Distances
    hotels = await enrich_distances(hotels, trip)
    
    # 4. Scoring Engine — Scores modulaires
    scored = score_hotels(trip, hotels)
    trip.scored_hotels = scored
    trip.recommendations = scored[:5]
    
    # 5. Explain Engine — Explications
    trip.explanations = explain_recommendations(scored[:5], trip)
    
    # 6. Activities Engine — Suggestions
    trip.suggested_activities = suggest_activities(trip)
    
    trip.processing_time_ms = round((time.time() - start) * 1000)
    
    return trip.to_dict()


def _empty_response(trip):
    trip.processing_time_ms = 0
    d = trip.to_dict()
    d["message"] = "Aucun hotel trouve pour ces dates."
    return d
