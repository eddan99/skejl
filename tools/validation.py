from google.genai import types

from tools.gemini_client import get_gemini_client, get_model_name
from tools.prompts import build_validation_prompt, build_variant_validation_prompt


def validate_generated_image(original_image_path: str, generated_image_raw_data: bytes, analysis: dict) -> tuple:
    gemini_client = get_gemini_client()

    with open(original_image_path, "rb") as file:
        original_image_raw_data = file.read()

    if original_image_path.endswith(".png"):
        original_image_type = "image/png"
    else:
        original_image_type = "image/jpeg"

    generated_image_type = "image/jpeg"

    color = analysis.get("color", "unknown color")
    garment_type = analysis.get("garment_type", "garment")

    validation_prompt = build_validation_prompt(color, garment_type)

    response = gemini_client.models.generate_content(
        model=get_model_name(),
        contents=[
            types.Part(inline_data=types.Blob(mime_type=original_image_type, data=original_image_raw_data)),
            types.Part(inline_data=types.Blob(mime_type=generated_image_type, data=generated_image_raw_data)),
            types.Part(text=validation_prompt)
        ]
    )
    result_text = response.text.strip()

    if result_text.startswith("APPROVED"):
        return True, result_text
    else:
        return False, result_text


def validate_generated_variant(original_image_paths: list, generated_variant_raw_data: bytes, analysis: dict, view_angle: str) -> tuple:
    gemini_client = get_gemini_client()

    original_images_data = []
    for image_path in original_image_paths:
        with open(image_path, "rb") as file:
            original_image_raw_data = file.read()

        if image_path.endswith(".png"):
            image_type = "image/png"
        else:
            image_type = "image/jpeg"

        original_images_data.append((original_image_raw_data, image_type))

    generated_image_type = "image/jpeg"

    color = analysis.get("color", "unknown color")
    garment_type = analysis.get("garment_type", "garment")

    validation_prompt = build_variant_validation_prompt(color, garment_type, view_angle)

    contents = []

    for original_data, mime_type in original_images_data:
        contents.append(types.Part(inline_data=types.Blob(mime_type=mime_type, data=original_data)))

    contents.append(types.Part(inline_data=types.Blob(mime_type=generated_image_type, data=generated_variant_raw_data)))

    contents.append(types.Part(text=validation_prompt))

    response = gemini_client.models.generate_content(
        model=get_model_name(),
        contents=contents
    )
    result_text = response.text.strip()

    if result_text.startswith("APPROVED"):
        return True, result_text
    else:
        return False, result_text
