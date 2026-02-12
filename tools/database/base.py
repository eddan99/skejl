"""
Abstract base class for database adapters.

Defines interface that all database implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class DatabaseAdapter(ABC):
    """
    Abstract interface for performance database.

    All implementations (JSON, MongoDB) must implement these methods.
    """

    @abstractmethod
    def search_similar(
        self,
        garment_type: str,
        color: str,
        max_results: int = 5,
        min_impressions: int = 1000
    ) -> List[Dict]:
        """
        Search for similar products by garment_type and color.

        Args:
            garment_type: e.g. "hoodie", "t-shirt"
            color: e.g. "dark", "light"
            max_results: Maximum results to return
            min_impressions: Minimum impressions threshold

        Returns:
            List of products sorted by conversion_rate (highest first)
        """
        pass

    @abstractmethod
    def get_best_image_settings(
        self,
        garment_type: str,
        color: str,
        min_impressions: int = 1000
    ) -> Optional[Dict]:
        """
        Get best performing image settings for product type.

        Args:
            garment_type: e.g. "hoodie"
            color: e.g. "dark"
            min_impressions: Minimum impressions threshold

        Returns:
            Dict with image_settings and reasoning, or None
        """
        pass

    @abstractmethod
    def add_product(self, product: dict) -> bool:
        """
        Add product to database.

        Args:
            product: Product dict with all required fields

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_total_products(self) -> int:
        """
        Get total number of products in database.

        Returns:
            Count of products
        """
        pass
