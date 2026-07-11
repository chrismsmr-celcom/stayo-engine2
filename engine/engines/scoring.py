"""
STAYO Scoring Engine
Version 2.0 - Modulaire et fiable
"""

from engine.core.trip import Trip
import logging

logger = logging.getLogger(__name__)


class ScoredHotel:
    """Conteneur pour les scores d'un hôtel"""
    
    def __init__(self, hotel):
        self.hotel = hotel
        self.scores = {}
        self.total = 0
        self.confidence = 100
        self.reasons = []
        self.warnings = []


# ============================================================
# PUBLIC - Point d'entrée principal
# ============================================================

async def score_hotels(hotels: list, trip) -> list:
    """
    Calcule les scores pour tous les hôtels
    
    Args:
        hotels: Liste des hôtels à scorer
        trip: Objet Trip contenant le contexte
    
    Returns:
        Liste des hôtels enrichis avec scores
    """
    if not hotels:
        return []
    
    # Déterminer le type de voyage
    trip_type = trip.intent.get("trip_type", "leisure") if hasattr(trip, 'intent') else "leisure"
    weights = _weights(trip_type)
    
    results = []
    
    for hotel in hotels:
        sh = ScoredHotel(hotel)
        
        # Calculer chaque score
        sh.scores["location"] = _location_score(hotel, trip, sh)
        sh.scores["price"] = _price_score(hotel, trip, sh)
        sh.scores["quality"] = _quality_score(hotel, sh)
        sh.scores["preferences"] = _preferences_score(hotel, trip, sh)
        sh.scores["transport"] = _transport_score(hotel, sh)
        sh.scores["experience"] = _experience_score(hotel, trip, sh)
        
        # Calculer le score pondéré
        weighted_sum = 0
        total_weight = 0
        
        for key, value in sh.scores.items():
            w = weights.get(key, 1)
            weighted_sum += value * w
            total_weight += w
        
        sh.total = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0
        
        # Calculer la confiance
        sh.confidence = _confidence(hotel, trip)
        
        # Ajouter les métadonnées à l'hôtel
        hotel["score"] = sh.total
        hotel["confidence"] = sh.confidence
        hotel["score_details"] = sh.scores
        hotel["reasons"] = sh.reasons
        hotel["warnings"] = sh.warnings
        
        results.append(hotel)
    
    # Trier par score, puis confiance, puis rating
    results.sort(
        key=lambda x: (
            x.get("score", 0),
            x.get("confidence", 0),
            x.get("rating", 0)
        ),
        reverse=True
    )
    
    return results


# ============================================================
# FONCTIONS DE SCORING INDIVIDUELLES
# ============================================================

def _location_score(hotel, trip, sh) -> float:
    """Score basé sur la distance au lieu principal"""
    minutes = hotel.get("distance_event_minutes", 999)
    
    if minutes is None:
        minutes = 999
    
    if minutes <= 5:
        sh.reasons.append("À moins de 5 min du lieu principal")
        return 100.0
    elif minutes <= 10:
        sh.reasons.append("Très proche de votre destination")
        return 90.0
    elif minutes <= 20:
        return 75.0
    elif minutes <= 30:
        sh.warnings.append("Temps de trajet moyen")
        return 55.0
    else:
        sh.warnings.append(f"Éloigné de votre destination ({minutes} min)")
        return 25.0


def _price_score(hotel, trip, sh) -> float:
    """Score basé sur le prix par rapport au budget"""
    price = hotel.get("price")
    budget = trip.context.get("budget") if hasattr(trip, 'context') else None
    
    if price is None:
        sh.warnings.append("Prix indisponible")
        return 50.0
    
    if budget is None or budget <= 0:
        return 70.0
    
    ratio = price / budget
    
    if ratio <= 0.6:
        sh.reasons.append("Excellent rapport qualité/prix")
        return 100.0
    elif ratio <= 0.8:
        return 90.0
    elif ratio <= 1.0:
        return 80.0
    elif ratio <= 1.2:
        return 65.0
    else:
        sh.warnings.append(f"Au-dessus du budget ({price:.2f} > {budget:.2f})")
        return 30.0


def _quality_score(hotel, sh) -> float:
    """Score basé sur la note et le nombre d'avis"""
    rating = hotel.get("rating", 0)
    reviews = hotel.get("reviewCount", 0)
    
    # Score de base
    if rating > 0:
        score = rating * 10  # 0-50 pour rating 0-5
    else:
        score = 30
    
    # Bonus pour les avis nombreux
    if reviews > 1000:
        score += 20
    elif reviews > 300:
        score += 10
    elif reviews > 100:
        score += 5
    
    # Bonus pour très bonne note
    if rating >= 4.5:
        sh.reasons.append("Très bien noté par les voyageurs")
        score += 10
    elif rating >= 4.0:
        sh.reasons.append("Bien noté par les voyageurs")
        score += 5
    elif rating < 2.0 and rating > 0:
        sh.warnings.append("Note faible")
    
    return min(score, 100)


def _preferences_score(hotel, trip, sh) -> float:
    """Score basé sur les préférences du voyageur"""
    # Récupérer les préférences
    preferences = trip.intent.get("must_have", []) if hasattr(trip, 'intent') else []
    
    if not preferences:
        return 70.0
    
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    
    score = 60
    matched = 0
    
    for pref in preferences:
        if any(pref.lower() in f for f in facilities):
            score += 10
            matched += 1
            sh.reasons.append(f"{pref} disponible")
        else:
            score -= 5
            sh.warnings.append(f"Pas de {pref}")
    
    # Bonus si toutes les préférences sont satisfaites
    if matched == len(preferences) and len(preferences) > 0:
        score += 10
        sh.reasons.append("Toutes vos préférences sont satisfaites")
    
    return max(0, min(score, 100))


