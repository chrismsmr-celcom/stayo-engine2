"""
Hotel Engine — Connexion LiteAPI.
"""

import os, asyncio, httpx

LITEAPI_KEY = os.getenv("LITEAPI_KEY", "prod_3a27a498-2b18-43a8-a91e-f3f241c889a7")
LITEAPI_BASE = "https://api.liteapi.travel/v3.0"


async def fetch_hotels(lat, lng, checkin, checkout, adults, currency, radius=5000, limit=200):
    async with httpx.AsyncClient(timeout=30) as client:
        # Étape 1 : Hôtels
        res = await client.get(f"{LITEAPI_BASE}/data/hotels", params={
            "latitude": lat, "longitude": lng, "radius": min(radius, 50000),
            "limit": limit, "language": "fr"
        }, headers={"X-API-Key": LITEAPI_KEY})
        if res.status_code != 200: return []
        hotels = res.json().get("data", [])
        if not hotels: return []

        # Étape 2 : Prix
        ids = [h["id"] for h in hotels[:100]]
        res2 = await client.post(f"{LITEAPI_BASE}/hotels/rates", json={
            "hotelIds": ids, "checkin": checkin, "checkout": checkout,
            "currency": currency, "guestNationality": "FR",
            "occupancies": [{"adults": adults}], "maxRatesPerHotel": 1, "limit": 100, "timeout": 8
        }, headers={"X-API-Key": LITEAPI_KEY})
        prices = {}
        if res2.status_code == 200:
            for h in res2.json().get("data", []):
                rt = (h.get("roomTypes") or [{}])[0]
                amt = rt.get("offerRetailRate", {}).get("amount")
                if not amt and rt.get("rates"):
                    r = rt["rates"][0]
                    amt = (r.get("retailRate", {}) or {}).get("total", [{}])[0].get("amount")
                if amt: prices[h["hotelId"]] = round(float(amt))

        # Étape 3 : Fusion + enrichissement top 10
        result = []
        for h in hotels:
            if not (h.get("latitude") and h.get("longitude")): continue
            result.append({
                "id": h["id"], "name": h.get("name", "Hotel"),
                "lat": float(h["latitude"]), "lng": float(h["longitude"]),
                "address": h.get("address", ""), "city": h.get("city", ""),
                "country": h.get("country", ""),
                "thumbnail": h.get("thumbnail") or h.get("main_photo"),
                "rating": float(h.get("rating", 0)), "reviewCount": h.get("reviewCount", 0),
                "stars": h.get("stars", 0), "price": prices.get(h["id"]),
                "hotelFacilities": h.get("hotelFacilities", []),
                "currency": currency
            })

        # Étape 4 : Enrichir top 10 avec détails
        top10 = [h for h in result[:10] if not h["hotelFacilities"]]
        if top10:
            enriched = await asyncio.gather(*[_enrich(client, h["id"]) for h in top10], return_exceptions=True)
            for i, e in enumerate(enriched):
                if isinstance(e, dict):
                    top10[i]["hotelFacilities"] = e.get("facilities", [])
                    top10[i]["description"] = e.get("description", "")
                    top10[i]["importantInfo"] = e.get("importantInfo", "")
                    top10[i]["checkinTime"] = e.get("checkinTime", "")
                    top10[i]["checkoutTime"] = e.get("checkoutTime", "")
                    top10[i]["hotelImages"] = e.get("images", [])

        return result


async def _enrich(client, hotel_id):
    try:
        r = await client.get(f"{LITEAPI_BASE}/data/hotel", params={"hotelId": hotel_id, "language": "fr"}, headers={"X-API-Key": LITEAPI_KEY})
        if r.status_code != 200: return {}
        d = r.json().get("data", {})
        return {
            "facilities": d.get("hotelFacilities", []),
            "description": d.get("hotelDescription", ""),
            "importantInfo": d.get("hotelImportantInformation", ""),
            "checkinTime": (d.get("checkinCheckoutTimes") or {}).get("checkin", ""),
            "checkoutTime": (d.get("checkinCheckoutTimes") or {}).get("checkout", ""),
            "images": d.get("hotelImages", []),
            "cancellation": d.get("cancellationPolicies")
        }
    except: return {}