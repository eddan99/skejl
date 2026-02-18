from typing import Dict, Any


GARMENT_TYPES = [
    'hoodie', 'zip-up hoodie', 'sweatshirt',
    't-shirt', 'polo',
    'jacket', 'bomber jacket', 'coat', 'windbreaker', 'parka',
    'jeans', 'trousers', 'shorts'
]

_COLOR_ALIASES: dict[str, str] = {
    'brown': 'dark brown',
    'dark brown': 'dark brown',
    'grey': 'dark grey',
    'gray': 'dark grey',
    'dark gray': 'dark grey',
    'light gray': 'light grey',
    'medium grey': 'dark grey',
    'medium gray': 'dark grey',
    'off-white': 'cream',
    'off white': 'cream',
    'ivory': 'cream',
    'khaki': 'sand',
    'tan': 'sand',
    'camel': 'sand',
    'dark blue': 'navy',
    'dark green': 'forest green',
    'dark red': 'burgundy',
    'maroon': 'burgundy',
    'bright': 'colorful',
    'multicolor': 'colorful',
    'multi': 'colorful',
    'patterned': 'colorful',
}

_GARMENT_ALIASES: dict[str, str] = {
    'zip hoodie': 'zip-up hoodie',
    'zip up hoodie': 'zip-up hoodie',
    'full zip hoodie': 'zip-up hoodie',
    'crewneck': 'sweatshirt',
    'crew neck': 'sweatshirt',
    'tee': 't-shirt',
    'tshirt': 't-shirt',
    'dress pants': 'trousers',
    'chinos': 'trousers',
    'cargo pants': 'trousers',
    'cargo shorts': 'shorts',
    'denim': 'jeans',
    'leather jacket': 'jacket',
    'denim jacket': 'jacket',
    'varsity jacket': 'jacket',
    'fur jacket': 'jacket',
    'fur bomber': 'bomber jacket',
    'fur bomber jacket': 'bomber jacket',
    'flight jacket': 'bomber jacket',
    'rain jacket': 'windbreaker',
    'anorak': 'windbreaker',
    'down jacket': 'parka',
    'winter coat': 'coat',
    'overcoat': 'coat',
    'trench coat': 'coat',
}
COLORS = [
    'black', 'white', 'dark grey', 'light grey',
    'dark', 'dark brown', 'navy', 'burgundy', 'olive', 'forest green',
    'light', 'beige', 'cream', 'sand', 'light blue',
    'colorful', 'red', 'yellow', 'orange', 'green', 'blue', 'pink', 'purple'
]
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
    normalized = raw_color.lower().strip()
    normalized = _COLOR_ALIASES.get(normalized, normalized)

    if normalized not in COLORS:
        raise ValueError(
            f"Invalid color '{raw_color}'. Must be one of: {COLORS}"
        )

    return normalized


def normalize_fit(raw_fit: str) -> str:
    normalized = raw_fit.lower().replace(" fit", "").strip()

    if normalized not in FITS:
        raise ValueError(
            f"Invalid fit '{raw_fit}'. Must be one of: {FITS}"
        )

    return normalized


def normalize_garment_type(raw_type: str) -> str:
    normalized = raw_type.lower().strip()
    normalized = _GARMENT_ALIASES.get(normalized, normalized)

    if normalized not in GARMENT_TYPES:
        raise ValueError(
            f"Invalid garment_type '{raw_type}'. Must be one of: {GARMENT_TYPES}"
        )

    return normalized


def normalize_gender(raw_gender: str) -> str:
    normalized = raw_gender.lower().strip()

    if normalized not in GENDERS:
        raise ValueError(
            f"Invalid gender '{raw_gender}'. Must be one of: {GENDERS}"
        )

    return normalized


def normalize_composition(comp_input: Any) -> str:
    if isinstance(comp_input, str):
        return comp_input.strip()

    if isinstance(comp_input, dict):
        parts = [f"{key}: {value}" for key, value in comp_input.items()]
        return ", ".join(parts)

    raise ValueError(
        f"Invalid composition type {type(comp_input)}. Must be dict or str."
    )


def validate_image_settings(settings: Dict[str, str]) -> None:
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
    return {
        'garment_type': normalize_garment_type(features['garment_type']),
        'color': normalize_color(features['color']),
        'fit': normalize_fit(features['fit']),
        'gender': normalize_gender(features['gender']),
        'composition': normalize_composition(features.get('composition', '')),
        # Preserve other fields as-is
        **{k: v for k, v in features.items() if k not in ['garment_type', 'color', 'fit', 'gender', 'composition']}
    }
