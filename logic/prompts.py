import json


def build_image_gen_prompt(analysis: dict) -> str:
    """
    Bygger bildgenereringsprompt med förenklad clothing-sektion.
    Instruerar modellen att skapa BILD baserat på JSON-spec.
    """
    scenario = analysis.get("photography_scenario", {})

    # Förenkla clothing-sektionen — ta bort detaljerade fallback_description
    if "subject" in scenario and "clothing" in scenario["subject"]:
        clothing = scenario["subject"]["clothing"]
        # Behåll bara reference_instruction, ta bort fallback_description
        clothing["top"] = {
            "instruction": "Use the EXACT garment from the reference image. Match color, texture, fit, graphics perfectly."
        }
        clothing["bottom"] = {
            "instruction": "Use clothing from reference image or garments that naturally match the scenario and top garment."
        }

    scenario_json = json.dumps(scenario, indent=2, ensure_ascii=False)

    prompt = f"""TASK: Generate a photorealistic fashion PHOTOGRAPH.

IMPORTANT: You MUST return an IMAGE. DO NOT return text, JSON, or descriptions. ONLY generate a photograph.

CRITICAL GARMENT INSTRUCTION:
The reference image shows the EXACT garment. Copy it with 100% accuracy:
- EXACT color, shade, tone
- EXACT texture, fabric, sheen
- EXACT fit, silhouette, cut
- EXACT graphics/patterns (replace copyrighted logos with generic abstract alternatives)
- Do NOT invent or modify the garment
- No real celebrities, no real brand logos

PHOTO SPECIFICATION (JSON format):
{scenario_json}

Follow the JSON specification exactly to generate the photograph. The "clothing" section instructs you to use the reference-image."""

    return prompt


def build_validation_prompt(color: str, garment_type: str) -> str:
    """
    Bygger prompt för att validera att en genererad bild matchar originalbilden.
    """
    prompt = f"""You are an expert at comparing clothing garments.

You are given two images:
1. ORIGINAL IMAGE: Shows a {garment_type} in {color}
2. GENERATED IMAGE: A new image that should show the same garment worn by a person

Your task: Verify if the garment is EXACTLY THE SAME in both images.

Check these specific things:
- Color: Is the color exactly the same? (original color: {color})
- Graphics/patterns: If there are prints, logos or patterns - are they exactly the same?
- Fit/silhouette: Does the garment appear to have the same fit and shape?
- Texture: Does the fabric/material look the same?
- Are the image_format 4:5?


IMPORTANT:
- Respond ONLY with "APPROVED" or "REJECTED"
- On the next line: Briefly explain why (max 2 sentences)

Format:
APPROVED
The garment matches exactly: same color, graphics and fit.

OR:

REJECTED
The color is too dark/light compared to the original.
"""
    return prompt


def build_variant_prompt(view_angle: str) -> str:
    """
    Bygger prompt för att generera en variant av en bild (side eller back).
    """
    angle_description = "from the side" if view_angle == "side" else "from behind"

    prompt = f"""TASK: Generate a photorealistic fashion PHOTOGRAPH.

IMPORTANT: You MUST return an IMAGE. DO NOT return text, JSON, or descriptions. ONLY generate a photograph.

REFERENCE IMAGES provided (in order):
1. ORIGINAL GARMENT IMAGES: One or more images showing the actual garment from different angles (front, back, side)
2. GENERATED SCENE IMAGE: Shows a person wearing the garment in a specific environment (front view)

YOUR TASK: Generate THE EXACT SAME SCENE but photographed {angle_description}.
image_format = "4:5"

REQUIREMENTS:
- Use the ORIGINAL GARMENT IMAGES to see how the {angle_description} of the garment actually looks (color, texture, graphics, fit)
- Use the GENERATED SCENE IMAGE for: person (appearance, hair, age), environment, lighting, pose
- SAME person as in the generated scene
- SAME environment and lighting as in the generated scene
- SAME pose and body position as in the generated scene
- EXACT garment details {angle_description} as shown in the original garment images
- ONLY DIFFERENCE: Camera angle is now {angle_description}

CRITICAL: If original images show how the garment looks {angle_description}, replicate those exact details (prints, logos, texture, color).

Generate a photograph that looks like you walked around the person from the scene and took another shot {angle_description}."""

    return prompt


