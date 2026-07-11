"""
STAYO Recommendation Engine
Orchestrateur principal du moteur de recommandation.
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
    traveler_id: str = None
) -> dict:

    start = time.perf_counter()

    try:

        logger.info("Starting recommendation engine")

        #
        # 1 - Comprendre le voyage
        #

        trip = await parse_intent(
            query=query,
            traveler_id=traveler_id
        )

        #
        # 2 - Recherche hôtels
        #

        hotels = await fetch_hotels(

            latitude=trip.context.event_lat,

            longitude=trip.context.event_lng,

            checkin=trip.context.checkin,

            checkout=trip.context.checkout,

            adults=trip.context.adults,

            currency=trip.context.currency

        )

        trip.total_found = len(hotels)

        if len(hotels) == 0:

            return _empty(trip)

        #
        # 3 - Calcul des distances
        #

        hotels = await enrich_distances(

            hotels,

            trip

        )

        #
        # 4 - Calcul du score
        #

        scored = score_hotels(

            trip,

            hotels

        )

        trip.scored_hotels = scored

        trip.recommendations = scored[:5]

        #
        # 5 - Explications
        #

        trip.explanations = explain_recommendations(

            scored[:5],

            trip

        )

        #
        # 6 - Activités
        #

        trip.suggested_activities = suggest_activities(trip)

        #
        # 7 - Temps d'exécution
        #

        trip.processing_time_ms = round(

            (time.perf_counter() - start) * 1000,

            2

        )

        logger.info(

            "Recommendation completed in %sms",

            trip.processing_time_ms

        )

        return trip.to_dict()

    except Exception:

        logger.exception("Recommendation Engine Error")

        raise


def _empty(trip: Trip):

    trip.processing_time_ms = 0

    data = trip.to_dict()

    data["recommendations"] = []

    data["message"] = "No hotel found."

    return data
