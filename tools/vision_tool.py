import json
from google.genai import types

from config.paths import PRODUCTS_JSON
from tools.gemini_client import get_gemini_client, get_model_name
from tools.json_utils import parse_gemini_response
from tools.prompts import (
    build_analysis_prompt,
    build_feature_extraction_prompt,
    build_description_prompt
)
from tools.taxonomy import normalize_product_features


def load_product_data(image_path: str) -> dict:
    from pathlib import Path
    filename_without_extension = Path(image_path).stem

    with open(PRODUCTS_JSON, "r", encoding="utf-8") as file:
        all_products = json.load(file)

    for product in all_products:
        product_filename = Path(product["image"]).stem

        if product_filename == filename_without_extension:
            return product

    raise ValueError(f"No product found for image: {image_path}")


def analyze_product_image(image_path: str, brand_identity: str = None) -> dict:
    gemini_client = get_gemini_client()

    with open(image_path, "rb") as file:
        image_raw_data = file.read()

    if image_path.endswith(".png"):
        image_type = "image/png"
    else:
        image_type = "image/jpeg"

    product_metadata = load_product_data(image_path)

    prompt_text = build_analysis_prompt(product_metadata, brand_identity)

    response = gemini_client.models.generate_content(
        model=get_model_name(),
        contents=[
            types.Part(inline_data=types.Blob(mime_type=image_type, data=image_raw_data)),
            types.Part(text=prompt_text)
        ]
    )
    return parse_gemini_response(response.text)


def extract_product_features(image_path: str) -> dict:
    gemini_client = get_gemini_client()

    with open(image_path, "rb") as file:
        image_raw_data = file.read()

    if image_path.endswith(".png"):
        image_type = "image/png"
    else:
        image_type = "image/jpeg"

    product_metadata = load_product_data(image_path)

    prompt_text = build_feature_extraction_prompt(product_metadata)

    response = gemini_client.models.generate_content(
        model=get_model_name(),
        contents=[
            types.Part(inline_data=types.Blob(mime_type=image_type, data=image_raw_data)),
            types.Part(text=prompt_text)
        ]
    )

    features = parse_gemini_response(response.text)
    try:
        features = normalize_product_features(features)
    except ValueError as e:
        print(f"Warning: Normalization failed: {e}")

    return features

def generate_product_description(
    product_features: dict,
    photography_scenario: dict,
    brand_identity: str = None
) -> str:
    gemini_client = get_gemini_client()

    prompt_text = build_description_prompt(
        product_features,
        photography_scenario,
        brand_identity
    )

    response = gemini_client.models.generate_content(
        model=get_model_name(),
        contents=prompt_text
    )

    return response.text.strip()
