"""
SmartCart AI - FastAPI Dependencies
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db

# Re-export get_db for convenient endpoint injection
DatabaseSession = Depends(get_db)
