"""
ML Predictor - RandomForest model for predicting optimal image settings.

Trains on historical conversion data to predict which image settings
(style, lighting, background, pose, expression, angle) will achieve
highest conversion rates for given product features.

Model: RandomForestClassifier with MultiOutputClassifier wrapper
Input: garment_type, color, fit, gender (one-hot encoded)
Output: 6 image_settings + predicted conversion_rate
"""

import json
import os
import sys
import joblib
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Setup path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import (
    CONVERSION_DB_JSON,
    MODELS_DIR,
    RF_MODEL_PATH,
    LABEL_ENCODERS_PATH,
    METADATA_PATH,
    ensure_directories
)


def train_model(min_impressions: int = 1000, test_size: float = 0.2) -> Dict:
    """
    Train RandomForest model on conversion data.

    Args:
        min_impressions: Minimum impressions for statistical significance
        test_size: Fraction of data to use for testing

    Returns:
        Dict with training metrics
    """
    print(f"Loading data from {CONVERSION_DB_JSON}...")

    with open(CONVERSION_DB_JSON, 'r') as f:
        data = json.load(f)

    products = data['products']

    # Filter by minimum impressions
    valid_products = [
        p for p in products
        if p['performance']['impressions'] >= min_impressions
    ]

    print(f"Training on {len(valid_products)} products (min impressions: {min_impressions})")

    # Prepare features (X) and targets (y)
    X_raw = []
    y_raw = []

    for p in valid_products:
        # Features: garment_type, color, fit, gender
        X_raw.append([
            p['garment_type'],
            p['color'],
            p['fit'],
            p['gender']
        ])

        # Targets: 6 image settings
        settings = p['image_settings']
        y_raw.append([
            settings['style'],
            settings['lighting'],
            settings['background'],
            settings['pose'],
            settings['expression'],
            settings['angle']
        ])

    # Encode features
    feature_names = ['garment_type', 'color', 'fit', 'gender']
    target_names = ['style', 'lighting', 'background', 'pose', 'expression', 'angle']

    feature_encoders = {}
    X_encoded = []

    for i, name in enumerate(feature_names):
        encoder = LabelEncoder()
        column = [row[i] for row in X_raw]
        encoder.fit(column)
        encoded = encoder.transform(column)
        feature_encoders[name] = encoder
        X_encoded.append(encoded)

    X = np.column_stack(X_encoded)

    # Encode targets
    target_encoders = {}
    y_encoded = []

    for i, name in enumerate(target_names):
        encoder = LabelEncoder()
        column = [row[i] for row in y_raw]
        encoder.fit(column)
        encoded = encoder.transform(column)
        target_encoders[name] = encoder
        y_encoded.append(encoded)

    y = np.column_stack(y_encoded)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )

    # Train model
    print("Training RandomForest model...")
    base_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )

    model = MultiOutputClassifier(base_model)
    model.fit(X_train, y_train)

    # Evaluate
    print("Evaluating model...")
    y_pred = model.predict(X_test)

    accuracies = {}
    for i, name in enumerate(target_names):
        acc = accuracy_score(y_test[:, i], y_pred[:, i])
        accuracies[name] = acc
        print(f"  {name}: {acc:.2%}")

    avg_accuracy = np.mean(list(accuracies.values()))
    print(f"  Average accuracy: {avg_accuracy:.2%}")

    # Save model and encoders
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Saving model to {RF_MODEL_PATH}...")
    joblib.dump(model, RF_MODEL_PATH)

    encoders = {
        'features': feature_encoders,
        'targets': target_encoders,
        'feature_names': feature_names,
        'target_names': target_names
    }
    joblib.dump(encoders, LABEL_ENCODERS_PATH)

    # Save metadata
    metadata = {
        'training_size': len(X_train),
        'test_size': len(X_test),
        'accuracies': accuracies,
        'avg_accuracy': avg_accuracy,
        'min_impressions': min_impressions
    }

    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

    print("Model training complete!")

    return metadata


def _load_model() -> Tuple:
    """Load trained model and encoders."""
    if not RF_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {RF_MODEL_PATH}. Run train_model() first."
        )

    model = joblib.load(RF_MODEL_PATH)
    encoders = joblib.load(LABEL_ENCODERS_PATH)

    return model, encoders


