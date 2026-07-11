"""
STAYO Scoring Engine
Version 2.1 - Corrigé et optimisé
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScoredHotel:
    """Conteneur pour les scores d'un hôtel"""
    
    def __init__(self, hotel: Dict[str, Any]):
        self.hotel = hotel
        self.scores: Dict[str, float] = {}
        self.total: float = 0.0
        self.confidence: int = 100
        self.reasons: List[str] = []
        self.warnings: List[str] = []


# ============================================================
# PUBLIC - Point d'entrée principal
# ============================================================

def score_hotels(trip, hotels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calcule les scores pour tous les hôtels
    
    Args:
        trip: Objet Trip contenant le contexte (peut être un dict ou un objet)
        hotels: Liste des hôtels à scorer
    
    Returns:
        Liste des hôtels enrichis avec scores
    """
    if not hotels:
        return []
    
    # Déterminer le type de voyage (compatible dict et objet)
    trip_type = _get_trip_type(trip)
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
        sh.scores["trip"] = _trip_score(hotel, trip, sh)
        
        # Calculer le score pondéré
        weighted_sum = 0.0
        total_weight = 0.0
        
        for key, value in sh.scores.items():
            w = weights.get(key, 1.0)
            weighted_sum += value * w
            total_weight += w
        
        sh.total = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0
        
        # Calculer la confiance
        sh.confidence = _confidence(trip, hotel)
        
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
# FONCTIONS UTILITAIRES
# ============================================================

def _get_trip_type(trip) -> str:
    """Extrait le type de voyage d'un objet Trip ou d'un dict"""
    if hasattr(trip, 'intent') and isinstance(trip.intent, dict):
        return trip.intent.get("trip_type", "leisure")
    elif hasattr(trip, 'context') and hasattr(trip.context, 'trip_type'):
        return trip.context.trip_type or "leisure"
    elif isinstance(trip, dict):
        return trip.get("trip_type", "leisure")
    return "leisure"


def _get_context(trip, key: str, default=None):
    """Extrait une valeur du contexte de façon compatible"""
    if hasattr(trip, 'context'):
        context = trip.context
        if isinstance(context, dict):
            return context.get(key, default)
        elif hasattr(context, key):
            return getattr(context, key, default)
    elif isinstance(trip, dict):
        return trip.get(key, default)
    return default


# ============================================================
# FONCTIONS DE SCORING
# ============================================================

def _location_score(hotel: Dict[str, Any], trip, sh: ScoredHotel) -> float:
    """Score basé sur la distance au lieu principal"""
    minutes = hotel.get("distance_event_minutes", 999)
    
    if minutes is None or minutes > 999:
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


def _price_score(hotel: Dict[str, Any], trip, sh: ScoredHotel) -> float:
    """Score basé sur le prix par rapport au budget"""
    price = hotel.get("price")
    budget = _get_context(trip, "budget", None)
    
    if price is None:
        sh.warnings.append("Prix indisponible")
        return 50.0
    
    if budget is None or budget <= 0:
        return 70.0
    
    try:
        ratio = float(price) / float(budget)
    except (TypeError, ValueError):
        sh.warnings.append("Prix invalide")
        return 50.0
    
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


def _quality_score(hotel: Dict[str, Any], sh: ScoredHotel) -> float:
    """Score basé sur la note et le nombre d'avis"""
    rating = hotel.get("rating", 0)
    reviews = hotel.get("reviewCount", 0)
    
    # Score de base (0-50 pour rating 0-5)
    if rating > 0:
        try:
            score = float(rating) * 18  # Max 90 pour 5 étoiles
        except (TypeError, ValueError):
            score = 30.0
    else:
        score = 30.0
    
    # Bonus pour les avis nombreux
    if reviews > 1000:
        score += 10
        sh.reasons.append("Très nombreux avis positifs")
    elif reviews > 300:
        score += 5
        sh.reasons.append("Nombreux avis")
    elif reviews > 50:
        score += 2
    
    # Bonus pour très bonne note
    if rating >= 4.5:
        sh.reasons.append("Très bien noté par les voyageurs")
        score += 10
    elif rating >= 4.0:
        sh.reasons.append("Bien noté par les voyageurs")
        score += 5
    elif rating < 2.0 and rating > 0:
        sh.warnings.append("Note faible")
    
    return min(score, 100.0)


def _preferences_score(hotel: Dict[str, Any], trip, sh: ScoredHotel) -> float:
    """Score basé sur les préférences du voyageur"""
    # Récupérer les préférences
    if hasattr(trip, 'intent') and isinstance(trip.intent, dict):
        prefs = trip.intent.get("must_have", [])
    elif hasattr(trip, 'context') and hasattr(trip.context, 'preferences'):
        prefs = trip.context.preferences or []
    elif isinstance(trip, dict):
        prefs = trip.get("preferences", [])
    else:
        prefs = []
    
    # Normaliser
    if isinstance(prefs, str):
        prefs = [prefs]
    elif not isinstance(prefs, list):
        prefs = []
    
    prefs = [p.lower() for p in prefs if p]
    
    if not prefs:
        return 70.0
    
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    
    score = 60.0
    matched = 0
    
    for pref in prefs:
        if any(pref in f for f in facilities):
            score += 10
            matched += 1
            sh.reasons.append(f"{pref} disponible")
        else:
            score -= 5
            sh.warnings.append(f"Pas de {pref}")
    
    # Bonus si toutes les préférences sont satisfaites
    if matched == len(prefs) and len(prefs) > 0:
        score += 10
        sh.reasons.append("Toutes vos préférences sont satisfaites")
    
    return max(0.0, min(score, 100.0))


def _transport_score(hotel: Dict[str, Any], sh: ScoredHotel) -> float:
    """Score basé sur les options de transport disponibles"""
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    
    score = 40.0
    
    transport_keywords = {
        "metro": 15,
        "subway": 15,
        "train": 12,
        "bus": 10,
        "parking": 10,
        "airport": 12,
        "shuttle": 10,
        "taxi": 5,
        "car rental": 8,
        "station": 5
    }
    
    for keyword, points in transport_keywords.items():
        if any(keyword in f for f in facilities):
            score += points
            if points >= 12:
                sh.reasons.append(f"Accès {keyword} disponible")
    
    return min(score, 100.0)


def _trip_score(hotel: Dict[str, Any], trip, sh: ScoredHotel) -> float:
    """
    Score basé sur l'adéquation au type de voyage
    """
    facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
    trip_type = _get_trip_type(trip)
    
    score = 50.0
    
    if trip_type == "business":
        if any("wifi" in f for f in facilities):
            score += 20
            sh.reasons.append("Wi-Fi haut débit")
        if any("business" in f for f in facilities):
            score += 15
            sh.reasons.append("Équipé pour les voyageurs d'affaires")
        if any("meeting" in f for f in facilities) or any("salle" in f for f in facilities):
            score += 15
            sh.reasons.append("Salles de réunion disponibles")
        if any("calme" in f for f in facilities) or any("quiet" in f for f in facilities):
            score += 10
            sh.reasons.append("Environnement calme")
            
    elif trip_type == "romantic":
        if any("spa" in f for f in facilities):
            score += 20
            sh.reasons.append("Spa pour un moment détente")
        if any("restaurant" in f for f in facilities):
            score += 15
            sh.reasons.append("Restaurant gastronomique")
        if any("bar" in f for f in facilities):
            score += 10
            sh.reasons.append("Bar lounge")
        if any("vue" in f for f in facilities) or any("view" in f for f in facilities):
            score += 15
            sh.reasons.append("Vue magnifique")
        if any("balcon" in f for f in facilities) or any("balcony" in f for f in facilities):
            score += 10
            sh.reasons.append("Balcon privé")
            
    elif trip_type == "family":
        if any("pool" in f for f in facilities):
            score += 20
            sh.reasons.append("Piscine pour toute la famille")
        if any("family" in f for f in facilities) or any("familial" in f for f in facilities):
            score += 20
            sh.reasons.append("Adapté aux familles")
        if any("kids" in f for f in facilities) or any("children" in f for f in facilities):
            score += 15
            sh.reasons.append("Activités pour enfants")
        if any("parking" in f for f in facilities):
            score += 10
            sh.reasons.append("Parking disponible")
        if any("restaurant" in f for f in facilities):
            score += 5
            sh.reasons.append("Restaurant sur place")
            
    elif trip_type == "backpacker":
        if any("wifi" in f for f in facilities):
            score += 20
            sh.reasons.append("Wi-Fi gratuit")
        if any("luggage" in f for f in facilities) or any("bagagerie" in f for f in facilities):
            score += 15
            sh.reasons.append("Bagagerie disponible")
        if any("kitchen" in f for f in facilities) or any("cuisine" in f for f in facilities):
            score += 15
            sh.reasons.append("Cuisine partagée")
        if any("bar" in f for f in facilities) or any("social" in f for f in facilities):
            score += 10
            sh.reasons.append("Ambiance sociale")
            
    else:  # leisure (par défaut)
        if any("pool" in f for f in facilities):
            score += 15
            sh.reasons.append("Piscine disponible")
        if any("restaurant" in f for f in facilities):
            score += 10
            sh.reasons.append("Restaurant sur place")
        if any("bar" in f for f in facilities):
            score += 10
            sh.reasons.append("Bar disponible")
        if any("gym" in f for f in facilities) or any("fitness" in f for f in facilities):
            score += 10
            sh.reasons.append("Salle de sport")
        if any("spa" in f for f in facilities):
            score += 10
            sh.reasons.append("Spa disponible")
    
    return min(score, 100.0)


# ============================================================
# WEIGHTS - Poids par type de voyage
# ============================================================

def _weights(trip_type: str) -> Dict[str, float]:
    """Retourne les poids pour un type de voyage donné"""
    
    weights_map = {
        "business": {
            "location": 3.0,
            "price": 1.5,
            "quality": 1.5,
            "preferences": 2.5,
            "transport": 2.5,
            "trip": 3.0
        },
        "romantic": {
            "location": 1.5,
            "price": 1.0,
            "quality": 2.0,
            "preferences": 2.0,
            "transport": 1.0,
            "trip": 3.0
        },
        "family": {
            "location": 2.0,
            "price": 2.0,
            "quality": 1.5,
            "preferences": 2.0,
            "transport": 1.5,
            "trip": 3.0
        },
        "backpacker": {
            "location": 2.0,
            "price": 4.0,
            "quality": 1.0,
            "preferences": 1.0,
            "transport": 2.0,
            "trip": 1.0
        },
        "leisure": {
            "location": 2.0,
            "price": 2.0,
            "quality": 2.0,
            "preferences": 2.0,
            "transport": 2.0,
            "trip": 2.0
        }
    }
    
    return weights_map.get(trip_type, weights_map["leisure"])


# ============================================================
# CONFIDENCE - Niveau de confiance du score
# ============================================================

def _confidence(trip, hotel: Dict[str, Any]) -> int:
    """Calcule le niveau de confiance du score (0-100)"""
    confidence = 100
    
    # Pénalités pour données manquantes
    budget = _get_context(trip, "budget", None)
    if budget is None:
        confidence -= 10
        logger.debug("Confiance réduite: budget manquant")
    
    lat = _get_context(trip, "event_lat", None)
    lng = _get_context(trip, "event_lng", None)
    if lat is None or lng is None:
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
