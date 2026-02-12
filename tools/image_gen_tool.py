import os
from google import genai
from google.genai import types

from logic.prompts import build_image_gen_prompt, build_variant_prompt


def generate_product_image(reference_image_path: str, analysis: dict) -> tuple:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing in .env")

    nano_banana_client = genai.Client(api_key=api_key)

    decision_log = []
    with open(reference_image_path, "rb") as file:
        original_image_raw_data = file.read()

    if reference_image_path.endswith(".png"):
        image_type = "image/png"
    else:
        image_type = "image/jpeg"

    prompt_text = build_image_gen_prompt(analysis)
    decision_log.append("Sending original image and prompt to nano-banana-pro for generation")
    
    response = nano_banana_client.models.generate_content(
        model="nano-banana-pro-preview",
        contents=[
            types.Part(inline_data=types.Blob(mime_type=image_type, data=original_image_raw_data)),
            types.Part(text=prompt_text)
        ],
        config=types.GenerateContentConfig(
            response_modalities=["image"]
        )
    )

    if not response.parts:
        feedback = getattr(response, "prompt_feedback", None)
        reason = str(feedback) if feedback else "unknown reason"
        decision_log.append(f"Blocked: {reason}")
        decision_log.append("Decision: Skipping image generation for this product.")
        return None, decision_log

    for part in response.parts:
        if hasattr(part, "inline_data") and part.inline_data and hasattr(part.inline_data, "data"):
            decision_log.append("Result: Image generated successfully")
            return part.inline_data.data, decision_log

    decision_log.append("Error: No image in response")
    decision_log.append("Decision: Skipping this product.")
    return None, decision_log


def generate_variant(approved_image_raw_data: bytes, view_angle: str, original_image_paths: list = None) -> tuple:

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing in .env")

    nano_banana_client = genai.Client(api_key=api_key)

    decision_log = []

    prompt_text = build_variant_prompt(view_angle)

    if original_image_paths and len(original_image_paths) > 1:
        decision_log.append(f"Decision: Generating {view_angle}-variant with {len(original_image_paths)} original images as reference")
    else:
        decision_log.append(f"Decision: Generating {view_angle}-variant based on approved image")

    contents = []

    if original_image_paths:
        for img_path in original_image_paths:
            with open(img_path, "rb") as file:
                img_data = file.read()
                
            if img_path.endswith(".png"):
                img_type = "image/png"
            else:
                img_type = "image/jpeg"

            contents.append(types.Part(inline_data=types.Blob(mime_type=img_type, data=img_data)))

    contents.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=approved_image_raw_data)))

    contents.append(types.Part(text=prompt_text))

    response = nano_banana_client.models.generate_content(
        model="nano-banana-pro-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["image"]
        )
    )

    if not response.parts:
        feedback = getattr(response, "prompt_feedback", None)
        reason = str(feedback) if feedback else "unknown reason"
        decision_log.append(f"Blocked: {reason}")
        decision_log.append(f"Decision: Skipping {view_angle}-variant.")
        return None, decision_log

    for part in response.parts:
        if hasattr(part, "inline_data") and part.inline_data and hasattr(part.inline_data, "data"):
            decision_log.append(f"Result: {view_angle.capitalize()}-variant generated successfully")
            return part.inline_data.data, decision_log

    decision_log.append("Error: No image in response")
    decision_log.append(f"Decision: Skipping {view_angle}-variant.")
    return None, decision_log
