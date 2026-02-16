import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.genai import types

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import chainlit as cl

from config.paths import INPUT_DIR, OUTPUT_DIR, ensure_directories
from config.settings import settings
from tools.vision_tool import extract_product_features, analyze_product_image
from tools.image_gen_tool import generate_product_image, generate_variant
from tools.validation import validate_generated_image, validate_generated_variant
from tools.shopify_tool import upload_product_to_shopify
from tools.feedback_loop import record_published_product, get_dataset_size
from tools.image_utils import crop_to_4_5_ratio
from tools.ml.ml_predictor import predict_image_settings
from tools.scenario_generator import generate_photography_scenario
from tools.gemini_client import get_gemini_client, get_model_name
from tools.prompts import build_optimizer_prompt, build_creative_prompt, build_moderator_prompt, build_description_prompt
from tools.json_utils import parse_gemini_response
from tools.taxonomy import validate_image_settings


async def _notify(on_step, name: str, msg: str):
    """Call on_step, supporting both sync and async callbacks."""
    if on_step is None:
        return
    if asyncio.iscoroutinefunction(on_step):
        await on_step(name, msg)
    else:
        on_step(name, msg)


def _find_all_product_images(base_image_path: Path) -> list:
    stem = base_image_path.stem
    parent = base_image_path.parent
    ext = base_image_path.suffix
    found = [str(base_image_path)]
    for variant in ["_back", "_side"]:
        p = parent / f"{stem}{variant}{ext}"
        if p.exists():
            found.append(str(p))
    return found


async def _stream_agent(client, prompt: str, label: str) -> str:
    """Stream a single Gemini call token-by-token into a live Chainlit message."""
    msg = cl.Message(content=f"**{label}**\n\n")
    await msg.send()
    full_text = ""
    async for chunk in await client.aio.models.generate_content_stream(model=get_model_name(), contents=prompt):
        if chunk.text:
            full_text += chunk.text
            await msg.stream_token(chunk.text)
    await msg.update()
    return full_text.strip()


async def _run_debate_streaming(ml_prediction: dict, features: dict) -> dict:
    """Streams the 3-agent debate live into the chat. Returns same structure as multi_agent_debate."""
    client = get_gemini_client()
    ml_settings = ml_prediction['image_settings']

    optimizer_arg = await _stream_agent(client, build_optimizer_prompt(ml_prediction), "Optimizer — analyzing conversion data...")
    await asyncio.sleep(settings.RATE_LIMIT_DELAY)
    creative_arg = await _stream_agent(client, build_creative_prompt(ml_prediction, features, settings.DEFAULT_BRAND_IDENTITY), "Creative — considering brand alignment...")
    await asyncio.sleep(settings.RATE_LIMIT_DELAY)
    moderator_raw = await _stream_agent(client, build_moderator_prompt(optimizer_arg, creative_arg, ml_prediction, features), "Moderator — synthesizing consensus...")

    consensus = parse_gemini_response(moderator_raw)
    fallback = {"final_image_settings": ml_settings, "reasoning": "Fallback to ML prediction.", "consensus_type": "fallback_to_ml"}
    if "error" in consensus:
        consensus = fallback
    else:
        try:
            validate_image_settings(consensus["final_image_settings"])
        except ValueError:
            consensus = fallback

    return {
        "final_image_settings": consensus["final_image_settings"],
        "reasoning": consensus["reasoning"],
        "consensus_type": consensus.get("consensus_type", "unknown"),
        "debate_log": {"optimizer_argument": optimizer_arg, "creative_argument": creative_arg, "moderator_decision": consensus}
    }


