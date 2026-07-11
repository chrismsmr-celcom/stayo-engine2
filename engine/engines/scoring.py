"""
Scoring Engine — Score modulaire par catégorie.
Chaque catégorie est indépendante et pondérée selon le type de voyage.
"""

from engine.core.trip import Trip


class ScoredHotel:
    def __init__(self, hotel: dict):
        self.hotel = hotel
        self.scores = {}
        self.total = 0
        self.confidence = 100
        self.reasons = []
        self.warnings = []


def score_hotels(trip: Trip, hotels: list) -> list:
    """Calcule les scores modulaires pour chaque hôtel."""
    scored = []
    
    for hotel in hotels:
        sh = ScoredHotel(hotel)
        
        # Modules de scoring indépendants
        sh.scores["location"] = _location_score(hotel, trip)
        sh.scores["price"] = _price_score(hotel, trip)
        sh.scores["quality"] = _quality_score(hotel)
        sh.scores["amenities"] = _amenities_score(hotel, trip)
        sh.scores["transport"] = _transport_score(hotel, trip)
        sh.scores["lifestyle"] = _lifestyle_score(hotel, trip)
        
        # Pondération selon le type de voyage
        weights = _get_weights(trip.intent.trip_type)
        
        sh.total = round(sum(sh.scores[k] * weights.get(k, 1) for k in sh.scores) / sum(weights.values()), 1)
        sh.confidence = _calculate_confidence(trip, sh)
        
        sh.hotel["score"] = sh.total
        sh.hotel["confidence"] = sh.confidence
        sh.hotel["score_details"] = sh.scores
        sh.hotel["reasons"] = sh.reasons
        sh.hotel["warnings"] = sh.warnings
        
        scored.append(sh.hotel)
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def _location_score(hotel, trip):
    dist = hotel.get("distance_event_minutes", 999)
    if dist <= 5: return 100
    if dist <= 10: return 90
    if dist <= 15: return 75
    if dist <= 20: return 55
    if dist <= 30: return 35
    return 10


def _price_score(hotel, trip):
    price = hotel.get("price")
    budget = trip.context.budget
    if price is None: return 50
    if price <= budget * 0.5: return 100
    if price <= budget * 0.8: return 90
    if price <= budget: return 80
    if price <= budget * 1.3: return 50
    return 10


def _quality_score(hotel):
    rating = hotel.get("rating", 0)
    reviews = hotel.get("reviewCount", 0)
    base = rating * 10
    if reviews > 1000: base += 10
    elif reviews > 100: base += 5
    return min(100, base)


def _amenities_score(hotel, trip):
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    score = 50
    must = [m.lower() for m in trip.intent.must_have]
    for m in must:
        if any(m in f for f in facilities): score += 15
        else: score -= 10
    nice = [n.lower() for n in trip.intent.nice_to_have]
    for n in nice:
        if any(n in f for f in facilities): score += 5
    return max(0, min(100, score))


def _transport_score(hotel, trip):
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    score = 30
    if any("metro" in f or "subway" in f for f in facilities): score += 25
    if any("bus" in f for f in facilities): score += 15
    if any("parking" in f for f in facilities): score += 15
    if any("airport" in f or "shuttle" in f for f in facilities): score += 15
    return min(100, score)


def _lifestyle_score(hotel, trip):
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    score = 50
    if trip.intent.trip_type == "business":
        if any("wifi" in f or "internet" in f for f in facilities): score += 20
        if any("business" in f or "meeting" in f for f in facilities): score += 15
        if any("restaurant" in f for f in facilities): score += 15
    elif trip.intent.trip_type == "romantic":
        if any("spa" in f or "sauna" in f for f in facilities): score += 25
        if any("restaurant" in f or "bar" in f for f in facilities): score += 15
        if any("view" in f or "vue" in f for f in facilities): score += 10
    elif trip.intent.trip_type == "family":
        if any("pool" in f or "piscine" in f for f in facilities): score += 20
        if any("family" in f or "enfant" in f for f in facilities): score += 20
        if any("restaurant" in f for f in facilities): score += 10
    return min(100, score)


def _get_weights(trip_type):
    return {
        "business": {"location": 3, "price": 1.5, "quality": 1, "amenities": 2.5, "transport": 2.5, "lifestyle": 2},
        "romantic": {"location": 1, "price": 1, "quality": 2.5, "amenities": 2, "transport": 1, "lifestyle": 3},
        "family": {"location": 2, "price": 2, "quality": 1.5, "amenities": 2.5, "transport": 1.5, "lifestyle": 2.5},
        "backpacker": {"location": 1.5, "price": 3.5, "quality": 0.5, "amenities": 0.5, "transport": 2, "lifestyle": 1},
        "leisure": {"location": 2, "price": 2, "quality": 2, "amenities": 1.5, "transport": 1.5, "lifestyle": 2}
    }.get(trip_type, {"location": 2, "price": 1.5, "quality": 1.5, "amenities": 1.5, "transport": 1.5, "lifestyle": 1.5})


def _calculate_confidence(trip, scored):
    conf = 100
    if not trip.context.budget: conf -= 15
    if not trip.context.event: conf -= 20
    if scored.hotel.get("price") is None: conf -= 20
    if scored.hotel.get("rating", 0) == 0: conf -= 10
    if len(scored.reasons) < 2: conf -= 10
    return max(0, min(100, conf))