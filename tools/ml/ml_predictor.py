import joblib
import pandas as pd
from itertools import product as iterproduct
from pathlib import Path

_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / 'data' / 'models'

_STYLES      = ['urban_outdoor', 'studio_minimal', 'lifestyle_indoor', 'casual_lifestyle', 'streetwear', 'lifestyle_outdoor']
_LIGHTINGS   = ['golden_hour', 'studio', 'natural', 'overcast', 'dramatic']
_BACKGROUNDS = ['studio_white', 'studio_grey', 'neutral_wall', 'urban_street', 'graffiti_wall', 'nature_outdoor', 'park', 'busy_pattern']
_POSES       = ['walking', 'standing', 'action', 'sitting', 'dynamic', 'casual']
_EXPRESSIONS = ['confident', 'serious', 'smiling', 'neutral', 'focused']
_ANGLES      = ['front', 'side', '3/4', 'back']

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
        in iterproduct(_STYLES, _LIGHTINGS, _BACKGROUNDS, _POSES, _EXPRESSIONS, _ANGLES)
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
