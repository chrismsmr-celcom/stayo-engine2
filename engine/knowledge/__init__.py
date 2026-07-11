"""
STAYO Knowledge - Base de connaissances
"""

import json
import os
from typing import Dict, Any

KNOWLEDGE_DIR = os.path.dirname(__file__)


def load_knowledge(file_name: str) -> Dict[str, Any]:
    """
    Charge un fichier de connaissance JSON
    
    Args:
        file_name: Nom du fichier (ex: "business.json")
    
    Returns:
        Dict contenant les connaissances
    """
    file_path = os.path.join(KNOWLEDGE_DIR, file_name)
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_knowledge(trip_type: str) -> Dict[str, Any]:
    """
    Récupère les connaissances pour un type de voyage
    
    Args:
        trip_type: Type de voyage (business, romantic, family, backpacker, leisure)
    
    Returns:
        Dict avec les règles et questions
    """
    file_map = {
        "business": "business.json",
        "romantic": "romantic.json",
        "family": "family.json",
        "backpacker": "backpacker.json",
        "leisure": "leisure.json"
    }
    
    file_name = file_map.get(trip_type, "leisure.json")
    return load_knowledge(file_name)


__all__ = ["load_knowledge", "get_knowledge"]
