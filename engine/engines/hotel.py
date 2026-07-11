"""
STAYO Hotel Engine V2

Responsabilité :
- Connexion LiteAPI
- Recherche hôtels
- Prix
- Normalisation
- Préparation IA
"""

import os
import asyncio
import httpx

from engine.engines.hotel_features import extract_features


LITEAPI_KEY = os.getenv("LITEAPI_KEY")

LITEAPI_BASE = "https://api.liteapi.travel/v3.0"



async def fetch_hotels(
    lat,
    lng,
    checkin,
    checkout,
    adults,
    currency,
    radius=5000,
    limit=200
):


    async with httpx.AsyncClient(
        timeout=30
    ) as client:


        hotels = await _search_hotels(
            client,
            lat,
            lng,
            radius,
            limit
        )


        if not hotels:

            return []



        prices = await _fetch_prices(
            client,
            hotels,
            checkin,
            checkout,
            adults,
            currency
        )



        normalized = []



        for hotel in hotels:


            if not hotel.get("latitude"):

                continue



            item = {

                "id": hotel.get("id"),

                "name":
                    hotel.get(
                        "name",
                        "Hotel"
                    ),


                "lat":
                    float(
                        hotel["latitude"]
                    ),


                "lng":
                    float(
                        hotel["longitude"]
                    ),


                "address":
                    hotel.get(
                        "address",
                        ""
                    ),


                "city":
                    hotel.get(
                        "city",
                        ""
                    ),


                "thumbnail":
                    hotel.get(
                        "thumbnail"
                    ),


                "rating":
                    float(
                        hotel.get(
                            "rating",
                            0
                        )
                    ),


                "reviewCount":
                    hotel.get(
                        "reviewCount",
                        0
                    ),


                "stars":
                    hotel.get(
                        "stars",
                        0
                    ),


                "price":
                    prices.get(
                        hotel["id"]
                    ),


                "currency":
                    currency,


                "hotelFacilities":
                    hotel.get(
                        "hotelFacilities",
                        []
                    )

            }


            item["features"] = extract_features(
                item
            )


            normalized.append(
                item
            )



        return normalized
        # --------------------------------------------------
# SEARCH HOTELS
# --------------------------------------------------


async def _search_hotels(
    client,
    lat,
    lng,
    radius,
    limit
):

    """
    Recherche les hôtels autour
    d'un point GPS.
    """

    try:

        response = await client.get(

            f"{LITEAPI_BASE}/data/hotels",

            params={

                "latitude": lat,

                "longitude": lng,

                "radius": min(
                    radius,
                    50000
                ),

                "limit": limit,

                "language": "fr"

            },

            headers={

                "X-API-Key":
                    LITEAPI_KEY

            }

        )


        if response.status_code != 200:

            print(
                "LiteAPI hotel search error:",
                response.status_code
            )

            return []



        return response.json().get(
            "data",
            []
        )



    except Exception as e:

        print(
            "Hotel search exception:",
            e
        )

        return []





# --------------------------------------------------
# FETCH PRICES
# --------------------------------------------------


async def _fetch_prices(
    client,
    hotels,
    checkin,
    checkout,
    adults,
    currency
):

    """
    Récupère les prix disponibles.
    """

    prices = {}



    ids = [

        h["id"]

        for h in hotels[:100]

        if h.get("id")

    ]



    if not ids:

        return prices



    try:

        response = await client.post(


            f"{LITEAPI_BASE}/hotels/rates",


            json={

                "hotelIds":
                    ids,


                "checkin":
                    checkin,


                "checkout":
                    checkout,


                "currency":
                    currency,


                "guestNationality":
                    "FR",


                "occupancies":[

                    {

                        "adults":
                            adults

                    }

                ],


                "maxRatesPerHotel":
                    1,


                "limit":
                    100,


                "timeout":
                    8

            },


            headers={

                "X-API-Key":
                    LITEAPI_KEY

            }


        )



        if response.status_code != 200:

            return prices




        for hotel in response.json().get(
            "data",
            []
        ):


            hotel_id = hotel.get(
                "hotelId"
            )


            amount = _extract_price(
                hotel
            )


            if amount:

                prices[hotel_id] = round(
                    float(amount)
                )



    except Exception as e:

        print(
            "Price error:",
            e
        )



    return prices





# --------------------------------------------------
# PRICE EXTRACTOR
# --------------------------------------------------


