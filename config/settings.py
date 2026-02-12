"""
Centralized configuration for the entire application.
"""
import os
from typing import Optional


class Settings:
    DEFAULT_BRAND_IDENTITY: str = (
        "A modern, minimalist e-commerce brand. Clean, confident, and always "
        "doing references to breaking bad series"
    )

    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_API_KEY: Optional[str] = None

    USE_ML_PREDICTION: bool = False
    ML_MIN_IMPRESSIONS: int = 1000

    MAX_GENERATION_ATTEMPTS: int = 2
    MAX_VARIANT_ATTEMPTS: int = 2

    UPLOAD_TO_SHOPIFY: bool = False

    RATE_LIMIT_DELAY: int = 3
    PROCESSING_DELAY: int = 5

    def __init__(self):
        self._load_from_env()

    def _load_from_env(self):
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        self.USE_ML_PREDICTION = os.getenv("USE_ML_PREDICTION", "false").lower() == "true"
        self.UPLOAD_TO_SHOPIFY = os.getenv("UPLOAD_TO_SHOPIFY", "false").lower() == "true"

        env_brand = os.getenv("BRAND_IDENTITY")
        if env_brand:
            self.DEFAULT_BRAND_IDENTITY = env_brand

        env_model = os.getenv("GEMINI_MODEL_NAME")
        if env_model:
            self.GEMINI_MODEL_NAME = env_model

        env_min_impressions = os.getenv("ML_MIN_IMPRESSIONS")
        if env_min_impressions:
            try:
                self.ML_MIN_IMPRESSIONS = int(env_min_impressions)
            except ValueError:
                pass

    def update_from_db(self, db_settings: dict):

        if "brand_identity" in db_settings:
            self.DEFAULT_BRAND_IDENTITY = db_settings["brand_identity"]

        if "model_name" in db_settings:
            self.GEMINI_MODEL_NAME = db_settings["model_name"]

        if "use_ml_prediction" in db_settings:
            self.USE_ML_PREDICTION = db_settings["use_ml_prediction"]

        if "upload_to_shopify" in db_settings:
            self.UPLOAD_TO_SHOPIFY = db_settings["upload_to_shopify"]

        if "max_generation_attempts" in db_settings:
            self.MAX_GENERATION_ATTEMPTS = db_settings["max_generation_attempts"]

        if "max_variant_attempts" in db_settings:
            self.MAX_VARIANT_ATTEMPTS = db_settings["max_variant_attempts"]

settings = Settings()
