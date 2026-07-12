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

    query: str

    traveler_id: Optional[str] = None



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

        logger.info(
            f"New recommendation request : {request.query}"
        )


        result = await recommend(

            query=request.query,

            traveler_id=request.traveler_id

        )


        if not result.get("recommendations"):

            raise HTTPException(

                status_code=404,

                detail=result.get(
                    "message",
                    "No recommendation found"
                )

            )


        # Sauvegarde historique voyageur

        if request.traveler_id:

            try:

                save_trip(

                    traveler_id=request.traveler_id,

                    trip_dict={

                        "raw_query": request.query,

                        "intent": result.get(
                            "intent",
                            {}
                        ),

                        "context": result.get(
                            "context",
                            {}
                        ),

                        "recommendations": result.get(
                            "recommendations",
                            []
                        )

                    }

                )


            except Exception as e:

                logger.warning(
                    f"Trip save error : {e}"
                )


        return result


    except HTTPException:

        raise


    except Exception as e:

        logger.exception(
            "Recommendation error"
        )

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )



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
