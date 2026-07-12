"""
STAYO Intelligence Engine - Main API Entry Point
Version: 2.0.0
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
import uvicorn
import os
import httpx

from engine.engines.recommend import recommend
from engine.engines.traveller import get_profile
from engine.database import save_trip, save_click, get_traveler_history
from engine.core.config import ACTIVITIES


# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# =====================================================
# APP
# =====================================================

app = FastAPI(
    title="STAYO Intelligence Engine",
    version="2.0.0",
    description="AI Travel Recommendation Engine",
    docs_url="/docs",
    redoc_url="/redoc"
)


# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# MODELS
# =====================================================

class SearchRequest(BaseModel):
    """Requête de recherche de recommandations"""
    query: str = "test"
    traveler_id: Optional[str] = None
    
    # ✅ AJOUTER trip_type
    trip_type: Optional[str] = None  # business, romantic, family, backpacker, leisure
    
    budget: Optional[float] = None
    currency: Optional[str] = "EUR"
    checkin: Optional[str] = None
    checkout: Optional[str] = None
    adults: Optional[int] = 2
    lat: Optional[float] = None
    lng: Optional[float] = None



class ClickRequest(BaseModel):

    traveler_id: str

    hotel_id: str

    hotel_name: str

    price: float

    score: float

    position: int



class FeedbackRequest(BaseModel):

    traveler_id: str

    trip_id: int

    rating: int

    comment: Optional[str] = None



# =====================================================
# ROOT
# =====================================================

@app.get("/")
async def root():

    return {

        "message": "STAYO Intelligence Engine",

        "version": "2.0.0",

        "status": "operational",

        "docs": "/docs"

    }



@app.get("/health")
async def health():

    return {

        "status": "ok",

        "engine": "STAYO Core",

        "version": "2.0.0"

    }



# =====================================================
# RECOMMENDATION
# =====================================================

@app.post("/recommend")
async def recommend_endpoint(request: SearchRequest):
    try:
        logger.info(f"New recommendation request : {request.query}")
        
        # Appel du moteur de recommandation
        result = await recommend(
            query=request.query,
            traveler_id=request.traveler_id,
            overrides={
                "trip_type": request.trip_type,
                "budget": request.budget,
                "currency": request.currency,
                "checkin": request.checkin,
                "checkout": request.checkout,
                "adults": request.adults,
                "lat": request.lat,
                "lng": request.lng
            }
        )
        
        # ✅ Récupérer les détails complets des hôtels recommandés
        if result.get("recommendations"):
            enriched_hotels = []
            for hotel in result["recommendations"]:
                # Récupérer les détails depuis LiteAPI
                details = await fetch_hotel_details(hotel.get("id"))
                if details:
                    # Fusionner les données
                    hotel["details"] = details
                    hotel["full_description"] = details.get("hotelDescription", "")
                    hotel["images"] = details.get("hotelImages", [])
                    hotel["checkin_time"] = details.get("checkinCheckoutTimes", {}).get("checkin", "Non specifie")
                    hotel["checkout_time"] = details.get("checkinCheckoutTimes", {}).get("checkout", "Non specifie")
                    hotel["cancellation_policies"] = details.get("cancellationPolicies", {})
                    hotel["important_info"] = details.get("hotelImportantInformation", "")
                    hotel["facilities_list"] = details.get("hotelFacilities", [])
                enriched_hotels.append(hotel)
            
            result["recommendations"] = enriched_hotels
        
        # ✅ Ajouter les paramètres utilisateur pour l'affichage
        result["user_params"] = {
            "checkin": request.checkin,
            "checkout": request.checkout,
            "adults": request.adults,
            "currency": request.currency,
            "nights": _calculate_nights(request.checkin, request.checkout)
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def fetch_hotel_details(hotel_id: str):
    """Récupère les détails d'un hôtel depuis LiteAPI"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:  # ← httpx maintenant défini
            response = await client.get(
                f"https://api.liteapi.travel/v3.0/data/hotel",
                params={"hotelId": hotel_id, "language": "fr"},
                headers={"X-API-Key": LITEAPI_KEY}
            )
            if response.status_code == 200:
                return response.json().get("data", {})
    except Exception as e:
        logger.error(f"Error fetching hotel details: {e}")
    return None


