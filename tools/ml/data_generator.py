import json
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Setup path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import CONVERSION_DB_JSON
from tools.taxonomy import (
    GARMENT_TYPES,
    COLORS,
    FITS,
    GENDERS,
    IMAGE_STYLES,
    LIGHTING_TYPES,
    BACKGROUNDS,
    POSES,
    EXPRESSIONS,
    ANGLES
)


def generate_realistic_performance(
    garment_type: str,
    color: str,
    style: str,
    lighting: str
) -> dict:
    base_conversion = 0.02
    
    garment_multipliers = {
        "hoodie": 1.3,
        "t-shirt": 1.1,
        "zip-up hoodie": 1.2,
        "jacket": 0.9,
        "jeans": 0.8
    }

    color_multipliers = {
        "dark": 1.2,
        "dark grey": 1.15,
        "black": 1.25,
        "light": 0.95,
        "white": 0.9,
        "colorful": 1.0
    }

    style_multipliers = {
        "urban_outdoor": 1.4,
        "skate_urban": 1.2,
        "street_style": 1.3,
        "action_sports": 1.1,
        "lifestyle_indoor": 0.95,
        "studio_minimal": 0.9,
        "artistic": 0.85
    }

    lighting_multipliers = {
        "golden_hour": 1.2,
        "natural": 1.1,
        "soft_diffused": 1.05,
        "studio": 1.0,
        "overcast": 0.95,
        "dramatic": 0.9
    }
    
    conversion_rate = base_conversion
    conversion_rate *= garment_multipliers.get(garment_type, 1.0)
    conversion_rate *= color_multipliers.get(color, 1.0)
    conversion_rate *= style_multipliers.get(style, 1.0)
    conversion_rate *= lighting_multipliers.get(lighting, 1.0)

    randomness = random.uniform(0.8, 1.2)
    conversion_rate *= randomness

    conversion_rate = max(0.005, min(0.06, conversion_rate))

    impressions = random.randint(1000, 5000)

    ctr = random.uniform(0.05, 0.15)
    clicks = int(impressions * ctr)

    purchases = int(impressions * conversion_rate)

    if conversion_rate > 0 and purchases == 0:
        purchases = 1

    return {
        "conversion_rate": round(conversion_rate, 4),
        "impressions": impressions,
        "clicks": clicks,
        "purchases": purchases
    }


def generate_product(index: int) -> dict:
    garment_type = random.choice(GARMENT_TYPES)
    color = random.choice(COLORS)
    fit = random.choice(FITS)
    gender = random.choice(GENDERS)

    style = random.choice(IMAGE_STYLES)
    lighting = random.choice(LIGHTING_TYPES)
    background = random.choice(BACKGROUNDS)
    pose = random.choice(POSES)
    expression = random.choice(EXPRESSIONS)
    angle = random.choice(ANGLES)
    performance = generate_realistic_performance(
        garment_type, color, style, lighting
    )

    days_ago = random.randint(0, 180)
    timestamp = datetime.now() - timedelta(days=days_ago)

    return {
        "id": f"{garment_type.replace(' ', '_')}_{color.replace(' ', '_')}_{index:03d}",
        "garment_type": garment_type,
        "color": color,
        "fit": fit,
        "gender": gender,
        "image_settings": {
            "style": style,
            "lighting": lighting,
            "background": background,
            "pose": pose,
            "expression": expression,
            "angle": angle
        },
        "performance": performance,
        "created_at": timestamp.isoformat()
    }

def generate_dataset(num_products: int = 1000) -> dict:
    products = [generate_product(i) for i in range(num_products)]
    return {
        "version": "1.0",
        "description": "Synthetic conversion data for e-commerce products",
        "last_updated": datetime.now().isoformat(),
        "total_products": len(products),
        "products": products
    }

def save_dataset(dataset: dict, output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2, ensure_ascii=False)

    print(f"Saved {dataset['total_products']} products to {output_path}")

def print_statistics(dataset: dict) -> None:
    products = dataset["products"]
    conversion_rates = [p["performance"]["conversion_rate"] for p in products]
    avg_conversion = sum(conversion_rates) / len(conversion_rates)
    min_conversion = min(conversion_rates)
    max_conversion = max(conversion_rates)
    valid_products = [p for p in products if p["performance"]["impressions"] >= 1000]

    print("\nDataset Statistics:")
    print(f"  Total products: {len(products)}")
    print(f"  Products with 1000+ impressions: {len(valid_products)}")
    print(f"  Average conversion rate: {avg_conversion:.2%}")
    print(f"  Min conversion: {min_conversion:.2%}")
    print(f"  Max conversion: {max_conversion:.2%}")

    print("\nBreakdown by garment type:")
    for garment_type in GARMENT_TYPES:
        count = len([p for p in products if p["garment_type"] == garment_type])
        print(f"  {garment_type}: {count}")

if __name__ == "__main__":
    print("Generating synthetic dataset with 1000 products...")

    dataset = generate_dataset(num_products=1000)
    save_dataset(dataset, CONVERSION_DB_JSON)
    print_statistics(dataset)

    print("Done")
