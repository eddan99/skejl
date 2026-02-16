"""
Feedback loop: records published products as new training samples.

When a product is published to Shopify, its real garment features and the
image settings chosen by the debate system are appended to ctr_dataset.json
with synthetically generated CTR and impressions values.

In production these metrics would be sourced from GA4 (via the Analytics Data
API) or the Shopify Analytics API. For this study they are simulated to
demonstrate the full feedback-loop architecture while controlling for the
absence of live traffic.
"""

import json
import random

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from config.paths import CTR_DATASET_PATH, MODELS_DIR, RF_CTR_MODEL_PATH, FEATURE_COLUMNS_PATH

_ALL_FEATURES = [
    "garment_type", "color", "fit", "gender",
    "style", "lighting", "background", "pose", "expression", "angle",
]

_IMAGE_SETTINGS_KEYS = ["style", "lighting", "background", "pose", "expression", "angle"]


def _extract_final_image_settings(result: dict) -> dict | None:
    """Return the consensus image settings that were actually used."""
    try:
        settings = result["ml_metadata"]["debate_log"]["moderator_decision"]["final_image_settings"]
        if all(k in settings for k in _IMAGE_SETTINGS_KEYS):
            return settings
    except (KeyError, TypeError):
        pass

    # Fallback: raw ML prediction settings
    try:
        settings = result["ml_metadata"]["ml_prediction"]["image_settings"]
        if all(k in settings for k in _IMAGE_SETTINGS_KEYS):
            return settings
    except (KeyError, TypeError):
        pass

    return None


def record_published_product(result: dict) -> dict | None:
    """
    Append one new training sample to ctr_dataset.json.

    Uses the product's real garment features and the image settings chosen
    by the debate system. CTR is derived from the ML model's predicted value
    with Gaussian noise (std=0.004) to simulate natural variance.
    Impressions are sampled uniformly from [500, 5000].

    Returns the appended record, or None if required fields are missing.
    """
    garment_type = result.get("garment_type", "")
    color = result.get("color", "")
    fit = result.get("fit", "")
    gender = result.get("gender", "")

    if not all([garment_type, color, fit, gender]):
        return None

    image_settings = _extract_final_image_settings(result)
    if image_settings is None:
        return None

    try:
        predicted_ctr = result["ml_metadata"]["ml_prediction"]["predicted_conversion_rate"]
    except (KeyError, TypeError):
        predicted_ctr = 0.045  # dataset mean as fallback

    noisy_ctr = max(0.01, min(0.12, predicted_ctr + random.gauss(0, 0.004)))

    record = {
        "garment_type": garment_type,
        "color": color,
        "fit": fit,
        "gender": gender,
        **{k: image_settings[k] for k in _IMAGE_SETTINGS_KEYS},
        "ctr": round(noisy_ctr, 4),
        "impressions": random.randint(500, 5000),
    }

    dataset = []
    if CTR_DATASET_PATH.exists():
        with open(CTR_DATASET_PATH, "r", encoding="utf-8") as f:
            dataset = json.load(f)

    dataset.append(record)

    with open(CTR_DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    return record


def retrain_model() -> dict:
    """
    Retrain the RandomForest CTR model on the current ctr_dataset.json.
    Mirrors the logic in tools/ml/train_model.ipynb exactly.

    Returns metrics: n_samples, mae, r2.
    """
    with open(CTR_DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    X = pd.get_dummies(df[_ALL_FEATURES])
    y = df["ctr"]
    feature_columns = list(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    rf = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)

    mae = mean_absolute_error(y_test, rf.predict(X_test))
    r2 = r2_score(y_test, rf.predict(X_test))

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf, RF_CTR_MODEL_PATH)
    joblib.dump(feature_columns, FEATURE_COLUMNS_PATH)

    return {"n_samples": len(df), "mae": round(mae, 5), "r2": round(r2, 3)}


def get_dataset_size() -> int:
    if not CTR_DATASET_PATH.exists():
        return 0
    with open(CTR_DATASET_PATH, "r", encoding="utf-8") as f:
        return len(json.load(f))
