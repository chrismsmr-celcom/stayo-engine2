"""
Activities Engine — Suggestions selon le type de voyage.
"""

from engine.core.trip import Trip

ACTIVITIES_MAP = {
    "business": ["coworking", "restaurant d'affaires", "bar lounge", "salle de sport"],
    "romantic": ["spa", "diner romantique", "croisiere", "visite guidee privee", "degustation de vin"],
    "family": ["parc d'attractions", "zoo", "aquarium", "restaurant familial", "musee pour enfants"],
    "backpacker": ["visite gratuite", "street food", "auberge de jeunesse", "marche local"],
    "leisure": ["musee", "visite guidee", "shopping", "restaurant local", "parc"]
}


def suggest_activities(trip: Trip) -> list:
    base = ACTIVITIES_MAP.get(trip.intent.trip_type, ACTIVITIES_MAP["leisure"])
    # Ajouter les suggestions de DeepSeek si disponibles
    if trip.suggested_activities:
        combined = trip.suggested_activities + [a for a in base if a not in trip.suggested_activities]
        return combined[:6]
    return base[:4]