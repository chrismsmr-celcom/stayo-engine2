"""
STAYO Geo Engine
Gestion des distances, temps de trajet et contexte géographique.

Fonctions :
- Calcul distance hôtel -> lieux importants
- Temps de trajet réel via OpenRouteService
- Fallback Haversine
- Score géographique pour le ranking
"""

import os
import httpx

from math import radians, sin, cos, sqrt, asin

from engine.core.trip import Trip


ORS_KEY = os.getenv("OPENROUTESERVICE_KEY")


ORS_BASE_URL = (
    "https://api.openrouteservice.org/v2/matrix/"
)


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------


async def enrich_distances(
    hotels: list,
    trip: Trip
) -> list:

    """
    Ajoute les informations géographiques
    à chaque hôtel.
    """

    if not trip.context.event_lat or not trip.context.event_lng:

        return hotels


    destinations = _build_destinations(trip)


    origins = []


    for hotel in hotels:

        lat = hotel.get("lat")

        lng = hotel.get("lng")


        if lat and lng:

            origins.append(
                [
                    lng,
                    lat
                ]
            )

        else:

            origins.append(None)



    origins_clean = [
        o for o in origins if o
    ]


    if not origins_clean:

        return hotels



    profile = _select_profile(trip)



    if ORS_KEY:

        durations = await _ors_matrix(

            origins_clean,

            destinations,

            profile

        )

    else:

        durations = _haversine_matrix(

            origins_clean,

            destinations

        )



    index = 0


    for hotel in hotels:


        if origins[index] is None:

            continue



        times = durations[index]



        hotel["distance_event_minutes"] = round(

            times[0] / 60,

            1

        )


        hotel["geo_profile"] = profile



        if len(times) > 1:

            hotel["distance_family_minutes"] = round(

                times[1] / 60,

                1

            )



        hotel["geo_score"] = _geo_score(

            hotel,

            trip

        )


        index += 1



    return hotels



# --------------------------------------------------
# DESTINATIONS
# --------------------------------------------------


def _build_destinations(trip: Trip):

    """
    Crée la liste des points importants.
    """

    points = []


    # lieu principal

    points.append(

        [

            trip.context.event_lng,

            trip.context.event_lat

        ]

    )


    # famille / deuxième lieu

    if (

        trip.context.family_lat

        and

        trip.context.family_lng

    ):

        points.append(

            [

                trip.context.family_lng,

                trip.context.family_lat

            ]

        )


    return points



# --------------------------------------------------
# TRANSPORT PROFILE
# --------------------------------------------------


def _select_profile(trip: Trip):

    """
    Choisit le mode de transport.
    """

    trip_type = (

        trip.context.trip_type

        or

        "leisure"

    )


    if trip_type == "business":

        return "driving-car"


    if trip_type == "family":

        return "driving-car"


    if trip_type == "backpacker":

        return "foot-walking"


    return "foot-walking"
    # --------------------------------------------------
# OPENROUTESERVICE MATRIX
# --------------------------------------------------


async def _ors_matrix(
    origins: list,
    destinations: list,
    profile: str
):

    """
    Récupère les temps de trajet réels
    via OpenRouteService.
    """

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:


            response = await client.post(

                f"{ORS_BASE_URL}{profile}",

                headers={

                    "Authorization": ORS_KEY,

                    "Content-Type": "application/json"

                },

                json={

                    "locations":

                        origins + destinations,

                    "metrics":

                        ["duration"],

                    "units":

                        "m"

                }

            )


        if response.status_code != 200:

            return _haversine_matrix(

                origins,

                destinations

            )


        data = response.json()


        durations = data.get(
            "durations",
            []
        )


        result = []


        destination_start = len(origins)


        for i in range(len(origins)):

            row = []


            for j in range(len(destinations)):


                try:

                    value = durations[i][destination_start + j]

                except Exception:

                    value = None



                if value is None:

                    value = 999999



                row.append(value)



            result.append(row)



        return result



    except Exception as e:


        print(
            f"ORS error : {e}"
        )


        return _haversine_matrix(

            origins,

            destinations

        )





