import asyncio
import json
import os
import sys
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import chainlit as cl
from chainlit.input_widget import TextInput

from config.paths import INPUT_DIR, ensure_directories
from config.settings import settings
from ui.pipeline import process_product, refine_and_regenerate, publish_to_shopify
from tools.feedback_loop import retrain_model, get_dataset_size


async def _on_step(name: str, msg: str):
    await cl.Message(content=f"**{name}** — {msg}").send()


def _load_products() -> list:
    products_json = INPUT_DIR / "products.json"
    if not products_json.exists():
        return []
    with open(products_json, "r", encoding="utf-8") as f:
        return json.load(f)


def _match_images(image_paths: list, products: list) -> tuple[list, list]:
    product_stems = {Path(p["image"]).stem for p in products}
    matched, unmatched = [], []
    for img in image_paths:
        (matched if Path(img).stem in product_stems else unmatched).append(img)
    return matched, unmatched


@cl.on_chat_start
async def on_chat_start():
    ensure_directories()
    cl.user_session.set("result", None)
    cl.user_session.set("image_path", None)
    cl.user_session.set("matched_images", [])
    cl.user_session.set("manual_index", 0)
    cl.user_session.set("products_loaded", False)
    cl.user_session.set("state", "awaiting_files")

    await cl.ChatSettings([
        TextInput(
            id="gemini_api_key",
            label="Gemini API Key",
            initial=os.environ.get("GEMINI_API_KEY", ""),
            placeholder="AIza...",
        ),
        TextInput(
            id="brand_identity",
            label="Brand Identity",
            initial=settings.DEFAULT_BRAND_IDENTITY,
        ),
        TextInput(
            id="shopify_shop",
            label="Shopify Shop Name",
            initial=os.environ.get("SHOPIFY_SHOP_NAME", ""),
            placeholder="my-store",
        ),
        TextInput(
            id="shopify_token",
            label="Shopify Access Token",
            initial=os.environ.get("SHOPIFY_ACCESS_TOKEN", ""),
            placeholder="shpat_...",
        ),
    ]).send()

    await cl.Message(
        content=(
            "Welcome to skejl! Open **Settings** to configure your API key and brand identity, "
            "then drag in `products.json` + product images to get started."
        )
    ).send()


@cl.on_settings_update
async def on_settings_update(settings_dict: dict):
    if api_key := settings_dict.get("gemini_api_key", "").strip():
        os.environ["GEMINI_API_KEY"] = api_key
        settings.GEMINI_API_KEY = api_key

    if brand := settings_dict.get("brand_identity", "").strip():
        settings.DEFAULT_BRAND_IDENTITY = brand

    if shop := settings_dict.get("shopify_shop", "").strip():
        os.environ["SHOPIFY_SHOP_NAME"] = shop.lower().removesuffix(".myshopify.com")

    if token := settings_dict.get("shopify_token", "").strip():
        os.environ["SHOPIFY_ACCESS_TOKEN"] = token


def _missing_settings() -> list[str]:
    missing = []
    if not settings.GEMINI_API_KEY and not os.environ.get("GEMINI_API_KEY"):
        missing.append("Gemini API Key")
    if not os.environ.get("SHOPIFY_SHOP_NAME"):
        missing.append("Shopify Shop Name")
    if not os.environ.get("SHOPIFY_ACCESS_TOKEN"):
        missing.append("Shopify Access Token")
    return missing


async def _process_next():
    if missing := _missing_settings():
        fields = ", ".join(f"`{m}`" for m in missing)
        await cl.Message(
            content=f"Missing settings: {fields} — open **Settings** and fill them in before processing."
        ).send()
        return

    matched_images = cl.user_session.get("matched_images", [])
    idx = cl.user_session.get("manual_index", 0)

    if idx >= len(matched_images):
        await cl.Message(content="All products processed.").send()
        cl.user_session.set("state", "done")
        return

    image_path = matched_images[idx]
    cl.user_session.set("image_path", image_path)
    cl.user_session.set("result", None)
    cl.user_session.set("state", "processing")

    await cl.Message(
        content=f"Processing `{Path(image_path).name}` ({idx + 1}/{len(matched_images)})..."
    ).send()

    result = await process_product(image_path, use_ml=True, on_step=_on_step)
    cl.user_session.set("result", result)
    await _show_results(result)


