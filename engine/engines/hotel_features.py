"""
STAYO Scoring Engine
Version 2.0
"""

from engine.core.trip import Trip


class ScoredHotel:

    def __init__(self, hotel):

        self.hotel = hotel

        self.scores = {}

        self.total = 0

        self.confidence = 100

        self.reasons = []

        self.warnings = []


# ----------------------------------------------------
# PUBLIC
# ----------------------------------------------------

def score_hotels(trip: Trip, hotels: list):

    results = []

    trip_type = trip.context.trip_type or "leisure"

    weights = _weights(trip_type)

    for hotel in hotels:

        sh = ScoredHotel(hotel)

        sh.scores["location"] = _location_score(hotel, trip, sh)

        sh.scores["price"] = _price_score(hotel, trip, sh)

        sh.scores["quality"] = _quality_score(hotel, sh)

        sh.scores["preferences"] = _preferences_score(hotel, trip, sh)

        sh.scores["transport"] = _transport_score(hotel, sh)

        sh.scores["trip"] = _trip_score(hotel, trip, sh)

        weighted = 0

        total_weight = 0

        for key, value in sh.scores.items():

            w = weights.get(key, 1)

            weighted += value * w

            total_weight += w

        sh.total = round(weighted / total_weight, 1)

        sh.confidence = _confidence(trip, hotel)

        hotel["score"] = sh.total

        hotel["confidence"] = sh.confidence

        hotel["score_details"] = sh.scores

        hotel["reasons"] = sh.reasons

        hotel["warnings"] = sh.warnings

        results.append(hotel)

    results.sort(

        key=lambda x: (

            x["score"],

            x["confidence"],

            x.get("rating", 0)

        ),

        reverse=True

    )

    return results


# ----------------------------------------------------
# SCORES
# ----------------------------------------------------

def _location_score(hotel, trip, sh):

    minutes = hotel.get("distance_event_minutes", 999)

    if minutes <= 5:

        sh.reasons.append("À moins de 5 min du lieu principal")

        return 100

    if minutes <= 10:

        sh.reasons.append("Très proche de votre destination")

        return 90

    if minutes <= 20:

        return 75

    if minutes <= 30:

        sh.warnings.append("Temps de trajet moyen")

        return 55

    sh.warnings.append("Éloigné de votre destination")

    return 25


def _price_score(hotel, trip, sh):

    price = hotel.get("price")

    budget = trip.context.budget

    if price is None:

        sh.warnings.append("Prix indisponible")

        return 50

    if budget is None:

        return 70

    ratio = price / budget

    if ratio <= 0.6:

        sh.reasons.append("Excellent rapport qualité/prix")

        return 100

    if ratio <= 0.8:

        return 90

    if ratio <= 1:

        return 80

    if ratio <= 1.2:

        return 65

    sh.warnings.append("Au-dessus du budget")

    return 30


def _quality_score(hotel, sh):

    rating = hotel.get("rating", 0)

    reviews = hotel.get("reviewCount", 0)

    score = rating * 18

    if reviews > 1000:

        score += 10

    elif reviews > 300:

        score += 5

    if rating >= 4.5:

        sh.reasons.append("Très bien noté par les voyageurs")

    return min(score, 100)


def _preferences_score(hotel, trip, sh):

    prefs = [p.lower() for p in trip.context.preferences]

    facilities = [

        f.lower()

        for f in hotel.get("hotelFacilities", [])

    ]

    if not prefs:

        return 70

    score = 60

    for pref in prefs:

        if any(pref in f for f in facilities):

            score += 10

            sh.reasons.append(f"{pref} disponible")

        else:

            score -= 5

    return max(0, min(score, 100))


def _transport_score(hotel, sh):

    score = 50

    facilities = [

        f.lower()

        for f in hotel.get("hotelFacilities", [])

    ]

    keywords = {

        "metro":15,

        "subway":15,

        "bus":10,

        "parking":10,

        "airport":10,

        "shuttle":10

    }

    for k, pts in keywords.items():

        if any(k in f for f in facilities):

            score += pts

    return min(score,100)


def _trip_score(hotel, trip, sh):

    facilities = [

        f.lower()

        for f in hotel.get("hotelFacilities", [])

    ]

    score = 50

    trip_type = trip.context.trip_type

    if trip_type == "business":

        if any("wifi" in f for f in facilities):

            score += 20

        if any("business" in f for f in facilities):

            score += 15

        if any("meeting" in f for f in facilities):

            score += 15

    elif trip_type == "romantic":

        if any("spa" in f for f in facilities):

            score += 20

        if any("restaurant" in f for f in facilities):

            score += 15

        if any("bar" in f for f in facilities):

            score += 10

    elif trip_type == "family":

        if any("pool" in f for f in facilities):

            score += 20

        if any("family" in f for f in facilities):

            score += 20

        if any("kids" in f for f in facilities):

            score += 10

    return min(score,100)


# ----------------------------------------------------
# WEIGHTS
# ----------------------------------------------------

def _weights(trip_type):

    return {

        "business":{

            "location":3,

            "price":1.5,

            "quality":1.5,

            "preferences":2.5,

            "transport":2.5,

            "trip":3

        },

        "romantic":{

            "location":1.5,

            "price":1,

            "quality":2,

            "preferences":2,

            "transport":1,

            "trip":3

        },

        "family":{

            "location":2,

            "price":2,

            "quality":1.5,

            "preferences":2,

            "transport":1.5,

            "trip":3

        },

        "backpacker":{

            "location":2,

            "price":4,

            "quality":1,

            "preferences":1,

            "transport":2,

            "trip":1

        }

    }.get(

        trip_type,

        {

            "location":2,

            "price":2,

            "quality":2,

            "preferences":2,

            "transport":2,

            "trip":2

        }

    )


# ----------------------------------------------------
# CONFIDENCE
# ----------------------------------------------------

def _confidence(trip, hotel):

    score = 100

    if trip.context.budget is None:

        score -= 10

    if trip.context.event_lat is None:

        score -= 20

    if hotel.get("price") is None:

        score -= 20

    if hotel.get("rating") is None:

        score -= 10

    if hotel.get("distance_event_minutes") is None:

        score -= 20

    return max(0, score)
