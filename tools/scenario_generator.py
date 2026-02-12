"""
Photography Scenario Generator

Converts final image_settings from multi-agent debate into detailed
photography_scenario JSON for image generation.

Takes simple settings (style, lighting, background, pose, expression, angle)
and generates comprehensive scenario matching the existing format.
"""

import json
from typing import Dict


# Mapping templates for different combinations
STYLE_DESCRIPTIONS = {
    "urban_outdoor": {
        "setting": "urban outdoor environment with street photography aesthetic",
        "atmosphere": "energetic, authentic, street-style",
        "camera_style": "professional street photography"
    },
    "studio_minimal": {
        "setting": "clean minimalist studio",
        "atmosphere": "modern, sophisticated, clean",
        "camera_style": "professional studio portrait photography"
    },
    "lifestyle_indoor": {
        "setting": "casual indoor lifestyle environment",
        "atmosphere": "relaxed, authentic, lifestyle-focused",
        "camera_style": "professional lifestyle photography"
    },
    "skate_urban": {
        "setting": "urban skatepark environment",
        "atmosphere": "dynamic, youthful, action-oriented",
        "camera_style": "professional action sports photography"
    },
    "action_sports": {
        "setting": "outdoor action sports environment",
        "atmosphere": "energetic, powerful, athletic",
        "camera_style": "professional sports photography"
    },
    "artistic": {
        "setting": "artistic conceptual environment",
        "atmosphere": "creative, unique, conceptual",
        "camera_style": "fine art fashion photography"
    },
    "street_style": {
        "setting": "urban street fashion environment",
        "atmosphere": "stylish, contemporary, fashion-forward",
        "camera_style": "professional street fashion photography"
    }
}

LIGHTING_DESCRIPTIONS = {
    "golden_hour": "warm orange-pink golden hour lighting from the side, creating soft rim light and long shadows",
    "studio": "controlled studio lighting with key light and fill, even illumination",
    "natural": "natural daylight with soft shadows, balanced exposure",
    "overcast": "soft diffused overcast lighting, minimal shadows, even tones",
    "dramatic": "high-contrast dramatic lighting with strong shadows and highlights",
    "soft_diffused": "soft diffused lighting from multiple directions, gentle shadows"
}

BACKGROUND_TEMPLATES = {
    "graffiti_wall": "colorful graffiti-covered brick wall with urban street art",
    "studio_white": "clean white studio backdrop, seamless and minimal",
    "urban_street": "authentic urban street with buildings and infrastructure",
    "skatepark": "concrete skatepark with ramps and urban architecture",
    "nature": "natural outdoor environment with greenery and organic elements",
    "indoor_minimal": "minimal indoor space with clean lines and simple elements",
    "brick_wall": "exposed brick wall texture with industrial character"
}

POSE_TEMPLATES = {
    "walking": "natural walking pose, dynamic movement",
    "standing": "standing pose with natural stance",
    "action": "dynamic action pose with energy and movement",
    "sitting": "seated pose, relaxed and natural",
    "dynamic": "dynamic pose with movement and energy",
    "casual": "casual relaxed pose, natural and authentic"
}

EXPRESSION_TEMPLATES = {
    "confident": "confident expression with direct eye contact",
    "serious": "serious focused expression",
    "smiling": "genuine smiling expression",
    "neutral": "neutral calm expression",
    "focused": "focused intense expression"
}

ANGLE_TEMPLATES = {
    "front": "eye-level front angle, direct composition",
    "side": "side angle showing profile and garment details",
    "3/4": "three-quarter angle for dynamic perspective",
    "back": "back angle showing rear details"
}