def _calculate_nights(checkin: str, checkout: str) -> int:
    """Calcule le nombre de nuits entre deux dates"""
    if not checkin or not checkout:
        return 1
    try:
        from datetime import datetime
        c_in = datetime.strptime(checkin, "%Y-%m-%d")
        c_out = datetime.strptime(checkout, "%Y-%m-%d")
        return max(1, (c_out - c_in).days)
    except:
        return 1



# =====================================================
# CLICK TRACKING
# =====================================================

@app.post("/click")
async def record_click(click: ClickRequest):

    try:

        save_click(

            traveler_id=click.traveler_id,

            hotel_id=click.hotel_id,

            hotel_name=click.hotel_name,

            price=click.price,

            score=click.score,

            position=click.position

        )


        return {

            "status": "ok",

            "message": "Click saved"

        }


    except Exception as e:

        logger.exception(
            "Click error"
        )

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )



# =====================================================
# PROFILE
# =====================================================

@app.get("/profile/{traveler_id}")
async def traveler_profile(traveler_id: str):

    try:

        profile = get_profile(traveler_id)


        history = get_traveler_history(

            traveler_id,

            limit=10

        )


        return {

            "traveler_id": traveler_id,

            "preferences": profile.preferences,

            "favorite_amenities": profile.favorite_amenities,

            "avg_budget": profile.avg_budget,

            "preferred_trip_type": profile.preferred_trip_type,

            "recent_trips": history

        }


    except Exception as e:

        logger.exception(
            "Profile error"
        )

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )



# =====================================================
# ACTIVITIES
# =====================================================

@app.get("/activities/{trip_type}")
async def activities(trip_type: str):

    try:

        return {

            "trip_type": trip_type,

            "activities": ACTIVITIES.get(

                trip_type,

                ACTIVITIES.get(
                    "leisure",
                    []
                )

            )

        }


    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )

# ============ MÉMOIRE UTILISATEUR ============

# Stockage simple en mémoire (à remplacer par Redis/DB en prod)
user_memory = {}

@app.post("/remember")
async def remember_click(click: ClickRequest):
    """Enregistre les préférences de l'utilisateur"""
    if click.traveler_id not in user_memory:
        user_memory[click.traveler_id] = {
            "clicks": [],
            "preferences": {},
            "trip_history": []
        }
    
    user_memory[click.traveler_id]["clicks"].append({
        "hotel_id": click.hotel_id,
        "hotel_name": click.hotel_name,
        "price": click.price,
        "score": click.score,
        "timestamp": datetime.now().isoformat()
    })
    
    # Enregistrer les clics
    save_click(click.traveler_id, click.hotel_id, click.hotel_name, click.price, click.score, click.position)
    
    return {"status": "ok", "message": "Préférence enregistrée"}

@app.get("/profile/{traveler_id}")
async def get_traveler_profile(traveler_id: str):
    """Récupère le profil utilisateur avec historique"""
    try:
        profile = get_profile(traveler_id)
        history = get_traveler_history(traveler_id, limit=10)
        
        # Ajouter les préférences apprises
        preferences = {}
        if traveler_id in user_memory:
            clicks = user_memory[traveler_id]["clicks"]
            if clicks:
                # Analyser les clics pour en déduire les préférences
                hotel_ids = [c["hotel_id"] for c in clicks]
                avg_price = sum(c["price"] for c in clicks) / len(clicks)
                
                preferences = {
                    "avg_price": round(avg_price, 2),
                    "total_clicks": len(clicks),
                    "favorite_hotels": list(set([c["hotel_name"] for c in clicks]))[:5]
                }
        
        return {
            "traveler_id": traveler_id,
            "preferences": {**profile.preferences, **preferences},
            "favorite_amenities": profile.favorite_amenities,
            "avg_budget": profile.avg_budget,
            "preferred_trip_type": profile.preferred_trip_type,
            "recent_trips": history
        }
    except Exception as e:
        logger.error(f"Erreur récupération profil: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# FEEDBACK
# =====================================================

@app.post("/feedback")
async def feedback(request: FeedbackRequest):

    logger.info(

        f"Feedback {request.rating}/5 "
        f"from {request.traveler_id}"

    )


    return {

        "status": "ok",

        "message": "Feedback received"

    }



# =====================================================
# LOCAL START
# =====================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            8000
        )
    )


    uvicorn.run(

        "main:app",

        host="0.0.0.0",

        port=port,

        reload=True

    )
