"""
STAYO Recommendation Engine
Orchestrateur principal - Version 3.2
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
        intent_data = await parse_intent(query, traveler_id)
        
        # ✅ Si parse_intent retourne un dict, on l'utilise directement
        if isinstance(intent_data, dict):
            logger.info(f"🎯 INTENT DÉTECTÉ (dict):")
            logger.info(f"   - Type: {intent_data.get('trip_type', 'leisure')}")
            logger.info(f"   - Destination: {intent_data.get('destination', 'Paris')}")
            logger.info(f"   - Budget: {intent_data.get('budget', 300)}")
            logger.info(f"   - Adultes: {intent_data.get('adults', 2)}")
            logger.info(f"   - Enfants: {intent_data.get('children', 0)}")
            logger.info(f"   - Chambres: {intent_data.get('rooms', 1)}")
            logger.info(f"   - Must have: {intent_data.get('must_have', [])}")
            logger.info(f"   - Vibe: {intent_data.get('vibe', 'confort')}")
            
            # ✅ Récupérer les dates depuis date_range ou checkin/checkout
            checkin = intent_data.get('checkin', '')
            checkout = intent_data.get('checkout', '')
            
            # Si les dates sont vides, essayer depuis date_range
            if not checkin or not checkout:
                date_range = intent_data.get('date_range', [])
                if date_range and len(date_range) >= 2:
                    checkin = date_range[0]
                    checkout = date_range[1]
                    logger.info(f"   - Dates (from date_range): {checkin} → {checkout}")
            
            # Si toujours vides, utiliser les paramètres par défaut
            if not checkin:
                from datetime import datetime, timedelta
                today = datetime.now().strftime("%Y-%m-%d")
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                checkin = today
                checkout = tomorrow
                logger.info(f"   - Dates (default): {checkin} → {checkout}")
            
            # ===== 2. Créer l'objet Trip =====
            trip = Trip()
            trip.intent = type('Intent', (), {
                'trip_type': intent_data.get('trip_type', 'leisure'),
                'goal': 'hotel',
                'must_have': intent_data.get('must_have', []),
                'nice_to_have': intent_data.get('nice_to_have', []),
                'avoid': intent_data.get('avoid', []),
                'destination': intent_data.get('destination', 'Paris'),
                'budget': intent_data.get('budget', 300),
                'vibe': intent_data.get('vibe', 'confort'),
                'rooms': intent_data.get('rooms', 1)
            })()
            
            trip.context = type('Context', (), {
                'event': intent_data.get('destination', 'Paris'),
                'event_lat': intent_data.get('lat', 48.8566),
                'event_lng': intent_data.get('lng', 2.3522),
                'budget': intent_data.get('budget', 300),
                'currency': intent_data.get('currency', 'EUR'),
                'adults': intent_data.get('adults', 2),
                'children': intent_data.get('children', 0),
                'checkin': checkin,
                'checkout': checkout
            })()
            
        else:
            # Si c'est déjà un objet Trip
            trip = intent_data
            logger.info(f"🎯 TRIP DÉTECTÉ (objet):")
            logger.info(f"   - Type: {trip.intent.trip_type}")
            logger.info(f"   - Destination: {trip.intent.destination}")
            logger.info(f"   - Budget: {trip.context.budget}")
        
        # ===== 3. Appliquer les overrides =====
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
        
        logger.info(f"📅 Dates finales: checkin={trip.context.checkin}, checkout={trip.context.checkout}")
        
        # ===== 4. Récupérer les hôtels =====
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
        
        # ===== 5. Enrichir avec les distances =====
        hotels = await enrich_distances(hotels, trip)
        
        # ===== 6. Calculer les scores =====
        scored = await score_hotels(hotels, trip)
        
        if not scored:
            return _empty(trip, "Aucun hôtel disponible avec des prix dans votre budget")
        
        # ===== 7. Sélection des recommandations =====
        recommendations = _select_diverse_recommendations(scored, trip)
        
        trip.scored_hotels = scored
        trip.recommendations = recommendations
        
        # ===== 8. Générer les explications =====
        trip.explanations = explain_recommendations(recommendations, trip)
        
        # ===== 9. Suggérer des activités =====
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
    """Sélectionne des recommandations DIVERSIFIÉES"""
    if not scored:
        return []
    
    trip_type = trip.intent.trip_type if hasattr(trip.intent, 'trip_type') else "leisure"
    budget = trip.context.budget if hasattr(trip.context, 'budget') else 250
    
    recommendations = []
    scored_copy = scored.copy()
    
    # 1. Le MEILLEUR hôtel
    if scored_copy:
        recommendations.append(scored_copy[0])
        scored_copy.pop(0)
    
    # 2. Un hôtel moins cher (si budget)
    if budget:
        cheap_hotels = [h for h in scored_copy if h.get("price", 0) < budget * 0.7]
        if cheap_hotels and len(recommendations) < 5:
            recommendations.append(cheap_hotels[0])
            scored_copy.remove(cheap_hotels[0])
    
    # 3. Un hôtel dans le budget
    mid_hotels = [h for h in scored_copy if budget * 0.7 <= h.get("price", 0) <= budget]
    if mid_hotels and len(recommendations) < 5:
        recommendations.append(mid_hotels[0])
        scored_copy.remove(mid_hotels[0])
    
    # 4. Un hôtel proche
    close_hotels = [h for h in scored_copy if h.get("distance_event_minutes", 99) < 10]
    if close_hotels and len(recommendations) < 5:
        recommendations.append(close_hotels[0])
        scored_copy.remove(close_hotels[0])
    
    # 5. Pour les familles : appartement/suite
    if trip_type == "family":
        apartment_hotels = [h for h in scored_copy if any(
            word in h.get("name", "").lower() 
            for word in ["appart", "suite", "residence", "apartment"]
        )]
        if apartment_hotels and len(recommendations) < 5:
            recommendations.append(apartment_hotels[0])
            scored_copy.remove(apartment_hotels[0])
    
    # Compléter avec les meilleurs restants
    while len(recommendations) < 5 and scored_copy:
        recommendations.append(scored_copy[0])
        scored_copy.pop(0)
    
    return recommendations[:5]


def _empty(trip: Trip, message: str = "No hotel found."):
    data = trip.to_dict() if hasattr(trip, 'to_dict') else {}
    data["recommendations"] = []
    data["message"] = message
    return data