def build_variant_validation_prompt(color: str, garment_type: str, view_angle: str) -> str:
    """
    Bygger prompt för att validera en genererad variant (side/back) mot originalbilder.
    """
    angle_name = "side" if view_angle == "side" else "back"

    prompt = f"""You are an expert at comparing clothing garments.

You are given original reference images and a generated image:
- ORIGINAL IMAGES: One or more images showing a {garment_type} in {color} from different angles (may be just front, or front + back + side)
- GENERATED IMAGE ({angle_name.upper()} VIEW): A new image showing the same garment worn by a person from the {angle_name}

Your task: Verify if the generated {angle_name} view is CONSISTENT with the original images.

Check these specific things:
- Color: Is the color exactly the same? (original color: {color})
- Graphics/patterns: IF there are prints/logos, are they positioned correctly? Front prints should stay on front, back prints on back
- Fit/silhouette: Does the garment have the same fit and shape?
- Texture: Does the fabric/material look the same?
- Are the image_format 4:5?

IMPORTANT:
- Many garments have NO prints at all - this is completely normal
- IF there is a print on the front in original images, it should NOT appear on the back view (and vice versa)
- Respond ONLY with "APPROVED" or "REJECTED"
- On the next line: Briefly explain why (max 2 sentences)

Format:
APPROVED
The {angle_name} view is consistent: correct color, fit and print placement.

OR:

REJECTED
Front print incorrectly appears on the back view."""

    return prompt


DEFAULT_BRAND_IDENTITY = (
    "A modern, minimalist e-commerce brand. "
    "Clean, confident, and always doing references to breaking bad series. "
    "Descriptions are concise but evocative."
)