async def _generate_and_validate_variants(
    final_image_bytes: bytes,
    image_path: Path,
    result: dict,
    on_step
) -> dict:
    """Generate side and back variants and return a dict of {angle: path}."""
    original_images = _find_all_product_images(image_path)
    variant_paths = {}

    for variant_angle in ["side", "back"]:
        await _notify(on_step, "variants", f"Generating {variant_angle}-view variant...")

        final_variant_bytes = None

        for attempt in range(1, settings.MAX_VARIANT_ATTEMPTS + 1):
            await asyncio.sleep(settings.RATE_LIMIT_DELAY)
            try:
                variant_bytes, _ = await asyncio.to_thread(
                    generate_variant, final_image_bytes, variant_angle, original_images
                )
            except Exception as e:
                await _notify(on_step, "variants", f"API error on attempt {attempt}: {e}")
                if attempt < settings.MAX_VARIANT_ATTEMPTS:
                    await asyncio.sleep(settings.RATE_LIMIT_DELAY)
                continue

            if not variant_bytes:
                if attempt < settings.MAX_VARIANT_ATTEMPTS:
                    await asyncio.sleep(settings.RATE_LIMIT_DELAY)
                continue

            variant_bytes = crop_to_4_5_ratio(variant_bytes)
            await asyncio.sleep(settings.RATE_LIMIT_DELAY)

            try:
                is_valid, _ = await asyncio.to_thread(
                    validate_generated_variant, original_images, variant_bytes, result, variant_angle
                )
            except Exception as e:
                await _notify(on_step, "variants", f"Validation error on attempt {attempt}: {e}")
                if attempt < settings.MAX_VARIANT_ATTEMPTS:
                    await asyncio.sleep(settings.RATE_LIMIT_DELAY)
                continue

            if is_valid:
                final_variant_bytes = variant_bytes
                break
            elif attempt < settings.MAX_VARIANT_ATTEMPTS:
                await asyncio.sleep(settings.RATE_LIMIT_DELAY)

        if final_variant_bytes:
            variant_path = OUTPUT_DIR / f"{image_path.stem}_generated_{variant_angle}.jpg"
            with open(variant_path, "wb") as f:
                f.write(final_variant_bytes)
            variant_paths[variant_angle] = str(variant_path)
            await _notify(on_step, "variants", f"{variant_angle.capitalize()}-view saved.")
        else:
            await _notify(on_step, "variants", f"Could not generate {variant_angle}-view after {settings.MAX_VARIANT_ATTEMPTS} attempts.")

    return variant_paths


