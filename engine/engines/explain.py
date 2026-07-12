"""
Explain Engine — Pourquoi cet hôtel ?
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def explain_recommendations(hotels: list, trip) -> List[Dict[str, Any]]:
    """
    Génère des explications pour chaque recommandation
    
    Args:
        hotels: Liste des hôtels recommandés
        trip: Objet Trip avec le contexte
    
    Returns:
        Liste des explications
    """
    if not hotels:
        return []
    
    explanations = []
    
    for i, hotel in enumerate(hotels):
        reasons = []
        warnings = []
        
        # ✅ Récupération sécurisée des données
        distance = hotel.get("distance_event_minutes")
        price = hotel.get("price")
        rating = hotel.get("rating", 0)
        budget = trip.context.budget if hasattr(trip.context, 'budget') else None
        
        # ===== 1. Distance =====
        if distance is not None:
            if distance <= 10:
                reasons.append(f"À {distance} min du centre")
            elif distance <= 20:
                reasons.append(f"À {distance} min — quartier proche")
            else:
                warnings.append(f"À {distance} min — éloigné")
        else:
            warnings.append("Distance non disponible")
        
        # ===== 2. Prix =====
        if price is not None and budget is not None and budget > 0:
            if price <= budget:
                reasons.append(f"Dans votre budget ({price} {trip.context.currency if hasattr(trip.context, 'currency') else '€'})")
            elif price <= budget * 1.3:
                warnings.append(f"Un peu au-dessus ({price} {trip.context.currency if hasattr(trip.context, 'currency') else '€'})")
            else:
                warnings.append(f"Dépasse le budget ({price} {trip.context.currency if hasattr(trip.context, 'currency') else '€'})")
        elif price is not None:
            warnings.append(f"Prix: {price} €")
        else:
            warnings.append("Prix non disponible")
        
        # ===== 3. Note =====
        if rating >= 9.0:
            reasons.append(f"Note exceptionnelle ({rating}/10)")
        elif rating >= 8.0:
            reasons.append(f"Très bien noté ({rating}/10)")
        elif rating > 0:
            warnings.append(f"Note moyenne ({rating}/10)")
        
        # ===== 4. Préférences (RÉCUPÉRATION SÉCURISÉE) =====
        # ✅ Accès aux préférences via intent, pas context
        preferences = []
        if hasattr(trip.intent, 'must_have'):
            preferences = trip.intent.must_have or []
        elif hasattr(trip.intent, 'preferences'):
            preferences = trip.intent.preferences or []
        
        facilities = [f.lower() for f in hotel.get("hotelFacilities", [])]
        
        for pref in preferences:
            pref_lower = pref.lower()
            if any(pref_lower in f for f in facilities):
                reasons.append(f"{pref} disponible")
            else:
                warnings.append(f"Pas de {pref}")
        
        # ===== 5. Équipements supplémentaires =====
        luxury_items = ["spa", "sauna", "jacuzzi", "hammam"]
        if any(item in " ".join(facilities) for item in luxury_items):
            reasons.append("Équipements de luxe disponibles")
        
        # ===== 6. Score de confiance =====
        confidence = 100
        confidence -= len(warnings) * 8
        if price is None:
            confidence -= 20
        if distance is None:
            confidence -= 15
        if rating == 0:
            confidence -= 10
        confidence = max(0, min(100, confidence))
        
        # ===== 7. Résumé =====
        summary = hotel.get('name', 'Hôtel')
        if reasons:
            summary += " — " + " | ".join(reasons[:3])
        
        explanations.append({
            "hotel_name": hotel.get('name', 'Hôtel'),
            "rank": i + 1,
            "score": hotel.get('score', 0),
            "confidence": confidence,
            "reasons": reasons,
            "warnings": warnings,
            "summary": summary
        })
    
    return explanations


def explain_single_hotel(hotel: Dict[str, Any], trip) -> Dict[str, Any]:
    """
    Génère une explication pour un seul hôtel
    
    Args:
        hotel: Dictionnaire de l'hôtel
        trip: Objet Trip avec le contexte
    
    Returns:
        Dictionnaire d'explication
    """
    explanations = explain_recommendations([hotel], trip)
    return explanations[0] if explanations else {}
