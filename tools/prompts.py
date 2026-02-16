import json
from config.settings import settings


_STYLE_DIRECTIVES = {
    "urban_outdoor":     "LOCATION: Urban outdoor street environment — buildings, pavement, city. NOT a studio.",
    "studio_minimal":    "LOCATION: Clean indoor studio with plain backdrop. NO outdoor scenes, NO streets, NO buildings.",
    "lifestyle_indoor":  "LOCATION: Casual indoor space — living room, café, home. NOT a studio, NOT outdoor.",
    "casual_lifestyle":  "LOCATION: Relaxed everyday outdoor or indoor setting.",
    "streetwear":        "LOCATION: Urban street, skatepark or city environment.",
    "lifestyle_outdoor": "LOCATION: Outdoor lifestyle setting — park, nature, open space.",
}

_LIGHTING_DIRECTIVES = {
    "golden_hour": "LIGHTING: Warm orange-pink golden hour sunset. Strong warm glow, long shadows, rim light on subject.",
    "studio":      "LIGHTING: Controlled studio lighting — even, clean, no harsh shadows.",
    "natural":     "LIGHTING: Soft natural daylight. Balanced exposure, gentle shadows.",
    "overcast":    "LIGHTING: Soft diffused overcast sky. Flat, even lighting, minimal shadows.",
    "dramatic":    "LIGHTING: High-contrast dramatic lighting. Strong shadows, bright highlights, dark areas.",
}

_BACKGROUND_DIRECTIVES = {
    "studio_white":   "BACKGROUND: Pure white seamless studio backdrop. Nothing else behind the subject.",
    "studio_grey":    "BACKGROUND: Grey studio backdrop. Clean and plain.",
    "neutral_wall":   "BACKGROUND: Plain neutral wall. No street, no outdoor, no buildings.",
    "urban_street":   "BACKGROUND: Urban street with buildings, road, and city infrastructure.",
    "graffiti_wall":  "BACKGROUND: Colorful graffiti-covered brick wall.",
    "nature_outdoor": "BACKGROUND: Natural outdoor environment — greenery, trees, grass.",
    "park":           "BACKGROUND: Public park with grass, trees, and open space.",
    "busy_pattern":   "BACKGROUND: Visually busy patterned background.",
}

_POSE_DIRECTIVES = {
    "walking": "POSE: Natural walking, mid-stride, one foot forward.",
    "standing": "POSE: Relaxed upright standing. Both feet on ground.",
    "action":   "POSE: Dynamic action pose with movement and energy.",
    "sitting":  "POSE: Seated, relaxed position.",
    "dynamic":  "POSE: Dynamic pose with movement.",
    "casual":   "POSE: Casual, relaxed, natural stance.",
}

_ANGLE_DIRECTIVES = {
    "front": "CAMERA ANGLE: Straight-on front view.",
    "side":  "CAMERA ANGLE: Side profile.",
    "3/4":   "CAMERA ANGLE: Three-quarter angle.",
    "back":  "CAMERA ANGLE: Rear view from behind.",
}


_GENDER_DIRECTIVES = {
    "female": "SUBJECT: A woman. NOT a man.",
    "male":   "SUBJECT: A man. NOT a woman.",
    "unisex": "SUBJECT: A person (any gender).",
}


def _extract_hard_constraints(analysis: dict) -> str:
    """Extract final_image_settings from result and build explicit constraint block."""
    try:
        s = analysis["ml_metadata"]["debate_log"]["moderator_decision"]["final_image_settings"]
    except (KeyError, TypeError):
        return ""

    lines = []
    if d := _GENDER_DIRECTIVES.get(analysis.get("gender", "")):
        lines.append(d)
    if d := _STYLE_DIRECTIVES.get(s.get("style", "")):
        lines.append(d)
    if d := _LIGHTING_DIRECTIVES.get(s.get("lighting", "")):
        lines.append(d)
    if d := _BACKGROUND_DIRECTIVES.get(s.get("background", "")):
        lines.append(d)
    if d := _POSE_DIRECTIVES.get(s.get("pose", "")):
        lines.append(d)
    if d := _ANGLE_DIRECTIVES.get(s.get("angle", "")):
        lines.append(d)

    if not lines:
        return ""

    return "MANDATORY SCENE CONSTRAINTS — follow these exactly, they override everything else:\n" + "\n".join(
        f"{i+1}. {line}" for i, line in enumerate(lines)
    )


