"""
Performance Lookup - Database agnostic interface

Automatically selects database adapter based on DATABASE_TYPE environment variable.
- "json" → Uses JSON file (development)
- "mongodb" → Uses MongoDB Atlas (production)

Toggle in .env:
    DATABASE_TYPE=json  # or mongodb
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path for imports
if __name__ == "__main__":
    parent_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(parent_dir))

from tools.database import JSONDatabase, MongoDatabase

# Minimum impressions threshold for statistical significance
MIN_IMPRESSIONS = 1000


def _get_database():
    """
    Factory function to get appropriate database adapter.

    Returns:
        DatabaseAdapter instance (JSON or MongoDB)
    """
    db_type = os.getenv("DATABASE_TYPE", "json").lower()

    if db_type == "mongodb":
        return MongoDatabase()
    else:
        return JSONDatabase()


# Global database instance
_db = None


def get_db():
    """Get database instance (singleton)."""
    global _db
    if _db is None:
        _db = _get_database()
    return _db


def search_similar(
    garment_type: str,
    color: str,
    max_results: int = 5,
    min_impressions: int = MIN_IMPRESSIONS
) -> List[Dict]:
    """
    Search for similar products by garment_type and color.

    Used by Performance Agent to get exact historical data.

    Args:
        garment_type: e.g. "hoodie", "t-shirt", "jacket"
        color: e.g. "dark", "light", "colorful"
        max_results: Max number of results (default: 5)
        min_impressions: Minimum impressions for statistical significance (default: 1000)

    Returns:
        List of products sorted by conversion_rate descending
    """
    db = get_db()
    return db.search_similar(garment_type, color, max_results, min_impressions)


def get_best_image_settings(
    garment_type: str,
    color: str,
    min_impressions: int = MIN_IMPRESSIONS
) -> Optional[Dict]:
    """
    Returns best performing image settings for given product type.

    Used as FALLBACK if multi-agent debate cannot reach consensus.

    Args:
        garment_type: e.g. "hoodie"
        color: e.g. "dark"
        min_impressions: Minimum impressions threshold (default: 1000)

    Returns:
        Dict with recommendation or None if no data
    """
    db = get_db()
    return db.get_best_image_settings(garment_type, color, min_impressions)


def add_product(product: dict) -> bool:
    """
    Add product to database.

    Args:
        product: Dict with id, garment_type, color, image_settings, performance

    Returns:
        True if successful
    """
    db = get_db()
    return db.add_product(product)


def get_total_products() -> int:
    """
    Get total number of products in database.

    Returns:
        Count of products
    """
    db = get_db()
    return db.get_total_products()


if __name__ == "__main__":
    # Test
    db_type = os.getenv("DATABASE_TYPE", "json")
    print(f"Testing Performance Lookup with {db_type.upper()} database...")

    # Get total products
    total = get_total_products()
    print(f"Total products: {total}")

    if total > 0:
        # Test search
        results = search_similar("hoodie", "dark")
        print(f"\nFound {len(results)} dark hoodies with 1000+ impressions")

        if results:
            print("\nTop 3 results:")
            for i, product in enumerate(results[:3], 1):
                perf = product.get("performance", {})
                settings = product.get("image_settings", {})
                print(f"  {i}. {product.get('id')}")
                print(f"     Conversion: {perf.get('conversion_rate', 0):.2%} ({perf.get('impressions', 0)} impressions)")
                print(f"     Style: {settings.get('style')}, Lighting: {settings.get('lighting')}")

        # Test best settings
        best = get_best_image_settings("hoodie", "dark")
        if best:
            print("\nBest image settings (fallback):")
            print(best["reasoning"])
    else:
        print("\nNo data in database")
        if db_type == "json":
            print("Run: python tools/generate_synthetic_data.py")
        else:
            print("Import data to MongoDB first")
