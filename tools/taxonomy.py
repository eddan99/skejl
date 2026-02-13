"""
Central taxonomy module for data normalization and consistency.

This module defines all valid values for product features and image settings,
ensuring consistency across products.json, conversion_db.json, and output files.
"""

from typing import Dict, Any


# Product Feature Taxonomies
GARMENT_TYPES = ['hoodie', 'jacket', 'jeans', 't-shirt', 'zip-up hoodie']
COLORS = ['black', 'colorful', 'dark', 'dark grey', 'light', 'white']
FITS = ['loose', 'oversized', 'regular', 'tight']
GENDERS = ['female', 'male', 'unisex']

# Image Settings Taxonomies
IMAGE_STYLES = [
    'casual_lifestyle',
    'lifestyle_indoor',
    'lifestyle_outdoor',
    'streetwear',
    'studio_minimal',
    'urban_outdoor'
]

LIGHTING_TYPES = [
    'dramatic',
    'golden_hour',
    'natural',
    'overcast',
    'studio'
]

BACKGROUNDS = [
    'busy_pattern',
    'graffiti_wall',
    'nature_outdoor',
    'neutral_wall',
    'park',
    'studio_grey',
    'studio_white',
    'urban_street'
]

POSES = ['action', 'casual', 'dynamic', 'sitting', 'standing', 'walking']
EXPRESSIONS = ['confident', 'focused', 'neutral', 'serious', 'smiling']
ANGLES = ['3/4', 'back', 'front', 'side']


def normalize_color(raw_color: str) -> str:
    """
    Normalize color value.

    Examples:
        "Dark grey" -> "dark grey"
        "Black" -> "black"
        "LIGHT" -> "light"

    Args:
        raw_color: Raw color string from input

    Returns:
        Normalized lowercase color
    """
    normalized = raw_color.lower().strip()

    # Validate against taxonomy
    if normalized not in COLORS:
        raise ValueError(
            f"Invalid color '{raw_color}'. Must be one of: {COLORS}"
        )

    return normalized


def normalize_fit(raw_fit: str) -> str:
    """
    Normalize fit value by removing "fit" suffix.

    Examples:
        "Loose fit" -> "loose"
        "Regular Fit" -> "regular"
        "oversized" -> "oversized"

    Args:
        raw_fit: Raw fit string from input

    Returns:
        Normalized lowercase fit without suffix
    """
    normalized = raw_fit.lower().replace(" fit", "").strip()

    # Validate against taxonomy
    if normalized not in FITS:
        raise ValueError(
            f"Invalid fit '{raw_fit}'. Must be one of: {FITS}"
        )

    return normalized


def normalize_garment_type(raw_type: str) -> str:
    """
    Normalize garment type.

    Examples:
        "Hoodie" -> "hoodie"
        "T-Shirt" -> "t-shirt"
        "Zip-up Hoodie" -> "zip-up hoodie"

    Args:
        raw_type: Raw garment type string

    Returns:
        Normalized lowercase garment type
    """
    normalized = raw_type.lower().strip()

    # Validate against taxonomy
    if normalized not in GARMENT_TYPES:
        raise ValueError(
            f"Invalid garment_type '{raw_type}'. Must be one of: {GARMENT_TYPES}"
        )

    return normalized


def normalize_gender(raw_gender: str) -> str:
    """
    Normalize gender value.

    Examples:
        "Male" -> "male"
        "FEMALE" -> "female"

    Args:
        raw_gender: Raw gender string

    Returns:
        Normalized lowercase gender
    """
    normalized = raw_gender.lower().strip()

    # Validate against taxonomy
    if normalized not in GENDERS:
        raise ValueError(
            f"Invalid gender '{raw_gender}'. Must be one of: {GENDERS}"
        )

    return normalized


def normalize_composition(comp_input: Any) -> str:
    """
    Normalize composition from dict or string to standard string format.

    Examples:
        {"Shell": "100% Cotton"} -> "Shell: 100% Cotton"
        {"Shell": "60% Cotton", "Lining": "40% Polyester"}
            -> "Shell: 60% Cotton, Lining: 40% Polyester"
        "Shell: 100% Cotton" -> "Shell: 100% Cotton"

    Args:
        comp_input: Composition as dict or string

    Returns:
        Normalized composition string
    """
    if isinstance(comp_input, str):
        return comp_input.strip()

    if isinstance(comp_input, dict):
        parts = [f"{key}: {value}" for key, value in comp_input.items()]
        return ", ".join(parts)

    raise ValueError(
        f"Invalid composition type {type(comp_input)}. Must be dict or str."
    )


def validate_image_settings(settings: Dict[str, str]) -> None:
    """
    Validate that all image settings match taxonomy values.

    Args:
        settings: Dict with keys: style, lighting, background, pose, expression, angle

    Raises:
        ValueError: If any setting value is invalid
    """
    validations = {
        'style': (settings.get('style'), IMAGE_STYLES),
        'lighting': (settings.get('lighting'), LIGHTING_TYPES),
        'background': (settings.get('background'), BACKGROUNDS),
        'pose': (settings.get('pose'), POSES),
        'expression': (settings.get('expression'), EXPRESSIONS),
        'angle': (settings.get('angle'), ANGLES)
    }

    for setting_name, (value, valid_values) in validations.items():
        if value is None:
            raise ValueError(f"Missing required image setting: {setting_name}")

        if value not in valid_values:
            raise ValueError(
                f"Invalid {setting_name} '{value}'. Must be one of: {valid_values}"
            )


def normalize_product_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize all product features in one call.

    Args:
        features: Dict with raw product features

    Returns:
        Dict with normalized features
    """
    return {
        'garment_type': normalize_garment_type(features['garment_type']),
        'color': normalize_color(features['color']),
        'fit': normalize_fit(features['fit']),
        'gender': normalize_gender(features['gender']),
        'composition': normalize_composition(features.get('composition', '')),
        # Preserve other fields as-is
        **{k: v for k, v in features.items()
           if k not in ['garment_type', 'color', 'fit', 'gender', 'composition']}
    }
