"""
STAYO Intent Engine
Analyse la requête utilisateur et construit un objet Trip.
"""

import os
import json
import re
import httpx

from datetime import date, timedelta

from engine.core.trip import Trip


DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")

DEEPSEEK_URL = (
    "https://api.deepseek.com/chat/completions"
)


# --------------------------------------------------
# PUBLIC
# --------------------------------------------------

async def parse_intent(
    query: str,
    traveler_id: str = None
) -> Trip:

    trip = Trip(
        raw_query=query,
        traveler_id=traveler_id
    )


    if DEEPSEEK_KEY:

        try:
            data = await _deepseek(query)

        except Exception as e:

            print(
                f"DeepSeek Error: {e}"
            )

            data = _fallback(query)

    else:

        data = _fallback(query)


    _fill_trip(
        trip,
        data
    )

    return trip



# --------------------------------------------------
# DEEPSEEK
# --------------------------------------------------

async def _deepseek(query: str):

    today = date.today().isoformat()


    prompt = f"""

Aujourd'hui : {today}

Tu es STAYO Intelligence Engine.

Analyse la demande voyageur.

Retourne uniquement ce JSON :

{{
"trip_type":"",
"goal":"",
"destination":"",
"destination_lat":0,
"destination_lng":0,
"budget":200,
"currency":"EUR",
"checkin":"",
"checkout":"",
"adults":1,
"preferences":[],
"confidence":95
}}

"""


    async with httpx.AsyncClient(
        timeout=30
    ) as client:


        response = await client.post(

            DEEPSEEK_URL,

            headers={
                "Authorization":
                f"Bearer {DEEPSEEK_KEY}",
                "Content-Type":
                "application/json"
            },


            json={

                "model":
                "deepseek-chat",

                "temperature":
                0.1,

                "messages":[

                    {
                        "role":"system",
                        "content":prompt
                    },

                    {
                        "role":"user",
                        "content":query
                    }

                ]

            }

        )


    response.raise_for_status()


    content = (
        response.json()
        ["choices"][0]
        ["message"]
        ["content"]
    )


    match = re.search(
        r"\{.*\}",
        content,
        re.S
    )


    if not match:

        raise Exception(
            "JSON introuvable"
        )


    return json.loads(
        match.group()
    )



# --------------------------------------------------
# FALLBACK
# --------------------------------------------------

def _fallback(query):

    q = query.lower()


    trip_type = "leisure"


    if (
        "business" in q
        or "conférence" in q
    ):
        trip_type = "business"


    elif "couple" in q:

        trip_type = "romantic"


    elif "famille" in q:

        trip_type = "family"



    budget = 250


    match = re.search(
        r"(\d+)\s*(€|eur|euros?)",
        q
    )


    if match:

        budget = int(
            match.group(1)
        )


    preferences = []


    keywords = [

        "wifi",
        "spa",
        "restaurant",
        "parking",
        "piscine",
        "balcon",
        "vue",
        "petit-déjeuner"

    ]


    for keyword in keywords:

        if keyword in q:

            preferences.append(
                keyword
            )


    return {

        "trip_type":
        trip_type,


        "goal":
        "",


        "destination":
        "Paris",


        "destination_lat":
        48.8566,


        "destination_lng":
        2.3522,


        "budget":
        budget,


        "currency":
        "EUR",


        "checkin":
        (
            date.today()
            +
            timedelta(days=7)
        ).isoformat(),


        "checkout":
        (
            date.today()
            +
            timedelta(days=9)
        ).isoformat(),


        "adults":
        2 if "couple" in q else 1,


        "preferences":
        preferences,


        "confidence":
        60

    }



# --------------------------------------------------
# BUILD TRIP
# --------------------------------------------------

def _fill_trip(
    trip: Trip,
    data: dict
):


    trip.intent.trip_type = (
        data.get(
            "trip_type",
            "leisure"
        )
    )


    trip.intent.goal = (
        data.get(
            "goal",
            ""
        )
    )


    prefs = (
        data.get(
            "preferences",
            []
        )
    )


    trip.intent.must_have = prefs



    trip.context.event = (
        data.get(
            "destination",
            ""
        )
    )


    trip.context.event_lat = (
        data.get(
            "destination_lat"
        )
    )


    trip.context.event_lng = (
        data.get(
            "destination_lng"
        )
    )


    trip.context.checkin = (
        data.get(
            "checkin"
        )
    )


    trip.context.checkout = (
        data.get(
            "checkout"
        )
    )


    trip.context.adults = (
        data.get(
            "adults",
            1
        )
    )


    trip.context.currency = (
        data.get(
            "currency",
            "EUR"
        )
    )


    trip.context.budget = (
        data.get(
            "budget",
            200
        )
    )


    trip.confidence = (
        data.get(
            "confidence",
            60
        )
    )