async def process_product(image_path: str, use_ml: bool = True, on_step=None, user_hint: str = "") -> dict:
    """
    Full pipeline for one product.
    on_step(step_name, message) is called at each stage — supports both sync
    and async callbacks. All blocking API calls are offloaded to a thread pool
    so the event loop stays responsive throughout.
    Returns a result dict including generated_image_path and variant_paths.
    """
    ensure_directories()
    image_path = Path(image_path)

    if use_ml:
        await _notify(on_step, "features", f"Extracting features from {image_path.name}...")
        features = await asyncio.to_thread(extract_product_features, str(image_path))
        await _notify(on_step, "features", f"Garment: {features.get('garment_type')} ({features.get('color')}, {features.get('fit')}, {features.get('gender')})")

        await _notify(on_step, "ml", "Running ML prediction...")
        ml_prediction = await asyncio.to_thread(
            predict_image_settings,
            features['garment_type'], features['color'], features['fit'], features['gender']
        )
        img_s = ml_prediction['image_settings']
        await _notify(on_step, "ml", f"Predicted CTR: {ml_prediction['predicted_conversion_rate']*100:.1f}%  |  {img_s['style']}, {img_s['lighting']}")

        debate_result = await _run_debate_streaming(ml_prediction, features)
        final_s = debate_result['final_image_settings']
        await _notify(on_step, "debate", f"Consensus: {debate_result['consensus_type']}  |  {final_s['style']}, {final_s['lighting']}")

        await _notify(on_step, "scenario", "Generating photography scenario...")
        photography_scenario = generate_photography_scenario(final_s, features)

        if user_hint:
            photography_scenario["user_guidance"] = user_hint

        description = await _stream_agent(
            get_gemini_client(),
            build_description_prompt(features, photography_scenario),
            "Writing product description..."
        )

        result = {
            **features,
            "photography_scenario": photography_scenario,
            "description": description,
            "ml_metadata": {
                "ml_prediction": ml_prediction,
                "debate_log": debate_result['debate_log'],
                "final_reasoning": debate_result['reasoning'],
                "consensus_type": debate_result['consensus_type']
            }
        }
    else:
        await _notify(on_step, "analysis", "Analyzing product (legacy mode)...")
        result = await asyncio.to_thread(analyze_product_image, str(image_path))
        await _notify(on_step, "analysis", f"Garment: {result.get('garment_type')} ({result.get('color')}, {result.get('fit')})")

    output_file = OUTPUT_DIR / f"{image_path.stem}_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    final_image_bytes = None

    for attempt in range(1, settings.MAX_GENERATION_ATTEMPTS + 1):
        await _notify(on_step, "generate", f"Generating image (attempt {attempt}/{settings.MAX_GENERATION_ATTEMPTS})...")
        try:
            image_bytes, gen_log = await asyncio.to_thread(generate_product_image, str(image_path), result)
        except Exception as e:
            await _notify(on_step, "generate", f"API error on attempt {attempt}: {e}")
            if attempt < settings.MAX_GENERATION_ATTEMPTS:
                await asyncio.sleep(settings.RATE_LIMIT_DELAY)
            continue

        if not image_bytes:
            await _notify(on_step, "generate", f"Generation blocked: {gen_log[-1]}")
            if attempt < settings.MAX_GENERATION_ATTEMPTS:
                await asyncio.sleep(settings.RATE_LIMIT_DELAY)
            continue

        image_bytes = crop_to_4_5_ratio(image_bytes)
        await asyncio.sleep(settings.RATE_LIMIT_DELAY)

        await _notify(on_step, "validate", "Validating generated image...")
        try:
            is_valid, _ = await asyncio.to_thread(validate_generated_image, str(image_path), image_bytes, result)
        except Exception as e:
            await _notify(on_step, "validate", f"Validation error on attempt {attempt}: {e}")
            if attempt < settings.MAX_GENERATION_ATTEMPTS:
                await asyncio.sleep(settings.RATE_LIMIT_DELAY)
            continue

        await _notify(on_step, "validate", f"Validation: {'Approved' if is_valid else 'Rejected'}")

        if is_valid:
            final_image_bytes = image_bytes
            break
        elif attempt < settings.MAX_GENERATION_ATTEMPTS:
            await asyncio.sleep(settings.RATE_LIMIT_DELAY)

    result["generated_image_path"] = None
    result["variant_paths"] = {}

    if not final_image_bytes:
        await _notify(on_step, "done", f"Could not generate approved image after {settings.MAX_GENERATION_ATTEMPTS} attempts.")
        return result

    generated_image_path = OUTPUT_DIR / f"{image_path.stem}_generated.jpg"
    with open(generated_image_path, "wb") as f:
        f.write(final_image_bytes)
    result["generated_image_path"] = str(generated_image_path)
    result["variant_paths"] = await _generate_and_validate_variants(final_image_bytes, image_path, result, on_step)

    await _notify(on_step, "done", "Pipeline complete.")
    return result