def build_image_gen_prompt(analysis: dict) -> str:
    scenario = analysis.get("photography_scenario", {})

    if "subject" in scenario.get("example_output_structure", {}):
        clothing = scenario["example_output_structure"]["subject"].get("clothing", {})
        clothing["top"] = {
            "instruction": "Use the EXACT garment from the reference image. Match color, texture, fit, graphics perfectly."
        }
        clothing["bottom"] = {
            "instruction": "Use clothing from reference image or garments that naturally match the scenario and top garment."
        }

    hard_constraints = _extract_hard_constraints(analysis)
    scenario_json = json.dumps(scenario, indent=2, ensure_ascii=False)

    prompt = f"""TASK: Generate a photorealistic fashion PHOTOGRAPH.

IMPORTANT: You MUST return an IMAGE. DO NOT return text, JSON, or descriptions. ONLY generate a photograph.

{hard_constraints}

CRITICAL GARMENT INSTRUCTION:
The reference image shows the EXACT garment. Copy it with 100% accuracy:
- EXACT color, shade, tone
- EXACT texture, fabric, sheen
- EXACT fit, silhouette, cut
- EXACT graphics/patterns (replace copyrighted logos with generic abstract alternatives)
- Do NOT invent or modify the garment
- No real celebrities, no real brand logos

PEOPLE:
- The scene must contain ONLY the main subject (the person wearing the garment)
- Do NOT include any other people, bystanders or figures anywhere in the image

DETAILED PHOTO SPECIFICATION (JSON):
{scenario_json}

The mandatory constraints above take priority. The JSON provides additional detail for subject, styling and composition."""

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


def build_variant_prompt(view_angle: str, num_source_images: int = 1) -> str:
    """
    Bygger prompt för att generera en variant av en bild (side eller back).
    """
    angle_description = "from the side" if view_angle == "side" else "from behind"

    if num_source_images == 1:
        back_print_note = "Only ONE reference image was provided (front view only). Assume there is NO print, graphic or logo on the back or sides of the garment unless it is clearly visible wrapping around from the front."
    else:
        back_print_note = "Use the original garment images to determine if there are prints or graphics on the back or sides."

    prompt = f"""TASK: Generate a photorealistic fashion PHOTOGRAPH.

IMPORTANT: You MUST return an IMAGE. DO NOT return text, JSON, or descriptions. ONLY generate a photograph.

REFERENCE IMAGES provided (in order):
1. ORIGINAL GARMENT IMAGES: One or more images showing the actual garment from different angles (front, back, side)
2. GENERATED SCENE IMAGE: Shows a person wearing the garment in a specific environment (front view)

YOUR TASK: Generate THE EXACT SAME SCENE but photographed {angle_description}.
image_format = "4:5"

REQUIREMENTS:
- SAME person, environment, lighting and pose as in the generated scene
- ONLY DIFFERENCE: Camera angle is now {angle_description}
- Match garment color, texture and fit exactly

GARMENT BACK/SIDE:
- {back_print_note}

PEOPLE:
- The scene must contain ONLY the main subject — no other people anywhere in the image.

Generate a photograph that looks like you walked around the person and took another shot {angle_description}."""

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


def build_analysis_prompt(product_metadata: dict, brand_identity: str = None) -> str:
    if brand_identity is None:
        brand_identity = settings.DEFAULT_BRAND_IDENTITY

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
  "title": "a short, catchy product name (2-3 words max) - examples: 'Chemistry Hoodie', 'Urban Jacket', 'Midnight Tee' - DO NOT include brand names or full descriptions",
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
  "description": "<a complete product description (3-5 sentences) written in the tone of the brand identity above. Use the image and metadata to be specific about details like color, material, fit and style. DO NOT mention brand names or the filename - write in a general, engaging tone>"
}}
"""
    return prompt


def build_feature_extraction_prompt(product_metadata: dict) -> str:
    """
    Bygger prompt för att extrahera produkt-features från bild (UTAN photography_scenario).
    Används i ML-driven flow där scenario genereras senare.
    """
    metadata_json = json.dumps(product_metadata, indent=2, ensure_ascii=False)

    prompt = f"""You are a fashion product analyst.

