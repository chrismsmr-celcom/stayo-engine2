"""
STAYO Engine - Package principal
Version 2.0
"""

from engine.core.trip import Trip
from engine.core.config import *
from engine.engine import parse_intent  # ✅ Nouvel import

__version__ = "2.0.0"
__all__ = ["Trip", "parse_intent"]  # ✅ Ajout de parse_intent
