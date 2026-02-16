"""
Generate a synthetic CTR dataset with garment-specific style affinities.

Replaces the old uniform dataset that caused the ML model to always recommend
urban_outdoor. CTR is derived from a garment × style affinity matrix so each
garment type has a distinct best style, making model recommendations vary.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.taxonomy import (
    GARMENT_TYPES, COLORS, FITS, GENDERS,
    IMAGE_STYLES, LIGHTING_TYPES, BACKGROUNDS, POSES, EXPRESSIONS, ANGLES,
)
from config.paths import CTR_DATASET_PATH

random.seed(42)

N_SAMPLES = 3000

# Base CTR by garment type (reflects typical category engagement)
GARMENT_BASE_CTR: dict[str, float] = {
    't-shirt':       0.055,
    'polo':          0.050,
    'hoodie':        0.060,
    'zip-up hoodie': 0.058,
    'sweatshirt':    0.052,
    'jacket':        0.065,
    'bomber jacket': 0.063,
    'coat':          0.060,
    'windbreaker':   0.055,
    'parka':         0.050,
    'jeans':         0.048,
    'trousers':      0.042,
    'shorts':        0.045,
}

# Style affinity deltas — each garment has its own ideal style
STYLE_AFFINITY: dict[str, dict[str, float]] = {
    't-shirt': {
        'studio_minimal':    +0.012,
        'casual_lifestyle':  +0.008,
        'streetwear':        +0.004,
        'lifestyle_indoor':  +0.000,
        'urban_outdoor':     -0.005,
        'lifestyle_outdoor': -0.005,
    },
    'polo': {
        'casual_lifestyle':  +0.012,
        'lifestyle_outdoor': +0.010,
        'studio_minimal':    +0.004,
        'lifestyle_indoor':  +0.000,
        'streetwear':        -0.008,
        'urban_outdoor':     -0.005,
    },
    'hoodie': {
        'streetwear':        +0.015,
        'casual_lifestyle':  +0.010,
        'urban_outdoor':     +0.005,
        'lifestyle_indoor':  +0.000,
        'studio_minimal':    -0.008,
        'lifestyle_outdoor': -0.005,
    },
    'zip-up hoodie': {
        'streetwear':        +0.012,
        'urban_outdoor':     +0.008,
        'casual_lifestyle':  +0.006,
        'lifestyle_indoor':  +0.000,
        'studio_minimal':    -0.006,
        'lifestyle_outdoor': -0.004,
    },
    'sweatshirt': {
        'casual_lifestyle':  +0.012,
        'lifestyle_indoor':  +0.008,
        'streetwear':        +0.004,
        'studio_minimal':    +0.000,
        'urban_outdoor':     -0.003,
        'lifestyle_outdoor': -0.005,
    },
    'jacket': {
        'urban_outdoor':     +0.015,
        'lifestyle_outdoor': +0.010,
        'streetwear':        +0.005,
        'casual_lifestyle':  +0.000,
        'studio_minimal':    -0.010,
        'lifestyle_indoor':  -0.008,
    },
    'bomber jacket': {
        'streetwear':        +0.015,
        'urban_outdoor':     +0.012,
        'lifestyle_outdoor': +0.004,
        'casual_lifestyle':  +0.000,
        'studio_minimal':    -0.008,
        'lifestyle_indoor':  -0.010,
    },
    'coat': {
        'urban_outdoor':     +0.012,
        'lifestyle_outdoor': +0.010,
        'casual_lifestyle':  +0.004,
        'studio_minimal':    +0.000,
        'streetwear':        -0.006,
        'lifestyle_indoor':  -0.008,
    },
    'windbreaker': {
        'lifestyle_outdoor': +0.015,
        'urban_outdoor':     +0.008,
        'casual_lifestyle':  +0.004,
        'streetwear':        -0.005,
        'studio_minimal':    -0.010,
        'lifestyle_indoor':  -0.008,
    },
    'parka': {
        'lifestyle_outdoor': +0.015,
        'urban_outdoor':     +0.008,
        'casual_lifestyle':  +0.004,
        'streetwear':        -0.006,
        'studio_minimal':    -0.010,
        'lifestyle_indoor':  -0.008,
    },
    'jeans': {
        'casual_lifestyle':  +0.012,
        'streetwear':        +0.010,
        'urban_outdoor':     +0.005,
        'lifestyle_outdoor': +0.004,
        'lifestyle_indoor':  -0.005,
        'studio_minimal':    -0.008,
    },
    'trousers': {
        'studio_minimal':    +0.012,
        'lifestyle_indoor':  +0.010,
        'casual_lifestyle':  +0.004,
        'lifestyle_outdoor': -0.005,
        'urban_outdoor':     -0.008,
        'streetwear':        -0.010,
    },
    'shorts': {
        'lifestyle_outdoor': +0.015,
        'casual_lifestyle':  +0.010,
        'urban_outdoor':     +0.005,
        'streetwear':        -0.005,
        'lifestyle_indoor':  -0.008,
        'studio_minimal':    -0.010,
    },
}

# Lighting affinity per style
LIGHTING_AFFINITY: dict[str, dict[str, float]] = {
    'studio_minimal':    {'studio': +0.006, 'natural': +0.002, 'overcast': +0.000, 'golden_hour': -0.004, 'dramatic': -0.008},
    'lifestyle_indoor':  {'natural': +0.006, 'studio': +0.004, 'overcast': +0.000, 'golden_hour': -0.002, 'dramatic': -0.006},
    'lifestyle_outdoor': {'golden_hour': +0.008, 'natural': +0.006, 'overcast': +0.002, 'dramatic': -0.004, 'studio': -0.006},
    'casual_lifestyle':  {'natural': +0.006, 'golden_hour': +0.004, 'overcast': +0.002, 'studio': +0.000, 'dramatic': -0.004},
    'streetwear':        {'dramatic': +0.008, 'studio': +0.004, 'natural': +0.000, 'overcast': -0.002, 'golden_hour': -0.004},
    'urban_outdoor':     {'dramatic': +0.008, 'golden_hour': +0.004, 'natural': +0.004, 'overcast': +0.000, 'studio': -0.006},
}

# Background affinity per style
BACKGROUND_AFFINITY: dict[str, dict[str, float]] = {
    'studio_minimal':    {'studio_white': +0.008, 'studio_grey': +0.006, 'neutral_wall': +0.002, 'park': -0.006, 'nature_outdoor': -0.008, 'urban_street': -0.008, 'graffiti_wall': -0.010, 'busy_pattern': -0.010},
    'lifestyle_indoor':  {'neutral_wall': +0.008, 'studio_grey': +0.004, 'busy_pattern': +0.002, 'studio_white': +0.002, 'park': -0.002, 'nature_outdoor': -0.004, 'urban_street': -0.006, 'graffiti_wall': -0.008},
    'lifestyle_outdoor': {'park': +0.010, 'nature_outdoor': +0.008, 'urban_street': +0.002, 'neutral_wall': -0.004, 'graffiti_wall': -0.004, 'busy_pattern': -0.006, 'studio_grey': -0.006, 'studio_white': -0.008},
    'casual_lifestyle':  {'park': +0.006, 'neutral_wall': +0.006, 'nature_outdoor': +0.004, 'urban_street': +0.002, 'studio_grey': +0.000, 'studio_white': +0.000, 'graffiti_wall': -0.006, 'busy_pattern': -0.006},
    'streetwear':        {'graffiti_wall': +0.010, 'urban_street': +0.008, 'busy_pattern': +0.002, 'neutral_wall': +0.000, 'park': -0.004, 'studio_grey': -0.004, 'nature_outdoor': -0.006, 'studio_white': -0.008},
    'urban_outdoor':     {'urban_street': +0.010, 'graffiti_wall': +0.006, 'neutral_wall': +0.002, 'park': +0.002, 'nature_outdoor': -0.002, 'busy_pattern': -0.002, 'studio_grey': -0.006, 'studio_white': -0.010},
}

POSE_DELTA: dict[str, float] = {
    'walking':  +0.003,
    'dynamic':  +0.003,
    'action':   +0.002,
    'casual':   +0.001,
    'standing': +0.000,
    'sitting':  -0.002,
}
EXPRESSION_DELTA: dict[str, float] = {
    'confident': +0.003,
    'smiling':   +0.002,
    'focused':   +0.001,
    'neutral':   +0.000,
    'serious':   -0.001,
}
ANGLE_DELTA: dict[str, float] = {
    '3/4':   +0.003,
    'front': +0.001,
    'side':  +0.000,
    'back':  -0.003,
}


def _compute_ctr(
    garment_type: str,
    style: str,
    lighting: str,
    background: str,
    pose: str,
    expression: str,
    angle: str,
) -> float:
    base = GARMENT_BASE_CTR[garment_type]
    delta = (
        STYLE_AFFINITY[garment_type].get(style, 0.0)
        + LIGHTING_AFFINITY[style].get(lighting, 0.0)
        + BACKGROUND_AFFINITY[style].get(background, 0.0)
        + POSE_DELTA.get(pose, 0.0)
        + EXPRESSION_DELTA.get(expression, 0.0)
        + ANGLE_DELTA.get(angle, 0.0)
    )
    noisy = base + delta + random.gauss(0, 0.005)
    return round(max(0.01, min(0.12, noisy)), 4)


def generate(n: int = N_SAMPLES) -> list[dict]:
    records = []
    for _ in range(n):
        garment_type = random.choice(GARMENT_TYPES)
        color        = random.choice(COLORS)
        fit          = random.choice(FITS)
        gender       = random.choice(GENDERS)
        style        = random.choice(IMAGE_STYLES)
        lighting     = random.choice(LIGHTING_TYPES)
        background   = random.choice(BACKGROUNDS)
        pose         = random.choice(POSES)
        expression   = random.choice(EXPRESSIONS)
        angle        = random.choice(ANGLES)

        records.append({
            'garment_type': garment_type,
            'color':        color,
            'fit':          fit,
            'gender':       gender,
            'style':        style,
            'lighting':     lighting,
            'background':   background,
            'pose':         pose,
            'expression':   expression,
            'angle':        angle,
            'ctr':          _compute_ctr(garment_type, style, lighting, background, pose, expression, angle),
            'impressions':  random.randint(500, 5000),
        })
    return records


if __name__ == '__main__':
    CTR_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = generate()
    with open(CTR_DATASET_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(data)} samples → {CTR_DATASET_PATH}")