You are given a product image and metadata from the supplier:

{metadata_json}

Analyze the image and extract product features. Return ONLY a valid JSON object — no extra text, no markdown, no explanations.

The JSON must contain:

{{
  "image": "{product_metadata['image']}",
  "art_nr": "{product_metadata.get('art_nr', '')}",
  "color": "exact color from metadata: {product_metadata.get('color', '')}",
  "fit": "exact fit from metadata: {product_metadata.get('fit', '')}",
  "composition": "convert composition dict to string, e.g. 'Shell: 60% Cotton, 40% Polyester'",
  "gender": "{product_metadata.get('gender', '')}",
  "garment_type": "identify garment type from image (e.g. hoodie, t-shirt, jacket, jeans, zip-up hoodie)",
  "title": "a short, catchy product name (2-3 words max) - examples: 'Chemistry Hoodie', 'Urban Jacket', 'Midnight Tee' - DO NOT include brand names or full descriptions"
}}

IMPORTANT:
- Do NOT generate a photography_scenario or description. Only extract the features above.
- Do NOT use the filename or any brand names in the title
- Title should be 2-3 words maximum, like a product name
"""
    return prompt


def build_description_prompt(
    product_features: dict,
    photography_scenario: dict,
    brand_identity: str = None
) -> str:
    """
    Bygger prompt för att generera produktbeskrivning baserat på
    features och final photography scenario.
    """
    if brand_identity is None:
        brand_identity = settings.DEFAULT_BRAND_IDENTITY

    features_json = json.dumps(product_features, indent=2, ensure_ascii=False)
    scenario_summary = f"{photography_scenario.get('background', {}).get('setting', 'dynamic environment')}"

    prompt = f"""You are a fashion product copywriter.

Product features:
{features_json}

Photography scenario:
The product will be photographed in: {scenario_summary}

Brand identity:
{brand_identity}

Write a complete product description (3-5 sentences) in the tone of the brand identity.
Be specific about the product's color, material, fit, and style.
Match the description to the photography scenario's atmosphere.

IMPORTANT:
- DO NOT mention any brand names or the filename in the description
- Write in a general, engaging tone without referencing specific brands
- Focus on the product itself and its features

Return ONLY the description text. No JSON, no markdown, no extra formatting.
"""
    return prompt


def build_optimizer_prompt(ml_prediction: dict) -> str:
    """
    Bygger prompt för Optimizer Agent i multi-agent debate.
    Advocates för ML-predicted settings baserat på data.
    """
    settings = ml_prediction['image_settings']
    conversion = ml_prediction['predicted_conversion_rate']
    confidence = ml_prediction.get('confidence', 0)

    prompt = f"""You are a data-driven optimizer for e-commerce product photography.

Your role: Advocate for proven, high-converting image settings based on ML analysis.

ML PREDICTION:
{json.dumps(settings, indent=2)}

EXPECTED CONVERSION RATE: {conversion*100:.2f}%
MODEL CONFIDENCE: {confidence*100:.1f}%

REASONING:
{ml_prediction.get('reasoning', 'Based on historical performance data')}

Make your case for following this data-driven approach. Be specific about:
1. Why these settings are predicted to perform well
2. What the data shows about similar products
3. The business value of optimizing for conversion

CRITICAL: Keep your argument VERY concise - maximum 100 words (about 5-6 sentences). Focus only on the most important facts and performance metrics. Be direct and specific.
"""
    return prompt


def build_creative_prompt(
    ml_prediction: dict,
    product_features: dict,
    brand_identity: str
) -> str:
    """
    Bygger prompt för Creative Agent i multi-agent debate.
    Proposes creative alternatives för brand differentiation.
    """
    settings = ml_prediction['image_settings']

    prompt = f"""You are a creative strategist for e-commerce product photography.

Your role: Balance data-driven decisions with creative brand differentiation.

BRAND IDENTITY:
{brand_identity}

PRODUCT:
{json.dumps(product_features, indent=2)}