def _extract_price(
    hotel
):

    """
    Compatible avec plusieurs
    formats LiteAPI.
    """


    room = (

        hotel.get(
            "roomTypes",
            [{}]

        )[0]

    )


    price = (

        room.get(
            "offerRetailRate",
            {}
        )
        .get(
            "amount"
        )

    )


    if price:

        return price



    rates = room.get(
        "rates",
        []
    )


    if rates:


        return (

            rates[0]
            .get(
                "retailRate",
                {}
            )
            .get(
                "total",
                [{}]

            )[0]
            .get(
                "amount"
            )

        )



    return None
    """
STAYO Hotel Features Engine

Transforme les informations hôtel
en données intelligentes pour le scoring.

Objectif :
Comprendre le type d'expérience
que propose un hôtel.
"""


def extract_features(hotel: dict) -> dict:

    facilities = _normalize_text(
        hotel.get("hotelFacilities", [])
    )

    name = hotel.get(
        "name",
        ""
    ).lower()


    text = " ".join(
        facilities
    ) + " " + name



    return {

        "luxury_score":
            _luxury_score(text, hotel),


        "business_score":
            _business_score(text),


        "romantic_score":
            _romantic_score(text),


        "family_score":
            _family_score(text),


        "wellness_score":
            _wellness_score(text),


        "food_score":
            _food_score(text),


        "transport_score":
            _transport_score(text),


        "comfort_score":
            _comfort_score(text)

    }





# -----------------------------------------
# NORMALISATION
# -----------------------------------------


def _normalize_text(items):

    if not items:

        return []


    result = []


    for item in items:

        if isinstance(item, dict):

            value = (

                item.get("name")

                or

                item.get("title")

            )

            if value:

                result.append(
                    value.lower()
                )


        elif isinstance(item, str):

            result.append(
                item.lower()
            )


    return result





# -----------------------------------------
# LUXE
# -----------------------------------------


def _luxury_score(text, hotel):

    score = 40


    luxury_words = [

        "5 star",
        "five star",
        "luxury",
        "concierge",
        "butler",
        "executive",
        "suite",
        "premium",
        "vip"

    ]


    for word in luxury_words:

        if word in text:

            score += 10



    stars = hotel.get(
        "stars",
        0
    )


    if stars >= 5:

        score += 30

    elif stars >= 4:

        score += 15



    return min(
        score,
        100
    )





# -----------------------------------------
# BUSINESS
# -----------------------------------------


def _business_score(text):

    score = 30


    keywords = [

        "business center",
        "meeting",
        "conference",
        "coworking",
        "wifi",
        "internet",
        "workspace",
        "printer"

    ]


    for word in keywords:

        if word in text:

            score += 10



    return min(
        score,
        100
    )





# -----------------------------------------
# ROMANTIQUE
# -----------------------------------------


def _romantic_score(text):

    score = 30


    keywords = [

        "spa",
        "wellness",
        "massage",
        "view",
        "sea view",
        "restaurant",
        "bar",
        "pool",
        "suite"

    ]


    for word in keywords:

        if word in text:

            score += 10



    return min(
        score,
        100
    )





# -----------------------------------------
# FAMILLE
# -----------------------------------------


def _family_score(text):

    score = 30


    keywords = [

        "family",
        "kids",
        "children",
        "baby",
        "playground",
        "pool",
        "connecting rooms"

    ]


    for word in keywords:

        if word in text:

            score += 12



    return min(
        score,
        100
    )





# -----------------------------------------
# WELLNESS
# -----------------------------------------


def _wellness_score(text):

    score = 20


    keywords = [

        "spa",
        "sauna",
        "massage",
        "fitness",
        "gym",
        "wellness"

    ]


    for word in keywords:

        if word in text:

            score += 15



    return min(
        score,
        100
    )





# -----------------------------------------
# RESTAURATION
# -----------------------------------------


def _food_score(text):

    score = 30


    keywords = [

        "restaurant",
        "gastronomic",
        "chef",
        "bar",
        "breakfast",
        "buffet"

    ]


    for word in keywords:

        if word in text:

            score += 12



    return min(
        score,
        100
    )





# -----------------------------------------
# TRANSPORT
# -----------------------------------------


def _transport_score(text):

    score = 30


    keywords = [

        "airport shuttle",
        "metro",
        "subway",
        "parking",
        "transfer",
        "taxi"

    ]


    for word in keywords:

        if word in text:

            score += 12



    return min(
        score,
        100
    )





# -----------------------------------------
# CONFORT GENERAL
# -----------------------------------------


def _comfort_score(text):

    score = 40


    keywords = [

        "air conditioning",
        "climate",
        "room service",
        "24 hour",
        "reception",
        "quiet"

    ]


    for word in keywords:

        if word in text:

            score += 10



    return min(
        score,
        100
    )
