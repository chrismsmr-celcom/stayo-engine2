"""
Traveller Engine — Profil voyageur et mémoire.
"""

from engine.core.trip import Trip


class TravellerProfile:
    def __init__(self, traveler_id: str = None):
        self.id = traveler_id
        self.preferences = {}
        self.history = []
        self.favorite_amenities = []
        self.avg_budget = 0
        self.preferred_trip_type = None

    def update_from_trip(self, trip: Trip):
        """Apprend des choix de l'utilisateur."""
        if trip.intent.trip_type:
            self.preferred_trip_type = trip.intent.trip_type
        if trip.context.budget:
            self.avg_budget = (self.avg_budget + trip.context.budget) / 2 if self.avg_budget else trip.context.budget
        for amenity in trip.intent.must_have:
            if amenity not in self.favorite_amenities:
                self.favorite_amenities.append(amenity)

    def apply_to_weights(self, weights: dict) -> dict:
        """Ajuste les poids selon les préférences apprises."""
        if not self.preferred_trip_type:
            return weights
        # Renforcer les poids du type préféré
        if self.preferred_trip_type == "business":
            weights["transport"] = weights.get("transport", 1) * 1.2
            weights["amenities"] = weights.get("amenities", 1) * 1.1
        elif self.preferred_trip_type == "backpacker":
            weights["price"] = weights.get("price", 1) * 1.3
        return weights


# Base de profils en mémoire (à remplacer par DB)
_profiles = {}


def get_profile(traveler_id: str) -> TravellerProfile:
    if traveler_id not in _profiles:
        _profiles[traveler_id] = TravellerProfile(traveler_id)
    return _profiles[traveler_id]


def save_profile(profile: TravellerProfile):
    _profiles[profile.id] = profile