ML RECOMMENDATION:
{json.dumps(settings, indent=2)}

While data shows these settings perform well, consider:
1. Does this align with our brand identity?
2. Are we differentiating from competitors or following generic trends?
3. Could creative alternatives create stronger brand recall?
4. What about visual storytelling and emotional connection?

Provide your perspective:
- If ML settings align with brand, acknowledge and suggest minor enhancements
- If they feel generic, propose creative alternatives that still consider performance
- Balance creativity with business goals

CRITICAL: Keep your argument VERY concise - maximum 100 words (about 5-6 sentences). Be constructive and specific.
"""
    return prompt


def build_moderator_prompt(
    optimizer_argument: str,
    creative_argument: str,
    ml_prediction: dict,
    product_features: dict
) -> str:
    """
    Bygger prompt för Moderator Agent i multi-agent debate.
    Synthesizes final decision från både perspectives.
    """
    ml_settings = ml_prediction['image_settings']

    prompt = f"""You are a moderator synthesizing the best decision from two perspectives.

PRODUCT FEATURES:
{json.dumps(product_features, indent=2)}

ML PREDICTION (Data-Driven):
{json.dumps(ml_settings, indent=2)}
Predicted conversion: {ml_prediction['predicted_conversion_rate']*100:.2f}%

OPTIMIZER'S ARGUMENT (Data-Driven):
{optimizer_argument}

CREATIVE'S ARGUMENT (Brand Differentiation):
{creative_argument}

Your task: Build consensus and decide final image settings.

Consider:
1. Both perspectives have merit - find the balanced approach
2. Can we keep high-performing settings while adding creative touches?
3. Which settings are most critical for conversion vs brand differentiation?

VALID VALUES — you MUST only use these exact strings:
- style: "urban_outdoor", "studio_minimal", "lifestyle_indoor", "casual_lifestyle", "streetwear", "lifestyle_outdoor"
- lighting: "golden_hour", "studio", "natural", "overcast", "dramatic"
- background: "studio_white", "studio_grey", "neutral_wall", "urban_street", "graffiti_wall", "nature_outdoor", "park", "busy_pattern"
- pose: "walking", "standing", "action", "sitting", "dynamic", "casual"
- expression: "confident", "serious", "smiling", "neutral", "focused"
- angle: "front", "side", "3/4", "back"

Respond with JSON in this exact format:
{{
  "final_image_settings": {{
    "style": "chosen_style",
    "lighting": "chosen_lighting",
    "background": "chosen_background",
    "pose": "chosen_pose",
    "expression": "chosen_expression",
    "angle": "chosen_angle"
  }},
  "reasoning": "2-3 sentence explanation of your synthesis",
  "consensus_type": "full_agreement" | "hybrid_approach" | "creative_override"
}}

CRITICAL: Respond with ONLY valid JSON. No markdown code fences, no extra text. Only use the exact valid values listed above.
"""
    return prompt


def build_refinement_prompt(scenario: dict, feedback: str) -> str:
    """
    Sends the current photography_scenario + free-text user feedback to Gemini.
    Asks Gemini to return an updated scenario JSON matching the same schema.
    """
    scenario_json = json.dumps(scenario, indent=2, ensure_ascii=False)

    prompt = f"""You are a photography director refining a product shoot scenario based on client feedback.

CURRENT SCENARIO:
{scenario_json}

CLIENT FEEDBACK:
{feedback}

Your task: Update the scenario JSON to reflect the feedback. Keep all unchanged fields identical.

VALID VALUES — only use these exact strings:
- style: "urban_outdoor", "studio_minimal", "lifestyle_indoor", "casual_lifestyle", "streetwear", "lifestyle_outdoor"
- lighting: "golden_hour", "studio", "natural", "overcast", "dramatic"
- background: "studio_white", "studio_grey", "neutral_wall", "urban_street", "graffiti_wall", "nature_outdoor", "park", "busy_pattern"
- pose: "walking", "standing", "action", "sitting", "dynamic", "casual"
- expression: "confident", "serious", "smiling", "neutral", "focused"
- angle: "front", "side", "3/4", "back"

Return the complete updated scenario as JSON. No markdown code fences, no extra text — only the JSON object.
"""
    return prompt
