import os
import json
import base64
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

_RATE_DELAY = 0.5

load_dotenv()


def _get_credentials() -> tuple[str, str, str, dict]:
    shop_name = os.getenv("SHOPIFY_SHOP_NAME", "")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    api_url = f"https://{shop_name}.myshopify.com/admin/api/2024-01"
    hdrs = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}
    return shop_name, access_token, api_url, hdrs


def create_product(title: str, description: str, sku: str, tags: list, price: str = "299.00") -> int:
    _, _, api_url, headers = _get_credentials()
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
        f"{api_url}/products.json",
        headers=headers,
        json=data
    )
    time.sleep(_RATE_DELAY)
    response.raise_for_status()
    result = response.json()
    product_id = result["product"]["id"]
    print(f"Product created: {title} (ID: {product_id})")
    return product_id


def upload_image(product_id: int, image_path: str, alt_text: str):
    _, _, api_url, headers = _get_credentials()
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    data = {
        "image": {
            "attachment": image_base64,
            "alt": alt_text
        }
    }

    response = requests.post(
        f"{api_url}/products/{product_id}/images.json",
        headers=headers,
        json=data
    )

    time.sleep(_RATE_DELAY)
    response.raise_for_status()

    print(f"Image uploaded: {alt_text}")


def upload_product_to_shopify(product_name: str, analysis_file: str, generated_images: list):
    print(f"Uploading '{product_name}' to Shopify")

    try:
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    except Exception as e:
        print(f"{e}")
        return None

    title = analysis.get("title", "AI Generated Product")
    description = analysis.get("description", "")
    sku = analysis.get("art_nr", f"AI-{product_name.upper()}")

    tags = [
        analysis.get("garment_type", ""),
        analysis.get("gender", ""),
        analysis.get("color", ""),
        analysis.get("fit", ""),
        "ai-generated"
    ]
    tags = [t for t in tags if t]

    try:
        product_id = create_product(title, description, sku, tags)
    except Exception as e:
        print(f"Could not create product: {e}")
        return None

    print(f"Uploading {len(generated_images)} images")

    for img_path in generated_images:
        try:
            filename = Path(img_path).name
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
            print(f"Could not upload {filename}: {e}")

    shop_name, _, _, _ = _get_credentials()
    print("Product upload complete")
    print(f"https://{shop_name}.myshopify.com/admin/products/{product_id}\n")

    return product_id
