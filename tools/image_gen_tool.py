from google.genai import types

from tools.gemini_client import get_gemini_client
from tools.image_utils import mime_type, extract_response_image
from tools.prompts import build_image_gen_prompt, build_variant_prompt


def generate_product_image(reference_image_path: str, analysis: dict) -> tuple:
    nano_banana_client = get_gemini_client()

    decision_log = []
    with open(reference_image_path, "rb") as file:
        original_image_raw_data = file.read()

    prompt_text = build_image_gen_prompt(analysis)
    decision_log.append("Sending original image and prompt to nano-banana-pro for generation")

    response = nano_banana_client.models.generate_content(
        model="nano-banana-pro-preview",
        contents=[
            types.Part(inline_data=types.Blob(mime_type=mime_type(reference_image_path), data=original_image_raw_data)),
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

    image_bytes = extract_response_image(response)
    if image_bytes:
        decision_log.append("Result: Image generated successfully")
        return image_bytes, decision_log

    decision_log.append("Error: No image in response")
    decision_log.append("Decision: Skipping this product.")
    return None, decision_log


def generate_variant(approved_image_raw_data: bytes, view_angle: str, original_image_paths: list = None) -> tuple:
    nano_banana_client = get_gemini_client()

    decision_log = []

    num_source_images = len(original_image_paths) if original_image_paths else 1
    prompt_text = build_variant_prompt(view_angle, num_source_images)

    if original_image_paths and len(original_image_paths) > 1:
        decision_log.append(f"Decision: Generating {view_angle}-variant with {len(original_image_paths)} original images as reference")
    else:
        decision_log.append(f"Decision: Generating {view_angle}-variant based on approved image")

    contents = []

    if original_image_paths:
        for img_path in original_image_paths:
            with open(img_path, "rb") as file:
                img_data = file.read()
            contents.append(types.Part(inline_data=types.Blob(mime_type=mime_type(img_path), data=img_data)))

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

    image_bytes = extract_response_image(response)
    if image_bytes:
        decision_log.append(f"Result: {view_angle.capitalize()}-variant generated successfully")
        return image_bytes, decision_log

    decision_log.append("Error: No image in response")
    decision_log.append(f"Decision: Skipping {view_angle}-variant.")
    return None, decision_log
