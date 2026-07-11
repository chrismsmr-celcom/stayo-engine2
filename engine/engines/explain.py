"""
STAYO Explain Engine
Explique pourquoi chaque hôtel est recommandé.
"""

from engine.core.trip import Trip


def explain_recommendations(hotels: list, trip: Trip) -> list:

    explanations = []

    for rank, hotel in enumerate(hotels, start=1):

        reasons = []

        warnings = []

        # --------------------------
        # Distance
        # --------------------------

        distance = hotel.get("distance_event_minutes")

        if distance is not None:

            if distance <= 5:

                reasons.append(
                    f"À seulement {distance} min de {trip.context.event}"
                )

            elif distance <= 10:

                reasons.append(
                    f"Très proche de {trip.context.event}"
                )

            elif distance <= 20:

                reasons.append(
                    f"Quartier proche ({distance} min)"
                )

            else:

                warnings.append(
                    f"Situé à {distance} min de votre destination"
                )

        # --------------------------
        # Prix
        # --------------------------

        budget = trip.context.budget

        price = hotel.get("price")

        currency = trip.context.currency

        if price is None:

            warnings.append("Prix indisponible")

        elif budget:

            if price <= budget:

                reasons.append(
                    f"Respecte votre budget ({price} {currency})"
                )

            elif price <= budget * 1.20:

                reasons.append(
                    "Légèrement au-dessus du budget"
                )

            else:

                warnings.append(
                    "Prix supérieur au budget prévu"
                )

        # --------------------------
        # Note
        # --------------------------

        rating = hotel.get("rating", 0)

        reviews = hotel.get("reviewCount", 0)

        if rating >= 9:

            reasons.append(
                f"Excellente note ({rating}/10)"
            )

        elif rating >= 8:

            reasons.append(
                f"Très bien noté ({rating}/10)"
            )

        elif rating > 0:

            warnings.append(
                f"Note moyenne ({rating}/10)"
            )

        if reviews > 1000:

            reasons.append(
                f"{reviews} avis voyageurs"
            )

        # --------------------------
        # Préférences
        # --------------------------

        facilities = [

            f.lower()

            for f in hotel.get("hotelFacilities", [])

        ]

        for pref in trip.context.preferences:

            if any(pref.lower() in f for f in facilities):

                reasons.append(
                    f"{pref.capitalize()} disponible"
                )

            else:

                warnings.append(
                    f"{pref.capitalize()} indisponible"
                )

        # --------------------------
        # Type de voyage
        # --------------------------

        trip_type = trip.context.trip_type

        if trip_type == "business":

            reasons.append(
                "Adapté aux déplacements professionnels"
            )

        elif trip_type == "romantic":

            reasons.append(
                "Convient à un séjour en couple"
            )

        elif trip_type == "family":

            reasons.append(
                "Adapté aux familles"
            )

        elif trip_type == "backpacker":

            reasons.append(
                "Bon choix pour un voyage économique"
            )

        # --------------------------
        # Confidence
        # --------------------------

        confidence = hotel.get("confidence", 90)

        # --------------------------
        # Résumé
        # --------------------------

        summary = " • ".join(reasons[:4])

        explanations.append({

            "rank": rank,

            "hotel_name": hotel.get("name"),

            "score": hotel.get("score", 0),

            "confidence": confidence,

            "reasons": reasons,

            "warnings": warnings,

            "summary": summary

        })

    return explanations