def _transport_score(hotel, sh) -> float:
    """Score basé sur les options de transport disponibles"""
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    
    score = 40  # Score de base
    
    transport_keywords = {
        "metro": 15,
        "subway": 15,
        "bus": 10,
        "train": 12,
        "parking": 10,
        "airport": 12,
        "shuttle": 10,
        "taxi": 5,
        "car rental": 8
    }
    
    for keyword, points in transport_keywords.items():
        if any(keyword in f for f in facilities):
            score += points
            if points >= 12:
                sh.reasons.append(f"Accès {keyword} disponible")
    
    return min(score, 100)


def _experience_score(hotel, trip, sh) -> float:
    """Score basé sur l'expérience spécifique au type de voyage"""
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    trip_type = trip.intent.get("trip_type", "leisure") if hasattr(trip, 'intent') else "leisure"
    
    score = 50
    
    if trip_type == "business":
        # Wifi haut débit
        if any("wifi" in f for f in facilities):
            score += 15
            sh.reasons.append("Wi-Fi disponible")
        if any("business" in f for f in facilities):
            score += 15
            sh.reasons.append("Équipé pour les voyageurs d'affaires")
        if any("meeting" in f for f in facilities):
            score += 10
            sh.reasons.append("Salles de réunion disponibles")
        if any("quiet" in f for f in facilities) or any("calme" in f for f in facilities):
            score += 10
            sh.reasons.append("Environnement calme")
            
    elif trip_type == "romantic":
        if any("spa" in f for f in facilities):
            score += 20
            sh.reasons.append("Spa pour un moment détente")
        if any("restaurant" in f for f in facilities):
            score += 15
            sh.reasons.append("Restaurant sur place")
        if any("bar" in f for f in facilities):
            score += 10
            sh.reasons.append("Bar pour un verre en amoureux")
        if any("view" in f for f in facilities) or any("vue" in f for f in facilities):
            score += 15
            sh.reasons.append("Vue magnifique")
            
    elif trip_type == "family":
        if any("pool" in f for f in facilities):
            score += 20
            sh.reasons.append("Piscine pour toute la famille")
        if any("family" in f for f in facilities):
            score += 15
            sh.reasons.append("Adapté aux familles")
        if any("kids" in f for f in facilities) or any("children" in f for f in facilities):
            score += 15
            sh.reasons.append("Activités pour enfants")
        if any("parking" in f for f in facilities):
            score += 10
            sh.reasons.append("Parking disponible")
            
    elif trip_type == "backpacker":
        if any("wifi" in f for f in facilities):
            score += 20
            sh.reasons.append("Wi-Fi gratuit")
        if any("luggage" in f for f in facilities) or any("bagagerie" in f for f in facilities):
            score += 15
            sh.reasons.append("Bagagerie disponible")
        if any("kitchen" in f for f in facilities) or any("cuisine" in f for f in facilities):
            score += 15
            sh.reasons.append("Cuisine pour cuisiner")
        if any("social" in f for f in facilities) or any("bar" in f for f in facilities):
            score += 10
            sh.reasons.append("Ambiance sociale")
    
    else:  # leisure
        if any("pool" in f for f in facilities):
            score += 15
        if any("restaurant" in f for f in facilities):
            score += 10
        if any("bar" in f for f in facilities):
            score += 10
        if any("gym" in f for f in facilities) or any("fitness" in f for f in facilities):
            score += 10
        if any("spa" in f for f in facilities):
            score += 10
    
    return min(score, 100)


# ============================================================
# WEIGHTS - Poids par type de voyage
# ============================================================

def _weights(trip_type: str) -> dict:
    """Retourne les poids pour un type de voyage donné"""
    
    weights_map = {
        "business": {
            "location": 3,
            "price": 1.5,
            "quality": 1.5,
            "preferences": 2,
            "transport": 2.5,
            "experience": 3
        },
        "romantic": {
            "location": 1.5,
            "price": 1,
            "quality": 2,
            "preferences": 2,
            "transport": 1,
            "experience": 3
        },
        "family": {
            "location": 2,
            "price": 2,
            "quality": 1.5,
            "preferences": 2,
            "transport": 1.5,
            "experience": 3
        },
        "backpacker": {
            "location": 2,
            "price": 4,
            "quality": 1,
            "preferences": 1,
            "transport": 2,
            "experience": 1
        },
        "leisure": {
            "location": 2,
            "price": 2,
            "quality": 2,
            "preferences": 2,
            "transport": 2,
            "experience": 2
        }
    }
    
    return weights_map.get(trip_type, weights_map["leisure"])


# ============================================================
# CONFIDENCE - Niveau de confiance du score
# ============================================================

def _confidence(hotel, trip) -> float:
    """Calcule le niveau de confiance du score"""
    confidence = 100
    
    # Pénalités pour données manquantes
    if trip.context.get("budget") is None:
        confidence -= 10
        logger.debug("Confiance réduite: budget manquant")
    
    if trip.context.get("event_lat") is None or trip.context.get("event_lng") is None:
        confidence -= 20
        logger.debug("Confiance réduite: coordonnées manquantes")
    
    if hotel.get("price") is None:
        confidence -= 20
        logger.debug("Confiance réduite: prix manquant")
    
    if hotel.get("rating") is None or hotel.get("rating") == 0:
        confidence -= 10
        logger.debug("Confiance réduite: note manquante")
    
    if hotel.get("distance_event_minutes") is None:
        confidence -= 20
        logger.debug("Confiance réduite: distance manquante")
    
    # Pénalité si peu d'avis
    review_count = hotel.get("reviewCount", 0)
    if review_count < 10:
        confidence -= 10
    elif review_count < 50:
        confidence -= 5
    
    return max(0, min(100, confidence))
