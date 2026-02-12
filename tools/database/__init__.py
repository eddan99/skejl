"""
Database adapters for performance data storage.

Supports both JSON (development) and MongoDB (production) with toggle.
"""

from .base import DatabaseAdapter
from .json_db import JSONDatabase
from .mongo_db import MongoDatabase

__all__ = ["DatabaseAdapter", "JSONDatabase", "MongoDatabase"]
