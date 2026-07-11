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


# engine/engines/recommend.py

async def recommend(query: str, traveler_id: str = None, overrides: dict = None):
    """
    Moteur principal de recommandation
    
    Args:
        query: Requête textuelle de l'utilisateur
        traveler_id: ID du voyageur (optionnel)
        overrides: Paramètres de surcharge (optionnel)
            - trip_type: business, romantic, family, backpacker, leisure
            - budget: float
            - currency: str
            - checkin: str (YYYY-MM-DD)
            - checkout: str (YYYY-MM-DD)
            - adults: int
            - lat: float
            - lng: float
    """
    # Initialiser overrides si None
    if overrides is None:
        overrides = {}
    
    # ===== Étape 1 : Comprendre l'intention =====
    from engine.engines.intent import understand_intent
    intent = await understand_intent(query, overrides=overrides)
    
    # ===== Étape 2 : Créer l'objet Trip =====
    from engine.core.trip import Trip
    trip = Trip(intent=intent, context={
        "budget": overrides.get("budget") or intent.get("budget", 300),
        "currency": overrides.get("currency") or "EUR",
        "checkin": overrides.get("checkin") or "2026-07-15",
        "checkout": overrides.get("checkout") or "2026-07-20",
        "adults": overrides.get("adults") or 2,
        "event": intent.get("destination", "Paris"),
        "event_lat": overrides.get("lat") or intent.get("lat"),
        "event_lng": overrides.get("lng") or intent.get("lng"),
    })
    
    # ===== Étape 3 : Récupérer les hôtels =====
    from engine.engines.hotel import fetch_hotels
    hotels = await fetch_hotels(
        lat=trip.context.get("event_lat", 48.8566),
        lng=trip.context.get("event_lng", 2.3522),
        checkin=trip.context.get("checkin"),
        checkout=trip.context.get("checkout"),
        adults=trip.context.get("adults", 2),
        currency=trip.context.get("currency", "EUR")
    )
    
    if not hotels:
        return {"recommendations": [], "message": "Aucun hôtel trouvé"}
    
    # ===== Étape 4 : Enrichir avec les distances =====
    from engine.engines.geo import enrich_distances
    hotels = await enrich_distances(hotels, trip)
    
    # ===== Étape 5 : Calculer les scores =====
    from engine.engines.scoring import score_hotels
    hotels = await score_hotels(hotels, trip)
    
    # Trier par score
    hotels = sorted(hotels, key=lambda x: x.get("score", 0), reverse=True)
    
    # ===== Étape 6 : Générer les explications =====
    from engine.engines.explain import explain_recommendations
    explanations = explain_recommendations(hotels[:10], trip)
    
    # ===== Étape 7 : Suggérer des activités =====
    from engine.engines.activities import suggest_activities
    activities = suggest_activities(trip)
    
    # ===== Retourner les résultats =====
    return {
        "recommendations": hotels[:10],
        "explanations": explanations,
        "activities": activities,
        "intent": intent,
        "context": trip.context,
        "total_found": len(hotels)
    }


def _empty_response(trip):
    trip.processing_time_ms = 0
    d = trip.to_dict()
    d["message"] = "Aucun hotel trouve pour ces dates."
    return d