@cl.action_callback("publish")
async def on_publish(action: cl.Action):
    result = cl.user_session.get("result")
    image_path = cl.user_session.get("image_path")

    if not result or not image_path:
        await cl.Message(content="Nothing to publish yet.").send()
        return

    if not os.environ.get("SHOPIFY_SHOP_NAME") or not os.environ.get("SHOPIFY_ACCESS_TOKEN"):
        await cl.Message(
            content="Shopify credentials are missing — open **Settings** and fill in Shop Name and Access Token."
        ).send()
        return

    await _do_publish(result, image_path)


async def _do_publish(result: dict, image_path: str):
    await cl.Message(content="Uploading to Shopify...").send()
    try:
        product_id = publish_to_shopify(result, Path(image_path).stem)
        if product_id:
            shop = os.environ.get("SHOPIFY_SHOP_NAME", "your-shop")
            await cl.Message(
                content=f"Published! Product ID: `{product_id}`\nhttps://{shop}.myshopify.com/admin/products/{product_id}"
            ).send()
        else:
            await cl.Message(content="Shopify upload failed — no generated images found.").send()
    except Exception as e:
        await cl.Message(content=f"Shopify error: {e}").send()

    await _advance()


@cl.action_callback("regenerate")
async def on_regenerate(action: cl.Action):
    image_path = cl.user_session.get("image_path")

    if not image_path:
        await cl.Message(content="No image to regenerate.").send()
        return

    cl.user_session.set("state", "processing")
    await cl.Message(content="Regenerating from scratch...").send()
    result = await process_product(image_path, use_ml=True, on_step=_on_step)
    cl.user_session.set("result", result)
    await _show_results(result)


@cl.action_callback("next_product")
async def on_next_product(action: cl.Action):
    await _advance()


async def _advance():
    matched_images = cl.user_session.get("matched_images", [])
    idx = cl.user_session.get("manual_index", 0)
    next_idx = idx + 1
    cl.user_session.set("manual_index", next_idx)

    if next_idx >= len(matched_images):
        await cl.Message(content="All products processed.").send()
        cl.user_session.set("state", "done")
    else:
        await _process_next()


