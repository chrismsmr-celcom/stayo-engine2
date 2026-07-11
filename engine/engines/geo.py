"""
Geo Engine — Distances et temps de trajet.
"""

import os, httpx
from math import radians, sin, cos, sqrt, asin
from engine.core.trip import Trip

ORS_KEY = os.getenv("OPENROUTESERVICE_KEY")


async def enrich_distances(hotels: list, trip: Trip) -> list:
    if not trip.context.event_lat or not trip.context.event_lng:
        return hotels

    origins = [[h["lng"], h["lat"]] for h in hotels]
    destinations = [[trip.context.event_lng, trip.context.event_lat]]
    if trip.context.family_lat:
        destinations.append([trip.context.family_lng, trip.context.family_lat])

    durations = await _ors_matrix(origins, destinations) if ORS_KEY else _haversine_matrix(origins, destinations)

    for i, hotel in enumerate(hotels):
        if i < len(durations):
            hotel["distance_event_minutes"] = round(durations[i][0] / 60, 1)
            if len(destinations) > 1:
                hotel["distance_family_minutes"] = round(durations[i][1] / 60, 1)
    return hotels


async def _ors_matrix(origins, destinations):
    async with httpx.AsyncClient() as c:
        r = await c.post("https://api.openrouteservice.org/v2/matrix/foot-walking",
            json={"locations": origins + destinations, "metrics": ["duration"], "units": "m"},
            headers={"Authorization": ORS_KEY})
    if r.status_code != 200: return _haversine_matrix(origins, destinations)
    data = r.json()
    return [[data["durations"][i][len(origins) + j] for j in range(len(destinations))] for i in range(len(origins))]


def _haversine_matrix(origins, destinations):
    def haversine(lat1, lng1, lat2, lng2):
        R = 6371; dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
        return R * 2 * asin(sqrt(a))
    return [[haversine(o[1], o[0], d[1], d[0]) * 12 * 60 for d in destinations] for o in origins]