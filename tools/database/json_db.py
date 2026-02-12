"""
JSON Database Adapter - For development/prototyping

Reads from conversion_db.json file.
Fast and simple for small datasets (< 1000 products).
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

from .base import DatabaseAdapter


class JSONDatabase(DatabaseAdapter):
    """JSON file-based database implementation."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize JSON database.

        Args:
            db_path: Path to JSON file (default: data/conversion_db.json)
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            db_path = project_root / "data" / "conversion_db.json"

        self.db_path = db_path

    def _load_data(self) -> dict:
        """Load data from JSON file."""
        if not self.db_path.exists():
            return {"products": []}

        with open(self.db_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def search_similar(
        self,
        garment_type: str,
        color: str,
        max_results: int = 5,
        min_impressions: int = 1000
    ) -> List[Dict]:
        """Search for similar products in JSON file."""
        data = self._load_data()
        products = data.get("products", [])

        if not products:
            return []

        # Filter by garment_type, color, and minimum impressions
        matches = [
            product for product in products
            if product.get("garment_type") == garment_type
            and product.get("color") == color
            and product.get("performance", {}).get("impressions", 0) >= min_impressions
        ]

        # Sort by conversion_rate (highest first)
        matches.sort(
            key=lambda p: p.get("performance", {}).get("conversion_rate", 0),
            reverse=True
        )

        return matches[:max_results]

    def get_best_image_settings(
        self,
        garment_type: str,
        color: str,
        min_impressions: int = 1000
    ) -> Optional[Dict]:
        """Get best performing image settings from JSON data."""
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
        """Add product to JSON file."""
        data = self._load_data()

        if "products" not in data:
            data["products"] = []

        data["products"].append(product)

        from datetime import datetime
        data["last_updated"] = datetime.now().isoformat()

        with open(self.db_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

        return True

    def get_total_products(self) -> int:
        """Get total number of products in JSON file."""
        data = self._load_data()
        return len(data.get("products", []))