async def _show_results(result: dict):
    images = []

    main_img = result.get("generated_image_path")
    if main_img and Path(main_img).exists():
        images.append(cl.Image(name="main", path=main_img, display="inline"))

    for angle, variant_path in result.get("variant_paths", {}).items():
        if variant_path and Path(variant_path).exists():
            images.append(cl.Image(name=angle, path=variant_path, display="inline"))

    if images:
        cl.user_session.set("state", "reviewing")
        await cl.Message(content="Generated images:", elements=images).send()
    else:
        matched_images = cl.user_session.get("matched_images", [])
        idx = cl.user_session.get("manual_index", 0)
        actions = [cl.Action(name="regenerate", payload={}, label="Retry (same settings)")]
        if (idx + 1) < len(matched_images):
            next_name = Path(matched_images[idx + 1]).name
            actions.append(cl.Action(name="next_product", payload={}, label=f"Skip -> {next_name}"))
        rejection = result.get("last_rejection_reason", "")
        reason_block = f"\n\n**Validator feedback:** {rejection}" if rejection else ""
        await cl.Message(
            content=(
                f"Generation failed after {settings.MAX_GENERATION_ATTEMPTS} attempts.{reason_block}\n\n"
                "Describe what to change (e.g. *'less dramatic lighting'*, *'outdoor setting'*), "
                "or press **Retry** to try again with the same settings."
            ),
            actions=actions
        ).send()
        cl.user_session.set("state", "awaiting_generation_feedback")
        return

    title = result.get("title", "")
    description = result.get("description", "")
    if title or description:
        parts = []
        if title:
            parts.append(f"**{title}**")
        if description:
            parts.append(description)
        await cl.Message(content="\n\n".join(parts)).send()

    matched_images = cl.user_session.get("matched_images", [])
    idx = cl.user_session.get("manual_index", 0)
    has_more = (idx + 1) < len(matched_images)

    actions = [
        cl.Action(name="publish", payload={}, label="Publish to Shopify"),
        cl.Action(name="regenerate", payload={}, label="Regenerate"),
    ]
    if has_more:
        next_name = Path(matched_images[idx + 1]).name
        actions.append(cl.Action(name="next_product", payload={}, label=f"Skip -> {next_name}"))

    await cl.Message(
        content="Happy with the result? Write feedback to refine, or use the buttons below.",
        actions=actions
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    state = cl.user_session.get("state", "awaiting_files")

    uploaded_json = False
    uploaded_images = []

    for element in message.elements:
        if not hasattr(element, "path") or not element.path:
            continue

        src = Path(element.path)
        suffix = Path(element.name).suffix.lower()

        if suffix == ".json":
            shutil.copy(src, INPUT_DIR / "products.json")
            uploaded_json = True
            cl.user_session.set("products_loaded", True)

        elif suffix in (".jpg", ".jpeg", ".png"):
            dest = INPUT_DIR / element.name
            shutil.copy(src, dest)
            uploaded_images.append(str(dest))

    if uploaded_json or uploaded_images:
        msgs = []
        if uploaded_json:
            msgs.append("products.json saved.")
        if uploaded_images:
            names = ", ".join(Path(p).name for p in uploaded_images)
            msgs.append(f"{len(uploaded_images)} image(s) saved: {names}")
        await cl.Message(content="\n".join(msgs)).send()

        products = _load_products()
        if not products:
            await cl.Message(content="products.json is missing or empty — please include it in your upload.").send()
            return

        matched, unmatched = _match_images(uploaded_images, products)

        existing = cl.user_session.get("matched_images", [])
        all_matched = list(dict.fromkeys(existing + matched))
        cl.user_session.set("matched_images", all_matched)

        if matched:
            await cl.Message(
                content=f"Matched {len(matched)} image(s): {', '.join(Path(p).name for p in matched)}"
            ).send()
        if unmatched:
            await cl.Message(
                content=f"No match in products.json for: {', '.join(Path(p).name for p in unmatched)}"
            ).send()

        if all_matched:
            if not cl.user_session.get("products_loaded"):
                await cl.Message(
                    content="Upload `products.json` before processing images — drag it in together with your images."
                ).send()
                return
            cl.user_session.set("manual_index", 0)
            await _process_next()
        return

    if message.content.strip().lower() == "/retrain":
        await cl.Message(content=f"Retraining model on {get_dataset_size()} samples...").send()
        try:
            metrics = await asyncio.to_thread(retrain_model)
            await cl.Message(
                content=(
                    f"Model retrained.\n"
                    f"- Samples: {metrics['n_samples']}\n"
                    f"- MAE: {metrics['mae']*100:.3f}% CTR\n"
                    f"- R2: {metrics['r2']}"
                )
            ).send()
        except Exception as e:
            await cl.Message(content=f"Retraining failed: {e}").send()
        return

    if state == "awaiting_generation_feedback" and not message.elements:
        image_path = cl.user_session.get("image_path")
        if image_path:
            hint = message.content.strip()
            await cl.Message(content="Retrying with your guidance...").send()
            cl.user_session.set("state", "processing")
            updated_result = await process_product(image_path, use_ml=True, on_step=_on_step, user_hint=hint)
            cl.user_session.set("result", updated_result)
            await _show_results(updated_result)
        return

    result = cl.user_session.get("result")
    image_path = cl.user_session.get("image_path")

    if state == "reviewing" and result and image_path and result.get("generated_image_path"):
        await cl.Message(content="Refining based on your feedback...").send()
        cl.user_session.set("state", "processing")
        updated_result = await refine_and_regenerate(
            result, image_path, message.content, on_step=_on_step
        )
        cl.user_session.set("result", updated_result)
        await _show_results(updated_result)
        return

    await cl.Message(
        content=(
            "Upload `products.json` + product images to get started.\n\n"
            "**Available command:** `/retrain` — retrain the ML model"
        )
    ).send()
