"""
Hotel Features Engine - Extraction des caractéristiques des hôtels
Version 1.0
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def extract_features(hotel: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les caractéristiques clés d'un hôtel pour le scoring.
    
    Args:
        hotel: Dictionnaire contenant les données de l'hôtel
    
    Returns:
        Dictionnaire avec les scores et caractéristiques extraits
    """
    if not hotel:
        return _default_features()
    
    # Récupérer les équipements
    facilities = hotel.get("hotelFacilities", [])
    if isinstance(facilities, str):
        facilities = [facilities]
    elif not isinstance(facilities, list):
        facilities = []
    
    facilities_lower = [f.lower() for f in facilities]
    
    # Calculer les scores
    features = {
        # Scores par type de voyage
        "business_score": _calculate_business_score(facilities_lower),
        "romantic_score": _calculate_romantic_score(facilities_lower),
        "family_score": _calculate_family_score(facilities_lower),
        "comfort_score": _calculate_comfort_score(facilities_lower),
        "luxury_score": _calculate_luxury_score(facilities_lower),
        
        # Caractéristiques booléennes
        "has_wifi": any("wifi" in f for f in facilities_lower),
        "has_pool": any("pool" in f for f in facilities_lower),
        "has_spa": any("spa" in f for f in facilities_lower),
        "has_restaurant": any("restaurant" in f for f in facilities_lower),
        "has_parking": any("parking" in f for f in facilities_lower),
        "has_gym": any("gym" in f for f in facilities_lower) or any("fitness" in f for f in facilities_lower),
        "has_business_center": any("business" in f for f in facilities_lower) or any("meeting" in f for f in facilities_lower),
        "is_family_friendly": any("family" in f for f in facilities_lower) or any("kids" in f for f in facilities_lower),
        "has_airport_shuttle": any("shuttle" in f for f in facilities_lower) or any("airport" in f for f in facilities_lower),
        "has_view": any("view" in f for f in facilities_lower) or any("vue" in f for f in facilities_lower) or any("balcony" in f for f in facilities_lower),
        
        # Métadonnées
        "features": facilities,
        "rating": hotel.get("rating", 0),
        "review_count": hotel.get("reviewCount", 0),
        "stars": hotel.get("stars", 0),
    }
    
    logger.debug(f"Features extraites pour {hotel.get('name', 'inconnu')}")
    
    return features


def _default_features() -> Dict[str, Any]:
    """Retourne des features par défaut"""
    return {
        "business_score": 50,
        "romantic_score": 50,
        "family_score": 50,
        "comfort_score": 50,
        "luxury_score": 50,
        "has_wifi": False,
        "has_pool": False,
        "has_spa": False,
        "has_restaurant": False,
        "has_parking": False,
        "has_gym": False,
        "has_business_center": False,
        "is_family_friendly": False,
        "has_airport_shuttle": False,
        "has_view": False,
        "features": [],
        "rating": 0,
        "review_count": 0,
        "stars": 0
    }


def _calculate_business_score(facilities: List[str]) -> int:
    """Calcule le score pour les voyageurs d'affaires"""
    score = 50
    if any("wifi" in f for f in facilities):
        score += 15
    if any("business" in f for f in facilities):
        score += 15
    if any("meeting" in f for f in facilities) or any("salle" in f for f in facilities):
        score += 10
    if any("calme" in f for f in facilities) or any("quiet" in f for f in facilities):
        score += 10
    if any("restaurant" in f for f in facilities):
        score += 5
    if any("bar" in f for f in facilities):
        score += 5
    if any("parking" in f for f in facilities):
        score += 5
    if any("shuttle" in f for f in facilities) or any("airport" in f for f in facilities):
        score += 5
    return min(score, 100)


def _calculate_romantic_score(facilities: List[str]) -> int:
    """Calcule le score pour les voyages romantiques"""
    score = 50
    if any("spa" in f for f in facilities):
        score += 20
    if any("restaurant" in f for f in facilities):
        score += 15
    if any("bar" in f for f in facilities):
        score += 10
    if any("view" in f for f in facilities) or any("vue" in f for f in facilities):
        score += 15
    if any("balcony" in f for f in facilities) or any("balcon" in f for f in facilities):
        score += 10
    if any("room service" in f for f in facilities) or any("service en chambre" in f for f in facilities):
        score += 10
    if any("pool" in f for f in facilities):
        score += 5
    return min(score, 100)


def _calculate_family_score(facilities: List[str]) -> int:
    """Calcule le score pour les voyages en famille"""
    score = 50
    if any("pool" in f for f in facilities):
        score += 20
    if any("family" in f for f in facilities) or any("familial" in f for f in facilities):
        score += 20
    if any("kids" in f for f in facilities) or any("children" in f for f in facilities):
        score += 15
    if any("parking" in f for f in facilities):
        score += 10
    if any("restaurant" in f for f in facilities):
        score += 10
    if any("playground" in f for f in facilities) or any("aire de jeu" in f for f in facilities):
        score += 10
    if any("babysitting" in f for f in facilities):
        score += 5
    return min(score, 100)


def _calculate_comfort_score(facilities: List[str]) -> int:
    """Calcule le score de confort général"""
    score = 50
    if any("air conditioning" in f for f in facilities) or any("climatisation" in f for f in facilities):
        score += 10
    if any("heating" in f for f in facilities) or any("chauffage" in f for f in facilities):
        score += 5
    if any("24h" in f for f in facilities) or any("24/7" in f for f in facilities):
        score += 10
    if any("room service" in f for f in facilities) or any("service en chambre" in f for f in facilities):
        score += 10
    if any("wifi" in f for f in facilities):
        score += 10
    if any("restaurant" in f for f in facilities):
        score += 5
    if any("bar" in f for f in facilities):
        score += 5
    if any("parking" in f for f in facilities):
        score += 5
    return min(score, 100)


def _calculate_luxury_score(facilities: List[str]) -> int:
    """Calcule le score de luxe"""
    score = 50
    if any("spa" in f for f in facilities):
        score += 20
    if any("restaurant" in f for f in facilities):
        score += 15
    if any("bar" in f for f in facilities):
        score += 10
    if any("view" in f for f in facilities) or any("vue" in f for f in facilities):
        score += 10
    if any("pool" in f for f in facilities):
        score += 10
    if any("fitness" in f for f in facilities) or any("gym" in f for f in facilities):
        score += 5
    if any("concierge" in f for f in facilities):
        score += 10
    if any("valet" in f for f in facilities):
        score += 5
    if any("limousine" in f for f in facilities):
        score += 5
    return min(score, 100)


# Alias pour compatibilité
def extract_hotel_features(hotel: Dict[str, Any]) -> Dict[str, Any]:
    """Alias pour extract_features"""
    return extract_features(hotel)
