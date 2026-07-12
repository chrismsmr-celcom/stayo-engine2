"""
Geo Engine — Distances et temps de trajet.
"""

import os
import httpx
from math import radians, sin, cos, sqrt, asin
import logging

logger = logging.getLogger(__name__)

ORS_KEY = os.getenv("OPENROUTESERVICE_KEY", "")


async def enrich_distances(hotels: list, trip) -> list:
    """
    Enrichit les hôtels avec les distances (en minutes) vers les points d'intérêt.
    
    Args:
        hotels: Liste des hôtels
        trip: Objet Trip avec context (peut être un dict ou un objet)
    
    Returns:
        Liste des hôtels enrichis avec distance_event_minutes et distance_family_minutes
    """
    if not hotels:
        return []
    
    # Extraire les coordonnées du trip (compatible dict et objet)
    event_lat, event_lng, family_lat, family_lng = _extract_coordinates(trip)
    
    # Si pas de coordonnées, retourner les hôtels sans distances
    if event_lat is None or event_lng is None:
        logger.warning("Aucune coordonnée dans le trip, distances non calculées")
        return hotels
    
    # Construire les origines (hôtels) et destinations (points d'intérêt)
    origins = [[h["lng"], h["lat"]] for h in hotels]
    destinations = [[event_lng, event_lat]]
    
    if family_lat is not None and family_lng is not None:
        destinations.append([family_lng, family_lat])
    
    # Calculer les durées
    if ORS_KEY:
        durations = await _ors_matrix(origins, destinations)
    else:
        durations = _haversine_matrix(origins, destinations)
    
    # Ajouter les distances aux hôtels
    for i, hotel in enumerate(hotels):
        if i < len(durations):
            # Distance vers l'événement (en minutes, convertie depuis les secondes)
            hotel["distance_event_minutes"] = round(durations[i][0] / 60, 1) if durations[i][0] is not None else None
            
            if len(destinations) > 1 and i < len(durations):
                hotel["distance_family_minutes"] = round(durations[i][1] / 60, 1) if durations[i][1] is not None else None
    
    return hotels


def _extract_coordinates(trip):
    """Extrait les coordonnées du trip (compatible dict et objet)"""
    if hasattr(trip, 'context'):
        context = trip.context
        if isinstance(context, dict):
            return (
                context.get("event_lat"),
                context.get("event_lng"),
                context.get("family_lat"),
                context.get("family_lng")
            )
        else:
            return (
                getattr(context, "event_lat", None),
                getattr(context, "event_lng", None),
                getattr(context, "family_lat", None),
                getattr(context, "family_lng", None)
            )
    elif isinstance(trip, dict):
        return (
            trip.get("event_lat"),
            trip.get("event_lng"),
            trip.get("family_lat"),
            trip.get("family_lng")
        )
    return (None, None, None, None)


async def _ors_matrix(origins, destinations):
    """Utilise l'API OpenRouteService pour calculer les distances"""
    if not ORS_KEY:
        logger.warning("ORS_KEY non configuré, utilisation de Haversine")
        return _haversine_matrix(origins, destinations)
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openrouteservice.org/v2/matrix/foot-walking",
                json={
                    "locations": origins + destinations,
                    "metrics": ["duration"],
                    "units": "m"
                },
                headers={"Authorization": ORS_KEY}
            )
            
            if response.status_code != 200:
                logger.warning(f"ORS API error: {response.status_code}, fallback sur Haversine")
                return _haversine_matrix(origins, destinations)
            
            data = response.json()
            n = len(origins)
            durations = []
            
            for i in range(n):
                row = []
                for j in range(len(destinations)):
                    val = data["durations"][i][n + j]
                    row.append(val)
                durations.append(row)
            
            return durations
    except Exception as e:
        logger.warning(f"ORS API exception: {e}, fallback sur Haversine")
        return _haversine_matrix(origins, destinations)


def _haversine_matrix(origins, destinations):
    """Calcule les distances avec la formule de Haversine (en km puis converties en minutes)"""
    def haversine(lat1, lng1, lat2, lng2):
        R = 6371  # Rayon de la Terre en km
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
        return R * 2 * asin(sqrt(a))
    
    durations = []
    for o in origins:
        row = []
        for d in destinations:
            # Convertir km en minutes (environ 12 km/h en moyenne)
            minutes = haversine(o[1], o[0], d[1], d[0]) * 12 * 60
            row.append(minutes)
        durations.append(row)
    
    return durations
