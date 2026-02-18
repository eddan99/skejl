import joblib
import pandas as pd
from itertools import product as iterproduct
from pathlib import Path

from tools.taxonomy import IMAGE_STYLES, LIGHTING_TYPES, BACKGROUNDS, POSES, EXPRESSIONS, ANGLES

_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / 'data' / 'models'

_IMAGE_SETTINGS = ['style', 'lighting', 'background', 'pose', 'expression', 'angle']


def _load_model():
    model = joblib.load(_MODEL_DIR / 'rf_ctr_model.pkl')
    feature_columns = joblib.load(_MODEL_DIR / 'feature_columns.pkl')
    return model, feature_columns


def predict_image_settings(garment_type: str, color: str, fit: str, gender: str) -> dict:
    model, feature_columns = _load_model()

    rows = [
        {'garment_type': garment_type, 'color': color, 'fit': fit, 'gender': gender,
         'style': st, 'lighting': li, 'background': bg,
         'pose': po, 'expression': ex, 'angle': an}
        for st, li, bg, po, ex, an
        in iterproduct(IMAGE_STYLES, LIGHTING_TYPES, BACKGROUNDS, POSES, EXPRESSIONS, ANGLES)
    ]

    candidates = pd.DataFrame(rows)
    X = pd.get_dummies(candidates).reindex(columns=feature_columns, fill_value=0)
    candidates['predicted_ctr'] = model.predict(X)

    best = candidates.nlargest(1, 'predicted_ctr').iloc[0]

    return {
        'image_settings': {col: best[col] for col in _IMAGE_SETTINGS},
        'predicted_conversion_rate': round(float(best['predicted_ctr']), 4),
        'confidence': 0.56,
        'reasoning': f'RandomForest predicted {best["predicted_ctr"]*100:.2f}% CTR from {len(rows)} combinations'
    }
