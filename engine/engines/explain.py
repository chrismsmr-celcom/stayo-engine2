"""
Explain Engine — Pourquoi cet hôtel ?
"""

from engine.core.trip import Trip


def explain_recommendations(hotels: list, trip: Trip) -> list:
    explanations = []
    for i, hotel in enumerate(hotels):
        reasons, warnings = [], []
        dist = hotel.get("distance_event_minutes")
        price = hotel.get("price")
        rating = hotel.get("rating", 0)
        
        if dist is not None:
            if dist <= 10: reasons.append(f"A {dist} min de {trip.context.event}")
            elif dist <= 20: reasons.append(f"A {dist} min — quartier proche")
            else: warnings.append(f"A {dist} min — eloigne")
        
        if price is not None:
            if price <= trip.context.budget: reasons.append(f"Dans votre budget ({price}{trip.context.currency})")
            elif price <= trip.context.budget * 1.3: warnings.append(f"Un peu au-dessus ({price}{trip.context.currency})")
            else: warnings.append(f"Depasse le budget ({price}{trip.context.currency})")
        else:
            warnings.append("Prix non disponible")
        
        if rating >= 9: reasons.append(f"Note exceptionnelle ({rating}/10)")
        elif rating >= 8: reasons.append(f"Tres bien note ({rating}/10)")
        elif rating > 0: warnings.append(f"Note moyenne ({rating}/10)")
        
        facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
        for must in trip.intent.must_have:
            if any(must.lower() in f for f in facilities):
                reasons.append(f"{must.capitalize()} disponible")
            else:
                warnings.append(f"Pas de {must}")
        
        confidence = 100 - (len(warnings) * 8) - (20 if price is None else 0)
        confidence = max(0, min(100, confidence))
        
        explanations.append({
            "hotel_name": hotel.get("name"), "rank": i + 1,
            "score": hotel.get("score", 0), "confidence": confidence,
            "reasons": reasons, "warnings": warnings,
            "summary": f"{hotel.get('name')} — " + " | ".join(reasons[:3])
        })
    return explanations