async def refine_and_regenerate(result: dict, image_path: str, feedback: str, on_step=None) -> dict:
    """
    Edits the already-generated image based on free-text user feedback.
    Sends the generated image directly to the image generation model so it
    makes targeted edits rather than regenerating from scratch.
    Validates and regenerates side/back variants afterwards.
    All blocking calls are offloaded to a thread pool.
    Returns an updated result dict.
    """
    generated_path = result.get("generated_image_path")
    if not generated_path or not Path(generated_path).exists():
        await _notify(on_step, "refine", "No generated image found — cannot refine.")
        return result

    await _notify(on_step, "refine", f"Refining image: \"{feedback}\"")

    with open(generated_path, "rb") as f:
        generated_image_bytes = f.read()

    client = get_gemini_client()
    image_path_obj = Path(image_path)
    final_image_bytes = None

    prompt = (
        f"Edit this fashion product photograph: {feedback}. "
        "Keep everything else exactly the same — same person, same garment, "
        "same setting, same lighting. The garment must remain exactly as shown. "
        "No other people in the image. Return a photorealistic image only."
    )

    def _call_image_gen():
        return client.models.generate_content(
            model="nano-banana-pro-preview",
            contents=[
                types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=generated_image_bytes)),
                types.Part(text=prompt)
            ],
            config=types.GenerateContentConfig(response_modalities=["image"])
        )

    for attempt in range(1, settings.MAX_GENERATION_ATTEMPTS + 1):
        await _notify(on_step, "generate", f"Generating refined image (attempt {attempt}/{settings.MAX_GENERATION_ATTEMPTS})...")

        try:
            response = await asyncio.to_thread(_call_image_gen)
        except Exception as e:
            await _notify(on_step, "generate", f"API error on attempt {attempt}: {e}")
            if attempt < settings.MAX_GENERATION_ATTEMPTS:
                await asyncio.sleep(settings.RATE_LIMIT_DELAY)
            continue

        image_bytes = None
        if response.parts:
            for part in response.parts:
                if hasattr(part, "inline_data") and part.inline_data and hasattr(part.inline_data, "data"):
                    image_bytes = part.inline_data.data
                    break

        if not image_bytes:
            await _notify(on_step, "generate", "No image returned.")
            if attempt < settings.MAX_GENERATION_ATTEMPTS:
                await asyncio.sleep(settings.RATE_LIMIT_DELAY)
            continue

        image_bytes = crop_to_4_5_ratio(image_bytes)
        await asyncio.sleep(settings.RATE_LIMIT_DELAY)

        await _notify(on_step, "validate", "Validating refined image...")
        try:
            is_valid, _ = await asyncio.to_thread(validate_generated_image, str(image_path_obj), image_bytes, result)
        except Exception as e:
            await _notify(on_step, "validate", f"Validation error on attempt {attempt}: {e}")
            if attempt < settings.MAX_GENERATION_ATTEMPTS:
                await asyncio.sleep(settings.RATE_LIMIT_DELAY)
            continue

        await _notify(on_step, "validate", f"Validation: {'Approved' if is_valid else 'Rejected'}")

        if is_valid:
            final_image_bytes = image_bytes
            break
        elif attempt < settings.MAX_GENERATION_ATTEMPTS:
            await asyncio.sleep(settings.RATE_LIMIT_DELAY)

    if not final_image_bytes:
        await _notify(on_step, "done", "Could not generate approved refined image.")
        return result

    result = dict(result)
    generated_image_path = OUTPUT_DIR / f"{image_path_obj.stem}_generated.jpg"
    with open(generated_image_path, "wb") as f:
        f.write(final_image_bytes)
    result["generated_image_path"] = str(generated_image_path)
    result["variant_paths"] = await _generate_and_validate_variants(final_image_bytes, image_path_obj, result, on_step)

    await _notify(on_step, "done", "Refinement complete.")
    return result


def publish_to_shopify(result: dict, image_stem: str) -> str | None:
    """
    Uploads the product and all generated images to Shopify.
    On success, appends a training sample to ctr_dataset.json.
    Returns the Shopify product ID, or None on failure.
    """
    generated_images = []

    main_img = result.get("generated_image_path")
    if main_img and Path(main_img).exists():
        generated_images.append(main_img)

    for variant_path in result.get("variant_paths", {}).values():
        if variant_path and Path(variant_path).exists():
            generated_images.append(variant_path)

    if not generated_images:
        return None

    product_id = upload_product_to_shopify(
        product_name=image_stem,
        analysis_file=str(OUTPUT_DIR / f"{image_stem}_analysis.json"),
        generated_images=generated_images
    )

    if product_id:
        record = record_published_product(result)
        if record:
            print(f"Feedback loop: added sample to dataset (size now {get_dataset_size()})")

    return product_id


async def process_batch(use_ml: bool = True, on_step=None) -> list:
    """Processes all product images in data/input/ and returns a list of results."""
    ensure_directories()
    all_images = sorted([f for f in INPUT_DIR.iterdir() if f.suffix in ['.png', '.jpg']])
    images = [img for img in all_images if not ("_back" in img.stem or "_side" in img.stem)]

    if not images:
        await _notify(on_step, "batch", "No images found in data/input/")
        return []

    results = []
    for i, image_path in enumerate(images):
        await _notify(on_step, "batch", f"[{i+1}/{len(images)}] Processing {image_path.name}...")
        result = await process_product(str(image_path), use_ml=use_ml, on_step=on_step)
        results.append(result)
        if i < len(images) - 1:
            await asyncio.sleep(settings.PROCESSING_DELAY)

    return results
