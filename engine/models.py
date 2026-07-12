"""
models.py - Schémas Pydantic pour l'Intent Engine
Validation stricte des données
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date


class IntentSchema(BaseModel):
    """Schéma d'intention de voyage validé"""
    
    trip_type: str = Field(default="leisure", description="Type de voyage")
    destination: str = Field(default="Paris", description="Ville principale")
    area: Optional[str] = Field(default=None, description="Quartier ou sous-lieu")
    lat: float = Field(default=48.8566, description="Latitude", ge=-90, le=90)
    lng: float = Field(default=2.3522, description="Longitude", ge=-180, le=180)
    budget: int = Field(default=250, description="Budget estimé", ge=1)
    currency: str = Field(default="EUR", description="Devise")
    must_have: List[str] = Field(default_factory=list, description="Équipements essentiels")
    nice_to_have: List[str] = Field(default_factory=list, description="Équipements souhaitables")
    adults: int = Field(default=2, ge=1, description="Nombre d'adultes")
    children: int = Field(default=0, ge=0, description="Nombre d'enfants")
    rooms: int = Field(default=1, ge=1, description="Nombre de chambres")
    vibe: str = Field(default="confort", description="Ambiance recherchée")
    checkin: Optional[str] = Field(default="", description="Date d'arrivée YYYY-MM-DD")
    checkout: Optional[str] = Field(default="", description="Date de départ YYYY-MM-DD")
    place_description: Optional[str] = Field(default="", description="Description du lieu")
    raw_query: Optional[str] = Field(default="", description="Requête brute")
    
    @field_validator('checkout')
    @classmethod
    def check_date_sequence(cls, v, info):
        """Vérifie que la date de départ est après la date d'arrivée"""
        checkin_val = info.data.get('checkin')
        if v and checkin_val:
            try:
                if date.fromisoformat(v) < date.fromisoformat(checkin_val):
                    raise ValueError("La date de départ doit être après la date d'arrivée.")
            except (ValueError, TypeError):
                pass  # Ignorer si le format n'est pas ISO
        return v
    
    @field_validator('trip_type')
    @classmethod
    def validate_trip_type(cls, v):
        """Valide le type de voyage"""
        valid_types = ["business", "romantic", "family", "backpacker", "luxury", "leisure"]
        if v not in valid_types:
            return "leisure"
        return v
    
    @field_validator('vibe')
    @classmethod
    def validate_vibe(cls, v):
        """Valide le vibe"""
        valid_vibes = ["luxe", "confort", "budget", "design", "familial", "romantique", "professionnel", "décontracté"]
        if v not in valid_vibes:
            return "confort"
        return v
    
    class Config:
        """Configuration Pydantic"""
        json_schema_extra = {
            "example": {
                "trip_type": "family",
                "destination": "Paris",
                "area": "Bercy",
                "lat": 48.8385,
                "lng": 2.3822,
                "budget": 350,
                "currency": "EUR",
                "must_have": ["piscine", "chambre familiale"],
                "nice_to_have": ["restaurant", "parking"],
                "adults": 2,
                "children": 3,
                "rooms": 2,
                "vibe": "familial",
                "checkin": "2026-07-25",
                "checkout": "2026-07-30"
            }
        }