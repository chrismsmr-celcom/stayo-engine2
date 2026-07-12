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
    traveler_id: str | None = None
) -> dict:
    """
    Point d'entrée principal du moteur STAYO.
    """

    start = time.perf_counter()

    try:
        logger.info("Starting recommendation engine")

        # -------------------------------------------------
        # 1. Compréhension de la requête
        # -------------------------------------------------

        trip = await parse_intent(
            query=query,
            traveler_id=traveler_id
        )

        # -------------------------------------------------
        # 2. Recherche des hôtels
        # -------------------------------------------------

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
            return _empty(trip)

        # -------------------------------------------------
        # 3. Calcul des distances
        # -------------------------------------------------

        hotels = await enrich_distances(
            hotels,
            trip
        )

        # -------------------------------------------------
        # 4. Calcul des scores
        # -------------------------------------------------

        scored = score_hotels(
            trip,
            hotels
        )

        trip.scored_hotels = scored
        trip.recommendations = scored[:5]

        # -------------------------------------------------
        # 5. Explications
        # -------------------------------------------------

        trip.explanations = explain_recommendations(
            trip.recommendations,
            trip
        )

        # -------------------------------------------------
        # 6. Activités recommandées
        # -------------------------------------------------

        trip.suggested_activities = suggest_activities(trip)

        # -------------------------------------------------
        # 7. Temps d'exécution
        # -------------------------------------------------

        trip.processing_time_ms = round(
            (time.perf_counter() - start) * 1000,
            2
        )

        logger.info(
            "Recommendation completed in %.2f ms",
            trip.processing_time_ms
        )

        return trip.to_dict()

    except Exception:
        logger.exception("Recommendation Engine Error")
        raise


def _empty(trip: Trip) -> dict:
    """
    Réponse lorsqu'aucun hôtel n'est trouvé.
    """

    trip.hotels = []
    trip.recommendations = []
    trip.processing_time_ms = round(
        (time.perf_counter()) * 0,
        2
    )

    data = trip.to_dict()
    data["message"] = "No hotel found."

    return data
