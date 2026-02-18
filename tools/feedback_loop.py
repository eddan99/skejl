import json
import random
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from config.paths import CTR_DATASET_PATH, MODELS_DIR, RF_CTR_MODEL_PATH, FEATURE_COLUMNS_PATH
from tools.db import get_db

_COLLECTION = "ctr_samples"

_ALL_FEATURES = [
    "garment_type", "color", "fit", "gender",
    "style", "lighting", "background", "pose", "expression", "angle",
]

_IMAGE_SETTINGS_KEYS = ["style", "lighting", "background", "pose", "expression", "angle"]


def _extract_final_image_settings(result: dict) -> dict | None:
    try:
        settings = result["ml_metadata"]["debate_log"]["moderator_decision"]["final_image_settings"]
        if all(k in settings for k in _IMAGE_SETTINGS_KEYS):
            return settings
    except (KeyError, TypeError):
        pass

    try:
        settings = result["ml_metadata"]["ml_prediction"]["image_settings"]
        if all(k in settings for k in _IMAGE_SETTINGS_KEYS):
            return settings
    except (KeyError, TypeError):
        pass

    return None


def record_published_product(result: dict) -> dict | None:
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
        predicted_ctr = 0.045

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

    db = get_db()
    if db is not None:
        db.collection(_COLLECTION).add({**record, "published_at": datetime.now(timezone.utc)})

    dataset = []
    if CTR_DATASET_PATH.exists():
        with open(CTR_DATASET_PATH, "r", encoding="utf-8") as f:
            dataset = json.load(f)

    dataset.append(record)

    with open(CTR_DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    return record


def retrain_model() -> dict:
    db = get_db()
    if db is not None:
        data = []
        for doc in db.collection(_COLLECTION).stream():
            record = doc.to_dict()
            record.pop("published_at", None)
            data.append(record)
        if not data and CTR_DATASET_PATH.exists():
            with open(CTR_DATASET_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
    elif CTR_DATASET_PATH.exists():
        with open(CTR_DATASET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

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
    db = get_db()
    if db is not None:
        return db.collection(_COLLECTION).count().get()[0][0].value
    if not CTR_DATASET_PATH.exists():
        return 0
    with open(CTR_DATASET_PATH, "r", encoding="utf-8") as f:
        return len(json.load(f))