# --------------------------------------------------
# HAVERSINE FALLBACK
# --------------------------------------------------


def _haversine_matrix(
    origins,
    destinations
):

    """
    Estimation quand ORS n'est pas disponible.

    Conversion approximative :
    distance km -> minutes voiture.
    """

    result = []


    for origin in origins:


        row = []


        for destination in destinations:


            distance = _haversine(

                origin[1],

                origin[0],

                destination[1],

                destination[0]

            )


            # estimation voiture :
            # 30 km/h en ville

            minutes = (

                distance / 30

            ) * 60



            row.append(

                minutes * 60

            )



        result.append(row)



    return result





def _haversine(
    lat1,
    lng1,
    lat2,
    lng2
):

    """
    Distance GPS en kilomètres.
    """

    R = 6371


    dlat = radians(
        lat2 - lat1
    )

    dlng = radians(
        lng2 - lng1
    )


    a = (

        sin(dlat / 2) ** 2

        +

        cos(radians(lat1))

        *

        cos(radians(lat2))

        *

        sin(dlng / 2) ** 2

    )


    return R * 2 * asin(
        sqrt(a)
    )
    # --------------------------------------------------
# GEO SCORE
# --------------------------------------------------


def _geo_score(
    hotel,
    trip: Trip
):

    """
    Score géographique global.

    Plus le logement est pratique
    pour le voyageur, plus le score est élevé.
    """

    score = 100


    event_time = hotel.get(
        "distance_event_minutes"
    )


    family_time = hotel.get(
        "distance_family_minutes"
    )



    # Importance du lieu principal

    if event_time is not None:


        if event_time <= 5:

            score += 0


        elif event_time <= 10:

            score -= 5


        elif event_time <= 20:

            score -= 15


        elif event_time <= 30:

            score -= 30


        else:

            score -= 50



    # Deuxième lieu important

    if family_time is not None:


        if family_time <= 15:

            score += 5


        elif family_time <= 30:

            score -= 5


        elif family_time > 45:

            score -= 15



    return max(
        0,
        min(score,100)
    )





# --------------------------------------------------
# CENTRE DE GRAVITE DU VOYAGE
# --------------------------------------------------


def calculate_trip_center(
    trip: Trip
):

    """
    Calcule le point géographique moyen
    du voyage.

    Exemple :

    Conférence La Défense 70%

    Famille Clamart 30%

    """

    points = []


    weights = []



    if (

        trip.context.event_lat

        and

        trip.context.event_lng

    ):

        points.append(

            (

                trip.context.event_lat,

                trip.context.event_lng

            )

        )


        weights.append(0.7)



    if (

        trip.context.family_lat

        and

        trip.context.family_lng

    ):

        points.append(

            (

                trip.context.family_lat,

                trip.context.family_lng

            )

        )


        weights.append(0.3)



    if not points:

        return None



    lat = 0

    lng = 0



    for i, point in enumerate(points):

        lat += point[0] * weights[i]

        lng += point[1] * weights[i]



    return {

        "lat": lat,

        "lng": lng

    }





# --------------------------------------------------
# VOYAGE COMPLEXITY SCORE
# --------------------------------------------------


def calculate_trip_complexity(
    trip: Trip
):

    """
    Mesure la difficulté du voyage.

    Plus il y a de contraintes,
    plus Stayo doit être intelligent.
    """

    complexity = 0



    if trip.context.event:

        complexity += 20



    if trip.context.family_lat:

        complexity += 20



    if len(
        trip.context.preferences
    ) > 3:

        complexity += 20



    if trip.context.budget:

        complexity += 10



    if trip.context.trip_type:

        complexity += 10



    return min(
        complexity,
        100
    )