def generate_photography_scenario(
    image_settings: Dict[str, str],
    product_features: Dict[str, str]
) -> Dict:
    """
    Generate detailed photography scenario from image settings.

    Args:
        image_settings: Dict with style, lighting, background, pose, expression, angle
        product_features: Dict with garment_type, color, fit, gender

    Returns:
        Detailed photography_scenario dict
    """
    style = image_settings['style']
    lighting = image_settings['lighting']
    background = image_settings['background']
    pose = image_settings['pose']
    expression = image_settings['expression']
    angle = image_settings['angle']

    # Get style description
    style_desc = STYLE_DESCRIPTIONS.get(style, {
        "setting": f"{style} environment",
        "atmosphere": "authentic, engaging",
        "camera_style": "professional photography"
    })

    # Build subject description
    garment_type = product_features.get('garment_type', 'garment')
    color = product_features.get('color', 'colored')
    fit = product_features.get('fit', 'regular fit')
    gender = product_features.get('gender', 'person')

    # Gender mapping for description
    gender_map = {
        'male': 'man',
        'female': 'woman',
        'unisex': 'person'
    }

    subject_gender = gender_map.get(gender, 'person')

    pose_desc = POSE_TEMPLATES.get(pose, f"{pose} pose")
    expression_desc = EXPRESSION_TEMPLATES.get(expression, f"{expression} expression")

    subject_description = (
        f"A {subject_gender} in a {color} {fit} {garment_type}, "
        f"{pose_desc} with {expression_desc}, "
        f"in a {style_desc['setting']}"
    )

    # Build scenario
    scenario = {
        "rule": (
            "Always select a lively, believable real-world situation. "
            "Base the entire scene (pose, background, lighting, mood, accessories) "
            "on how and where people actually wear this type of garment in real life. "
            "Never use a plain, neutral or static studio background unless style is 'studio_minimal'."
        ),
        "output_instruction": (
            "Generate **only** one complete JSON object following this exact structure, "
            "keys, nesting and detail level. Adapt all content (description, pose, expression, "
            "background, lighting, atmosphere, accessories etc.) to the chosen real-life scenario "
            "and the actual garment from the reference image. Never contradict or invent clothing "
            "details — strictly follow the reference image for appearance, fit, color, logos, textures."
        ),
        "example_output_structure": {
            "subject": {
                "description": subject_description,
                "pose_rules": f"{pose_desc}, natural proportions and physics, no distortions",
                "age": "young adult mid-to-late 20s",
                "expression": expression_desc,
                "hair": {
                    "color": "natural color appropriate for subject",
                    "style": "natural style appropriate for scenario"
                },
                "clothing": {
                    "reference_instruction": (
                        "Use the provided reference image for the EXACT garment. "
                        "Match color, texture, fit, graphics perfectly. Do NOT invent or modify the garment. "
                        "Match the other clothing items to the scenario and the reference garment."
                    )
                },
                "face": {
                    "preserve_original": True,
                    "makeup": "natural look appropriate for scenario"
                }
            },
            "accessories": {
                "instruction": "Add appropriate accessories for the scenario and style"
            },
            "prop": None,
            "photography": {
                "camera_style": style_desc['camera_style'],
                "angle": ANGLE_TEMPLATES.get(angle, f"{angle} angle"),
                "shot_type": "full-body composition with environmental context",
                "aspect_ratio": "Aspect ratio is always 4:5, vertical orientation",
                "texture": "ultra-sharp focus, high resolution, photorealistic details, rich textures, cinematic depth"
            },
            "background": {
                "setting": style_desc['setting'],
                "terrain": BACKGROUND_TEMPLATES.get(background, f"{background} background"),
                "elements": [
                    f"Background elements matching {background} environment",
                    "Environmental details supporting the scenario",
                    "Contextual elements enhancing the scene"
                ],
                "atmosphere": style_desc['atmosphere'],
                "lighting": LIGHTING_DESCRIPTIONS.get(lighting, f"{lighting} lighting")
            }
        }
    }

    return scenario


if __name__ == "__main__":
    # Test scenario generation
    print("Testing scenario generator...\n")

    test_settings = {
        "style": "urban_outdoor",
        "lighting": "golden_hour",
        "background": "graffiti_wall",
        "pose": "walking",
        "expression": "confident",
        "angle": "front"
    }

    test_features = {
        "garment_type": "hoodie",
        "color": "dark",
        "fit": "loose",
        "gender": "male"
    }

    scenario = generate_photography_scenario(test_settings, test_features)

    print("Generated Photography Scenario:")
    print(json.dumps(scenario, indent=2))
