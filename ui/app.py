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

from config.paths import INPUT_DIR, ensure_directories
from config.settings import settings
from ui.pipeline import process_product, refine_and_regenerate, publish_to_shopify
from tools.feedback_loop import retrain_model, get_dataset_size


async def _on_step(name: str, msg: str):
    await cl.Message(content=f"**{name}** — {msg}").send()


def _require_api_key() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _load_products() -> list:
    products_json = INPUT_DIR / "products.json"
    if not products_json.exists():
        return []
    with open(products_json, "r", encoding="utf-8") as f:
        return json.load(f)


def _match_images(image_paths: list, products: list) -> tuple[list, list]:
    """Return (matched, unmatched) based on filename stem vs products.json entries."""
    product_stems = {Path(p["image"]).stem for p in products}
    matched, unmatched = [], []
    for img in image_paths:
        (matched if Path(img).stem in product_stems else unmatched).append(img)
    return matched, unmatched


async def _ask_brand():
    current = settings.DEFAULT_BRAND_IDENTITY
    await cl.Message(
        content=(
            f"**Brand identity** used for product descriptions and photography style.\n\n"
            f"Current: *{current}*\n\n"
            "Type a new brand identity to replace it, or press **Skip** to keep the current one."
        ),
        actions=[cl.Action(name="skip_brand", payload={}, label="Skip — keep current")]
    ).send()
    cl.user_session.set("state", "awaiting_brand")


async def _ask_upload():
    await cl.Message(
        content="Upload your product folder — drag in `products.json` and all product images at once."
    ).send()
    cl.user_session.set("state", "awaiting_files")


@cl.on_chat_start
async def on_chat_start():
    ensure_directories()
    cl.user_session.set("result", None)
    cl.user_session.set("image_path", None)
    cl.user_session.set("matched_images", [])
    cl.user_session.set("manual_index", 0)
    cl.user_session.set("products_loaded", False)

    if not _require_api_key():
        cl.user_session.set("state", "awaiting_api_key")
        await cl.Message(content="Welcome to skejl! Please enter your Gemini API key to get started:").send()
        return

    await cl.Message(content="API key found ✓").send()
    await _ask_brand()


@cl.action_callback("skip_brand")
async def on_skip_brand(action: cl.Action):
    await cl.Message(content="Brand identity unchanged.").send()
    await _ask_upload()


