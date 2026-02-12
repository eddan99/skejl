"""
MongoDB Database Adapter - For production/scale

Uses MongoDB Atlas (cloud) or local MongoDB.
Efficient for large datasets (1000+ products).
"""

import os
from typing import List, Dict, Optional

from .base import DatabaseAdapter

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


class MongoDatabase(DatabaseAdapter):
    """MongoDB database implementation."""

    def __init__(self, connection_uri: Optional[str] = None, db_name: str = "skejl_db"):
        """
        Initialize MongoDB database.

        Args:
            connection_uri: MongoDB connection string (default: from MONGODB_URI env)
            db_name: Database name (default: skejl_db)
        """
        if not PYMONGO_AVAILABLE:
            raise ImportError(
                "pymongo is required for MongoDB support. "
                "Install with: pip install pymongo"
            )

        if connection_uri is None:
            connection_uri = os.getenv("MONGODB_URI")

        if not connection_uri:
            raise ValueError(
                "MongoDB connection URI required. "
                "Set MONGODB_URI in .env or pass to constructor"
            )

        self.client = MongoClient(connection_uri)
        self.db = self.client[db_name]
        self.collection = self.db["products"]

        # Test connection
        try:
            self.client.admin.command('ping')
        except ConnectionFailure:
            raise ConnectionError("Failed to connect to MongoDB")

        # Create indexes for fast queries
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for fast queries."""
        # Compound index on garment_type + color
        self.collection.create_index([("garment_type", 1), ("color", 1)])

        # Index on impressions for filtering
        self.collection.create_index([("performance.impressions", 1)])

        # Index on conversion_rate for sorting
        self.collection.create_index([("performance.conversion_rate", -1)])

    def search_similar(
        self,
        garment_type: str,
        color: str,
        max_results: int = 5,
        min_impressions: int = 1000
    ) -> List[Dict]:
        """Search for similar products in MongoDB."""
        # MongoDB query
        query = {
            "garment_type": garment_type,
            "color": color,
            "performance.impressions": {"$gte": min_impressions}
        }

        # Sort by conversion_rate (highest first)
        cursor = self.collection.find(query).sort(
            "performance.conversion_rate", -1
        ).limit(max_results)

        # Convert to list
        results = list(cursor)

        # Remove MongoDB _id field (not JSON serializable)
        for result in results:
            if "_id" in result:
                del result["_id"]

        return results

    def get_best_image_settings(
        self,
        garment_type: str,
        color: str,
        min_impressions: int = 1000
    ) -> Optional[Dict]:
        """Get best performing image settings from MongoDB."""
        matches = self.search_similar(garment_type, color, max_results=5, min_impressions=min_impressions)

        if not matches:
            return None

        best = matches[0]
        best_performance = best.get("performance", {})
        best_settings = best.get("image_settings", {})

        reasoning = (
            f"Based on {len(matches)} {color} {garment_type}s with {min_impressions}+ impressions:\n"
            f"Best performer: {best.get('id')} with {best_performance.get('conversion_rate', 0):.1%} conversion\n"
            f"Recommended style: {best_settings.get('style')}"
        )

        return {
            "image_settings": best_settings,
            "conversion_rate": best_performance.get("conversion_rate", 0),
            "impressions": best_performance.get("impressions", 0),
            "reasoning": reasoning
        }

    def add_product(self, product: dict) -> bool:
        """Add product to MongoDB."""
        result = self.collection.insert_one(product)
        return result.acknowledged

    def get_total_products(self) -> int:
        """Get total number of products in MongoDB."""
        return self.collection.count_documents({})

    def close(self):
        """Close MongoDB connection."""
        self.client.close()
