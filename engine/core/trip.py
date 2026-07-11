from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import date, timedelta


@dataclass
class TripIntent:
    """Ce que l'utilisateur veut vraiment."""
    trip_type: str = "leisure"          # business, family, romantic, backpacker
    goal: str = ""                       # conference, vacances, mariage...
    must_have: list = field(default_factory=list)    # ["wifi", "metro"]
    nice_to_have: list = field(default_factory=list) # ["gym", "piscine"]
    avoid: list = field(default_factory=list)        # ["nightlife", "noisy"]


@dataclass
class TripContext:
    """Contexte géographique et temporel."""
    event: str = ""
    event_lat: Optional[float] = None
    event_lng: Optional[float] = None
    family: Optional[str] = None
    family_lat: Optional[float] = None
    family_lng: Optional[float] = None
    checkin: str = ""
    checkout: str = ""
    adults: int = 1
    children: list = field(default_factory=list)
    currency: str = "EUR"
    budget: float = 200.0
    language: str = "fr"


@dataclass
class Trip:
    """L'objet central qui traverse tous les engines."""
    traveler_id: Optional[str] = None
    intent: TripIntent = field(default_factory=TripIntent)
    context: TripContext = field(default_factory=TripContext)
    raw_query: str = ""
    
    # Remplis par les engines
    hotels: list = field(default_factory=list)
    scored_hotels: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    explanations: list = field(default_factory=list)
    suggested_activities: list = field(default_factory=list)
    weather: list = field(default_factory=list)
    
    # Metadata
    confidence: float = 0.0
    total_found: int = 0
    processing_time_ms: float = 0.0
    
    def nights(self) -> int:
        if self.context.checkin and self.context.checkout:
            ci = date.fromisoformat(self.context.checkin)
            co = date.fromisoformat(self.context.checkout)
            return max(1, (co - ci).days)
        return 1
    
    def summary(self) -> str:
        return f"{self.nights()}n · {self.context.adults}ad · {self.context.currency}{self.context.budget}"
    
    def to_dict(self) -> dict:
        return asdict(self)