def _encode_features(features: Dict[str, str], encoders: Dict) -> np.ndarray:
    """Encode input features using label encoders."""
    feature_names = encoders['feature_names']
    feature_encoders = encoders['features']

    encoded = []
    for name in feature_names:
        value = features[name]
        encoder = feature_encoders[name]

        if value not in encoder.classes_:
            raise ValueError(
                f"Unknown {name} value: '{value}'. "
                f"Valid values: {list(encoder.classes_)}"
            )

        encoded.append(encoder.transform([value])[0])

    return np.array([encoded])


def _decode_predictions(predictions: np.ndarray, encoders: Dict) -> Dict[str, str]:
    """Decode model predictions to image settings."""
    target_names = encoders['target_names']
    target_encoders = encoders['targets']

    settings = {}
    for i, name in enumerate(target_names):
        encoder = target_encoders[name]
        settings[name] = encoder.inverse_transform([predictions[0][i]])[0]

    return settings


def _estimate_conversion_rate(
    image_settings: Dict[str, str],
    product_features: Dict[str, str]
) -> float:
    """
    Estimate conversion rate by finding similar products in historical data.
    """
    with open(CONVERSION_DB_JSON, 'r') as f:
        data = json.load(f)

    products = data['products']

    # Find products with matching features and settings
    similar_products = []

    for p in products:
        feature_match = all(
            p.get(key) == value
            for key, value in product_features.items()
        )

        settings_match = all(
            p['image_settings'].get(key) == value
            for key, value in image_settings.items()
        )

        if feature_match and settings_match:
            similar_products.append(p)

    if similar_products:
        # Average conversion rate from similar products
        avg_conv = np.mean([
            p['performance']['conversion_rate']
            for p in similar_products
        ])
        return avg_conv
    else:
        # No exact match, return average for feature combination
        feature_matches = [
            p for p in products
            if all(p.get(key) == value for key, value in product_features.items())
        ]

        if feature_matches:
            return np.mean([
                p['performance']['conversion_rate']
                for p in feature_matches
            ])
        else:
            # Fallback to overall average
            return np.mean([p['performance']['conversion_rate'] for p in products])


def predict_image_settings(
    garment_type: str,
    color: str,
    fit: str,
    gender: str
) -> Dict:
    """
    Predict optimal image settings for given product features.

    Args:
        garment_type: Type of garment (e.g., "hoodie")
        color: Color (e.g., "dark")
        fit: Fit style (e.g., "loose")
        gender: Target gender (e.g., "male")

    Returns:
        Dict with:
            - image_settings: Predicted settings (6 fields)
            - predicted_conversion_rate: Estimated conversion rate
            - confidence: Model confidence (average accuracy)
            - reasoning: Explanation of prediction
    """
    model, encoders = _load_model()

    features = {
        'garment_type': garment_type,
        'color': color,
        'fit': fit,
        'gender': gender
    }

    # Encode and predict
    X = _encode_features(features, encoders)
    predictions = model.predict(X)

    # Decode predictions
    image_settings = _decode_predictions(predictions, encoders)

    # Estimate conversion rate
    predicted_conversion = _estimate_conversion_rate(image_settings, features)

    # Load metadata for confidence
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)

    confidence = metadata['avg_accuracy']

    # Generate reasoning
    reasoning = (
        f"Based on {metadata['training_size']} similar products with "
        f"{metadata['min_impressions']}+ impressions. "
        f"Model confidence: {confidence:.1%}"
    )

    return {
        'image_settings': image_settings,
        'predicted_conversion_rate': predicted_conversion,
        'confidence': confidence,
        'reasoning': reasoning
    }


if __name__ == "__main__":
    # Train model if run directly
    print("Training ML model...")
    metrics = train_model(min_impressions=1000)

    print("\nModel metrics:")
    print(json.dumps(metrics, indent=2))

    print("\nTesting prediction...")
    result = predict_image_settings(
        garment_type="hoodie",
        color="dark",
        fit="loose",
        gender="male"
    )

    print("\nPrediction result:")
    print(json.dumps(result, indent=2))
