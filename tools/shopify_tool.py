"""
Shopify Integration - Laddar upp produkter med bilder
"""

import os
import json
import base64
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SHOP_NAME = os.getenv("SHOPIFY_SHOP_NAME")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-01"

headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}


def create_product(title: str, description: str, sku: str, tags: list, price: str = "299.00") -> int:
    """
    Skapar en produkt i Shopify.
    Returnerar product_id.
    """
    data = {
        "product": {
            "title": title,
            "body_html": description,
            "vendor": "Skejl AI",
            "product_type": "Apparel",
            "tags": ", ".join(tags),
            "variants": [{
                "sku": sku,
                "price": price
            }]
        }
    }

    response = requests.post(
        f"{API_URL}/products.json",
        headers=headers,
        json=data
    )

    time.sleep(0.5)  # Rate limiting
    response.raise_for_status()

    result = response.json()
    product_id = result["product"]["id"]

    print(f"✓ Produkt skapad: {title} (ID: {product_id})")
    return product_id


def upload_image(product_id: int, image_path: str, alt_text: str):
    """
    Laddar upp en bild till en produkt.
    """
    # Läs bilden och konvertera till base64
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    data = {
        "image": {
            "attachment": image_base64,
            "alt": alt_text
        }
    }

    response = requests.post(
        f"{API_URL}/products/{product_id}/images.json",
        headers=headers,
        json=data
    )

    time.sleep(0.5)  # Rate limiting
    response.raise_for_status()

    print(f"Bild uppladdad: {alt_text}")


def upload_product_to_shopify(product_name: str, analysis_file: str, generated_images: list):
    """
    Huvudfunktion - laddar upp en komplett produkt med bilder.

    Args:
        product_name: t.ex. "honda"
        analysis_file: t.ex. "data/output/honda_analysis.json"
        generated_images: lista med bildfiler, t.ex.:
            ["data/output/honda_front_generated.jpg",
             "data/output/honda_side_generated.jpg",
             "data/output/honda_back_generated.jpg"]

    Returns:
        product_id om success, None om fel
    """
    print(f"\nLaddar upp '{product_name}' till Shopify...")

    # 1. Läs analysis-data (innehåller all information vi behöver)
    try:
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    except Exception as e:
        print(f"Kunde inte läsa analysis-fil: {e}")
        return None

    # 2. Bygg produktdata från analysis-filen
    title = analysis.get("title", "AI Generated Product")
    description = analysis.get("description", "")
    sku = analysis.get("art_nr", f"AI-{product_name.upper()}")

    # Samla tags från analysis-filen
    tags = [
        analysis.get("garment_type", ""),
        analysis.get("gender", ""),
        analysis.get("color", ""),
        analysis.get("fit", ""),
        "ai-generated"
    ]
    tags = [t for t in tags if t]  # Ta bort tomma

    # 4. Skapa produkten
    try:
        product_id = create_product(title, description, sku, tags)
    except Exception as e:
        print(f"❌ Kunde inte skapa produkt: {e}")
        return None

    # 5. Ladda upp bilder
    print(f"📸 Laddar upp {len(generated_images)} bilder...")

    for img_path in generated_images:
        try:
            filename = Path(img_path).name

            # Identifiera vilket view
            if "front" in filename:
                alt = f"{title} - Front view"
            elif "side" in filename:
                alt = f"{title} - Side view"
            elif "back" in filename:
                alt = f"{title} - Back view"
            else:
                alt = f"{title} - Product view"

            upload_image(product_id, img_path, alt)

        except Exception as e:
            print(f"  ⚠️  Kunde inte ladda upp {filename}: {e}")

    # 6. Klart!
    print(f"✅ Produkt uppladdad!")
    print(f"🔗 https://{SHOP_NAME}.myshopify.com/admin/products/{product_id}\n")

    return product_id
