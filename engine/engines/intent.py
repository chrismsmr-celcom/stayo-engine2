"""
Intent Engine — Comprend ce que veut VRAIMENT l'utilisateur.
Remplace l'ancien ai.py
"""

import os, json, httpx
from datetime import date, timedelta
from engine.core.trip import Trip, TripIntent, TripContext

DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")


async def parse_intent(query: str) -> Trip:
    """Parse la requête et retourne un objet Trip complet."""
    trip = Trip(raw_query=query)
    
    if DEEPSEEK_KEY and "sk-votre" not in DEEPSEEK_KEY:
        try:
            result = await _deepseek_intent(query)
            if result:
                trip = _build_trip_from_intent(result, query)
                return trip
        except Exception as e:
            print(f"DeepSeek error: {e}")
    
    # Fallback
    return _basic_trip(query)


async def _deepseek_intent(query: str) -> dict:
    today = date.today().isoformat()
    system = f"""Tu es un moteur d'analyse de voyage. Retourne UNIQUEMENT ce JSON :
{{
  "intent": {{
    "trip_type": "business",
    "goal": "conference",
    "must_have": ["wifi", "metro"],
    "nice_to_have": ["gym"],
    "avoid": ["nightlife", "noisy"]
  }},
  "context": {{
    "event": "La Défense",
    "event_lat": 48.8923,
    "event_lng": 2.2392,
    "family": null,
    "family_lat": null,
    "family_lng": null,
    "checkin": "2026-07-15",
    "checkout": "2026-07-17",
    "adults": 1,
    "currency": "EUR",
    "budget": 150
  }},
  "suggested_activities": ["coworking", "restaurant affaires"]
}}
Aujourd'hui = {today}. Calcule les dates à partir d'aujourd'hui.
Détecte la devise (USD, EUR, GBP).
Détecte le nombre d'adultes et enfants.
Suggère des activités selon le type de voyage."""

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post("https://api.deepseek.com/chat/completions",
            json={"model": "deepseek-chat", "messages": [{"role": "system", "content": system}, {"role": "user", "content": query}], "temperature": 0.1, "max_tokens": 500},
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"}
        )
    if r.status_code != 200: return {}
    content = r.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"): content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    try: return json.loads(content)
    except: return {}


def _build_trip_from_intent(data: dict, query: str) -> Trip:
    intent_data = data.get("intent", {})
    context_data = data.get("context", {})
    
    trip = Trip(
        raw_query=query,
        intent=TripIntent(
            trip_type=intent_data.get("trip_type", "leisure"),
            goal=intent_data.get("goal", ""),
            must_have=intent_data.get("must_have", []),
            nice_to_have=intent_data.get("nice_to_have", []),
            avoid=intent_data.get("avoid", [])
        ),
        context=TripContext(
            event=context_data.get("event", "Paris"),
            event_lat=context_data.get("event_lat", 48.8566),
            event_lng=context_data.get("event_lng", 2.3522),
            family=context_data.get("family"),
            checkin=context_data.get("checkin", (date.today() + timedelta(days=7)).isoformat()),
            checkout=context_data.get("checkout", (date.today() + timedelta(days=9)).isoformat()),
            adults=context_data.get("adults", 1),
            currency=context_data.get("currency", "EUR"),
            budget=context_data.get("budget", 200)
        ),
        suggested_activities=data.get("suggested_activities", [])
    )
    return trip


def _basic_trip(query: str) -> Trip:
    today = date.today().isoformat()
    return Trip(
        raw_query=query,
        intent=TripIntent(),
        context=TripContext(
            event="Paris", event_lat=48.8566, event_lng=2.3522,
            checkin=(date.fromisoformat(today) + timedelta(days=7)).isoformat(),
            checkout=(date.fromisoformat(today) + timedelta(days=9)).isoformat()
        )
    )