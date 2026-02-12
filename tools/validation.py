import os
from google import genai
from google.genai import types

from logic.prompts import build_validation_prompt, build_variant_validation_prompt


def validate_generated_image(original_image_path: str, generated_image_raw_data: bytes, analysis: dict) -> tuple:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    gemini_client = genai.Client(api_key=api_key)

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
        model="gemini-2.5-flash",
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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    gemini_client = genai.Client(api_key=api_key)

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
        model="gemini-2.5-flash",
        contents=contents
    )
    result_text = response.text.strip()

    if result_text.startswith("APPROVED"):
        return True, result_text
    else:
        return False, result_text