def build_analysis_prompt(product_metadata: dict, brand_identity: str = None) -> str:
    if brand_identity is None:
        brand_identity = DEFAULT_BRAND_IDENTITY

    metadata_json = json.dumps(product_metadata, indent=2, ensure_ascii=False)

    prompt = f"""You are a fashion product analyst and copywriter.

You are given a product image and the following metadata from the supplier:

productimage = "{product_metadata['image']}"
{metadata_json}
aspect_ratio = "4:5"

Brand identity to write in:
{brand_identity}

Analyze the image and the metadata. Return ONLY a valid JSON object — no extra text, no markdown, no explanations. Just the JSON.

The JSON must contain these where the "photography_scenario" key is instructions for the image generation model to create a photorealistic image of the {product_metadata['image']}:

{{
  "image": "the original image filename as in {metadata_json}",
  "title": "a catchy product title that would make you want to click on the product",
  "art_nr": "Keep the same as in {metadata_json}",
  "color": "Keep the same as in {metadata_json}",
  "fit": "Keep the same as in {metadata_json}",
  "composition": "Keep the same as in {metadata_json}, but convert the composition dict into a single string, e.g. 'Shell: 60% Cotton, 40% Polyester'",
  "gender": "Keep the same as in {metadata_json}",
  "garment_type": "e.g. t-shirt, jacket, sweatshirt, jeans",
  "photography_scenario": {{
    "rule": "Always select a lively, believable real-world situation. Base the entire scene (pose, background, lighting, mood, accessories) on how and where people actually wear this type of garment {product_metadata['image']} in real life. Never use a plain, neutral or static studio background.",
    "output_instruction": "Generate **only** one complete JSON object following this exact structure, keys, nesting and detail level. Adapt all content (description, pose, expression, background, lighting, atmosphere, accessories etc.) to the chosen real-life scenario and the actual garment from {product_metadata['image']} (the reference image). Never contradict or invent clothing details — strictly follow the reference image for appearance, fit, color, logos, textures.",
    "example_output_structure": {{
      "subject": {{
        "description": "A fierce athletic young woman posing dynamically on a rocky alpine trail, balancing on one leg while lifting the other high in a powerful kick pose",
        "pose_rules": "preserve natural proportions and physics, no distortions, dynamic tension in lifted leg, grounded stance on supporting leg",
        "age": "young adult mid-to-late 20s",
        "expression": "intense, fierce, teeth clenched, lips pulled back in powerful grimace/growl, eyes narrowed with determination",
        "hair": {{
          "color": "blonde with subtle highlights",
          "style": "long straight, partially tucked under hood, front sections visible and flowing slightly in breeze"
        }},
        "clothing": {{
          "reference_instruction": "Use the provided {product_metadata['image']} as a reference for the EXACT garment. Match color, texture, fit, graphics perfectly. Do NOT invent or modify the garment. Match the other clothing items to the scenario and the reference garment, but you can use different garments if needed for the scenario (e.g. shorts instead of pants)"
        }},
        "face": {{
          "preserve_original": true,
          "makeup": "minimal natural athletic look, light sheen from exertion, subtle glow on skin, no heavy makeup"
        }}
      }},
      "accessories": {{
        "headwear": {{
          "type": "headband",
          "color": "bright red",
          "details": "Arc'teryx branded text in white across front, worn across forehead holding hair back; use reference image if it shows different headwear"
        }},
        "eyewear": {{
          "type": "sport sunglasses",
          "details": "large oval frames, glossy black, dark-tinted lenses; match reference image if eyewear is visible"
        }},
        "socks": {{
          "type": "athletic ankle socks",
          "color": "white",
          "details": "mid-calf height, simple crew style; match reference if different"
        }},
        "shoes": {{
          "type": "trail running shoes",
          "brand_style": "aggressive trail model (e.g. Salomon Speedcross style)",
          "color": "black",
          "details": "chunky outsole with deep aggressive lugs, black mesh upper, protective toe cap, visible tread; prioritize reference image appearance if shoes differ"
        }},
        "backpack": {{
          "type": "technical daypack",
          "color": "black",
          "details": "slim fit, chest strap, hip belt, worn tightly; match reference image if backpack is shown differently"
        }}
      }},
      "prop": null,
      "photography": {{
        "camera_style": "professional outdoor adventure photography",
        "angle": "slightly low to eye-level, dynamic perspective emphasizing power and height of leg lift",
        "shot_type": "full-body composition with environmental context, subject centered but trail leading into frame",
        "aspect_ratio": "Aspect ratio is always 4:5, vertical orientation",
        "texture": "ultra-sharp focus, high resolution, natural golden-hour lighting, photorealistic details, rich textures on fabric (guided by reference image), rock, trees, skin with visible muscle definition and light sheen, cinematic depth"
      }},
      "background": {{
        "setting": "rugged alpine hiking trail in the Italian Dolomites",
        "terrain": "loose white-gray rocky scree and stone path underfoot",
        "elements": [
          "steep jagged limestone rock faces and peaks on left",
          "dense European larch trees with golden autumn needles on right and background",
          "distant mountain ridges",
          "clear sky with warm golden haze"
        ],
        "atmosphere": "empowering, fierce, high-energy outdoor adventure, raw mountain wilderness",
        "lighting": "warm orange-pink golden-hour sunset from right side, creating strong side-lighting, rim light on subject (hair, hood, shoulders, raised leg), long soft shadows on ground, volumetric glow through trees"
      }}
    }}
  }},
  "description": "<a complete product description (3-5 sentences) written in the tone of the brand identity above. Use the image and metadata to be specific about details like color, material, fit and style>"
}}
"""
    return prompt
