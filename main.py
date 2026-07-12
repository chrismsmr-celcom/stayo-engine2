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
import httpx  # ✅ AJOUTÉ

# Import des engines
from engine.engines.recommend import recommend
from engine.database import save_trip, save_click, get_traveler_history

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="STAYO Intelligence Engine",
    version="2.0.0",
    description="Moteur de recommandation d'hôtels intelligent",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# MODÈLES PYDANTIC
# ============================================================

class SearchRequest(BaseModel):
    query: str = "test"
    traveler_id: Optional[str] = None
    trip_type: Optional[str] = None
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


# ============================================================
# ENDPOINTS
# ============================================================

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
    return {"status": "ok", "version": "2.0.0", "engine": "STAYO Core"}


@app.post("/recommend")
async def recommend_endpoint(request: SearchRequest):
    try:
        logger.info(f"New recommendation request : {request.query}")
        
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
        
        # ✅ Vérification des résultats
        if not result.get("recommendations"):
            return {
                "message": "Aucun hôtel trouvé pour cette recherche",
                "recommendations": [],
                "hotels": []
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
        return {"status": "ok", "message": "Clic enregistré"}
    except Exception as e:
        logger.error(f"Erreur enregistrement clic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/profile/{traveler_id}")
async def get_traveler_profile(traveler_id: str):
    try:
        history = get_traveler_history(traveler_id, limit=10)
        return {
            "traveler_id": traveler_id,
            "recent_trips": history
        }
    except Exception as e:
        logger.error(f"Erreur récupération profil: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    try:
        logger.info(f"Feedback reçu: {feedback.trip_id} - {feedback.rating}/5")
        return {"status": "ok", "message": "Feedback enregistré"}
    except Exception as e:
        logger.error(f"Erreur feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