async def _process_next():
    """Process the next unprocessed product image in the queue."""
    matched_images = cl.user_session.get("matched_images", [])
    idx = cl.user_session.get("manual_index", 0)

    if idx >= len(matched_images):
        await cl.Message(content="All products processed ✓").send()
        cl.user_session.set("state", "done")
        return

    image_path = matched_images[idx]
    cl.user_session.set("image_path", image_path)
    cl.user_session.set("result", None)

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

    # Check Shopify credentials — ask if missing
    if not os.environ.get("SHOPIFY_SHOP_NAME"):
        cl.user_session.set("state", "awaiting_shopify_shop")
        await cl.Message(
            content="Enter your Shopify shop name (subdomain only, e.g. `my-store`):"
        ).send()
        return

    if not os.environ.get("SHOPIFY_ACCESS_TOKEN"):
        cl.user_session.set("state", "awaiting_shopify_token")
        await cl.Message(
            content="Enter your Shopify Admin API access token:"
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

    await cl.Message(content="Regenerating from scratch...").send()
    result = await process_product(image_path, use_ml=True, on_step=_on_step)
    cl.user_session.set("result", result)
    await _show_results(result)


@cl.action_callback("next_product")
async def on_next_product(action: cl.Action):
    await _advance()


async def _advance():
    """Move to the next product."""
    matched_images = cl.user_session.get("matched_images", [])
    idx = cl.user_session.get("manual_index", 0)
    next_idx = idx + 1
    cl.user_session.set("manual_index", next_idx)

    if next_idx >= len(matched_images):
        await cl.Message(content="All products processed ✓").send()
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
            actions.append(cl.Action(name="next_product", payload={}, label=f"Skip → {next_name}"))
        await cl.Message(
            content=(
                f"Generation failed after {settings.MAX_GENERATION_ATTEMPTS} attempts.\n"
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
        actions.append(cl.Action(name="next_product", payload={}, label=f"Skip → {next_name}"))

    await cl.Message(
        content="Happy with the result? Write feedback to refine, or use the buttons below.",
        actions=actions
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    state = cl.user_session.get("state", "awaiting_api_key")

    # ── API key ───────────────────────────────────────────────────────────────
    if state == "awaiting_api_key" and not message.elements:
        api_key = message.content.strip()
        os.environ["GEMINI_API_KEY"] = api_key
        settings.GEMINI_API_KEY = api_key
        await cl.Message(content="API key saved ✓").send()
        await _ask_brand()
        return

    # ── Brand identity setup ──────────────────────────────────────────────────
    if state == "awaiting_brand" and not message.elements:
        brand = message.content.strip()
        if brand:
            settings.DEFAULT_BRAND_IDENTITY = brand
            await cl.Message(content=f"Brand identity saved ✓\n> {brand}").send()
        await _ask_upload()
        return

    # ── Shopify shop name ─────────────────────────────────────────────────────
    if state == "awaiting_shopify_shop" and not message.elements:
        shop = message.content.strip().lower().removesuffix(".myshopify.com")
        os.environ["SHOPIFY_SHOP_NAME"] = shop
        await cl.Message(content=f"Shop name saved: `{shop}.myshopify.com` ✓").send()

        if not os.environ.get("SHOPIFY_ACCESS_TOKEN"):
            cl.user_session.set("state", "awaiting_shopify_token")
            await cl.Message(content="Enter your Shopify Admin API access token:").send()
        else:
            cl.user_session.set("state", "processing")
            result = cl.user_session.get("result")
            image_path = cl.user_session.get("image_path")
            if result and image_path:
                await _do_publish(result, image_path)
        return

    # ── Shopify access token ──────────────────────────────────────────────────
    if state == "awaiting_shopify_token" and not message.elements:
        token = message.content.strip()
        os.environ["SHOPIFY_ACCESS_TOKEN"] = token
        await cl.Message(content="Shopify access token saved ✓").send()
        cl.user_session.set("state", "processing")
        result = cl.user_session.get("result")
        image_path = cl.user_session.get("image_path")
        if result and image_path:
            await _do_publish(result, image_path)
        return

    # ── File uploads ──────────────────────────────────────────────────────────
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
            msgs.append("products.json saved ✓")
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
        all_matched = list({p: p for p in existing + matched}.keys())
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
            cl.user_session.set("state", "processing")
            cl.user_session.set("manual_index", 0)
            await _process_next()
        return

    # ── Publish shortcut ──────────────────────────────────────────────────────
    if message.content.strip().lower() in ("publicera", "publish"):
        await on_publish(cl.Action(name="publish", payload={}))
        return

    # ── /brand — update brand identity at any time ────────────────────────────
    if message.content.strip().lower() == "/brand":
        prev_state = cl.user_session.get("state")
        cl.user_session.set("brand_return_state", prev_state)
        cl.user_session.set("state", "awaiting_brand_update")
        await cl.Message(
            content=(
                f"Current brand identity:\n> {settings.DEFAULT_BRAND_IDENTITY}\n\n"
                "Type the new brand identity:"
            )
        ).send()
        return

    if state == "awaiting_brand_update" and not message.elements:
        brand = message.content.strip()
        if brand:
            settings.DEFAULT_BRAND_IDENTITY = brand
            await cl.Message(content=f"Brand identity updated ✓\n> {brand}").send()
        return_state = cl.user_session.get("brand_return_state", "awaiting_files")
        cl.user_session.set("state", return_state)
        return

    # ── /retrain — retrain the CTR model ─────────────────────────────────────
    if message.content.strip().lower() == "/retrain":
        await cl.Message(content=f"Retraining model on {get_dataset_size()} samples...").send()
        try:
            metrics = await asyncio.to_thread(retrain_model)
            await cl.Message(
                content=(
                    f"Model retrained ✓\n"
                    f"- Samples: {metrics['n_samples']}\n"
                    f"- MAE: {metrics['mae']*100:.3f}% CTR\n"
                    f"- R²: {metrics['r2']}"
                )
            ).send()
        except Exception as e:
            await cl.Message(content=f"Retraining failed: {e}").send()
        return

    # ── Feedback after generation failure — retry with user hint ─────────────
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

    # ── Free-text feedback — refine current result ────────────────────────────
    result = cl.user_session.get("result")
    image_path = cl.user_session.get("image_path")

    if state == "reviewing" and result and image_path and result.get("generated_image_path"):
        await cl.Message(content="Refining based on your feedback...").send()
        updated_result = await refine_and_regenerate(
            result, image_path, message.content, on_step=_on_step
        )
        cl.user_session.set("result", updated_result)
        await _show_results(updated_result)
        return

    # ── Fallback / help ───────────────────────────────────────────────────────
    await cl.Message(
        content=(
            "**How to use:**\n"
            "1. Upload `products.json` + product images (drag all files at once)\n"
            "2. The pipeline runs automatically for each product\n"
            "3. Write feedback to refine the image, e.g. *'make it more urban'*\n"
            "4. Press **Publish to Shopify** when happy, then move to the next product\n\n"
            "**Commands:** `/brand` — update brand identity  ·  `/retrain` — retrain ML model"
        )
    ).send()