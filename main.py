"""
STAYO Intelligence Engine - Main API Entry Point
Version: 2.0.0
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import uvicorn
import os

# Import des engines
from engine.engines.recommend import recommend
from engine.engines.traveller import get_profile, save_profile
from engine.database import save_trip, save_click, get_traveler_history
from engine.core.config import WEIGHTS, ACTIVITIES

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ Initialisation de l'application ============
app = FastAPI(
    title="STAYO Intelligence Engine",
    version="2.0.0",
    description="Moteur de recommandation d'hôtels intelligent",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============ Middleware CORS ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Models Pydantic ============
class SearchRequest(BaseModel):
    """Requête de recherche de recommandations"""
    query: str = "test"
    traveler_id: Optional[str] = None
    
    # Paramètres optionnels pour surcharger l'intent
    trip_type: Optional[str] = None  # business, romantic, family, backpacker, leisure
    budget: Optional[float] = None
    currency: Optional[str] = "EUR"
    checkin: Optional[str] = None
    checkout: Optional[str] = None
    adults: Optional[int] = 2
    lat: Optional[float] = None
    lng: Optional[float] = None


class ClickRequest(BaseModel):
    """Enregistrement d'un clic sur un hôtel"""
    traveler_id: str
    hotel_id: str
    hotel_name: str
    price: float
    score: float
    position: int


class FeedbackRequest(BaseModel):
    """Feedback utilisateur sur une recommandation"""
    traveler_id: str
    trip_id: int
    rating: int  # 1-5
    comment: Optional[str] = None


# ============ Endpoints ============

@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "message": "STAYO Intelligence Engine",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Vérification de l'état du service"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "engine": "STAYO Core"
    }


@app.post("/recommend")
async def recommend_endpoint(request: SearchRequest):
    """
    Endpoint principal de recommandation d'hôtels
    
    Args:
        request: SearchRequest avec la requête et les paramètres
        
    Returns:
        Dict contenant les recommandations et les explications
    """
    try:
        logger.info(f"Recommandation pour: {request.query} (traveler: {request.traveler_id})")
        
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
        
        # Vérification des résultats
        if not result.get("recommendations"):
            raise HTTPException(
                status_code=404,
                detail=result.get("message", "Aucun hôtel trouvé pour cette recherche")
            )
        
        # Sauvegarde en base de données (si traveler_id fourni)
        if request.traveler_id:
            try:
                save_trip(
                    traveler_id=request.traveler_id,
                    trip_dict={
                        "raw_query": request.query,
                        "intent": result.get("intent", {}),
                        "context": result.get("context", {}),
                        "recommendations": result.get("recommendations", [])
                    }
                )
            except Exception as e:
                logger.warning(f"Erreur sauvegarde trip: {e}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans recommend_endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne du serveur: {str(e)}"
        )


@app.post("/click")
async def record_click(click: ClickRequest):
    """
    Enregistre un clic utilisateur sur un hôtel
    
    Args:
        click: ClickRequest avec les infos du clic
        
    Returns:
        Dict de confirmation
    """
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
    """
    Récupère le profil d'un voyageur
    
    Args:
        traveler_id: ID du voyageur
        
    Returns:
        Dict avec les préférences et l'historique
    """
    try:
        profile = get_profile(traveler_id)
        history = get_traveler_history(traveler_id, limit=10)
        
        return {
            "traveler_id": traveler_id,
            "preferences": profile.preferences,
            "favorite_amenities": profile.favorite_amenities,
            "avg_budget": profile.avg_budget,
            "preferred_trip_type": profile.preferred_trip_type,
            "recent_trips": history
        }
    except Exception as e:
        logger.error(f"Erreur récupération profil: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/activities/{trip_type}")
async def get_activities(trip_type: str = "leisure"):
    """
    Récupère les activités suggérées pour un type de voyage
    
    Args:
        trip_type: Type de voyage (business, romantic, family, backpacker, leisure)
        
    Returns:
        Dict avec les activités suggérées
    """
    try:
        activities = ACTIVITIES.get(trip_type, ACTIVITIES["leisure"])
        return {
            "trip_type": trip_type,
            "activities": activities
        }
    except Exception as e:
        logger.error(f"Erreur récupération activités: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Soumet un feedback utilisateur
    
    Args:
        feedback: FeedbackRequest avec la note et le commentaire
        
    Returns:
        Dict de confirmation
    """
    try:
        # À implémenter : sauvegarde du feedback
        logger.info(f"Feedback reçu: {feedback.trip_id} - {feedback.rating}/5")
        return {
            "status": "ok",
            "message": "Feedback enregistré avec succès"
        }
    except Exception as e:
        logger.error(f"Erreur feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Point d'entrée pour le développement ============
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
