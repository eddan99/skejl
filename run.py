import json
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Laddar .env (GEMINI_API_KEY) innan något annat
load_dotenv()

# Lägger projektrooten i path så att "from logic..." och "from tools..." funkar
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.vision_tool import analyze_product_image
from tools.image_gen_tool import generate_product_image, generate_variant
from tools.validation import validate_generated_image, validate_generated_variant
from tools.shopify_tool import upload_product_to_shopify
from tools.image_utils import crop_to_4_5_ratio
import os

INPUT_DIR = PROJECT_ROOT / "data" / "input"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def find_all_product_images(base_image_path: Path) -> list:
    """
    Hittar alla bilder för en produkt.

    Namnkonvention:
      - Huvudbild: honda.jpg
      - Baksida: honda_back.jpg
      - Sidovy: honda_side.jpg

    Exempel:
      - Input: data/input/honda.jpg
      - Output: [data/input/honda.jpg, data/input/honda_back.jpg, data/input/honda_side.jpg]
    """
    stem = base_image_path.stem  # "honda"
    parent = base_image_path.parent  # data/input/
    ext = base_image_path.suffix  # ".jpg"

    found_images = [str(base_image_path)]  # Lägg alltid till huvudbilden först

    # Kolla om det finns back/side bilder
    for variant in ["_back", "_side"]:
        variant_path = parent / f"{stem}{variant}{ext}"
        if variant_path.exists():
            found_images.append(str(variant_path))

    return found_images


def main():
    # Hitta alla bilder i data/input/
    all_images = sorted(INPUT_DIR.glob("*.png")) + sorted(INPUT_DIR.glob("*.jpg"))

    # Filtrera bort variant-bilder (_back, _side) - de ska bara användas för validering
    images = [img for img in all_images if not ("_back" in img.stem or "_side" in img.stem)]

    if not images:
        print("Inga huvudbilder hittades i data/input/")
        return

    for i, image_path in enumerate(images):
        print(f"\n--- Analyserar: {image_path.name} ---")

        result = analyze_product_image(str(image_path))

        # Printa resultat
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Spara analysis till data/output/
        OUTPUT_DIR.mkdir(exist_ok=True)
        output_file = OUTPUT_DIR / f"{image_path.stem}_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Sparad: {output_file.name}")

        # Paus mellan Gemini-anrop för att undvika rate limit
        time.sleep(3)

        # Steg 2: Generera och validera produktbild (max 2 försök)
        print(f"\n--- Genererar bild: {image_path.name} ---")

        max_attempts = 2
        final_image_bytes = None

        for attempt in range(1, max_attempts + 1):
            print(f"  [Försök {attempt}/{max_attempts}]")

            # Generera bild
            image_bytes, gen_log = generate_product_image(str(image_path), result)

            # Printa genererings-log
            for entry in gen_log:
                print(f"  [{entry}]")

            # Om generering misslyckades (blockerad/fel)
            if not image_bytes:
                print(f"  [Generering misslyckades på försök {attempt}]")
                if attempt < max_attempts:
                    time.sleep(3)  # Vänta innan nästa försök
                continue

            # Croppa till 4:5 format
            print(f"  [Croppar till 4:5 format...]")
            image_bytes = crop_to_4_5_ratio(image_bytes)

            # Paus innan validering
            time.sleep(3)

            # Validera bilden
            print(f"  [Validerar bild...]")
            is_valid, validation_report = validate_generated_image(
                str(image_path),
                image_bytes,
                result
            )

            # Printa valideringsresultat
            print(f"  [Validering: {'GODKÄND' if is_valid else 'UNDERKÄND'}]")
            report_lines = validation_report.split('\n')
            for line in report_lines[1:]:  # Skippa första raden (APPROVED/REJECTED)
                if line.strip():
                    print(f"  [{line.strip()}]")

            # Om bilden är godkänd - spara och avsluta
            if is_valid:
                final_image_bytes = image_bytes
                print(f"  [Bild godkänd på försök {attempt}]")
                break
            else:
                print(f"  [Bild underkänd på försök {attempt}]")
                if attempt < max_attempts:
                    print(f"  [Försöker igen...]")
                    time.sleep(3)

        # Spara eller hoppa över
        if final_image_bytes:
            generated_image_path = OUTPUT_DIR / f"{image_path.stem}_generated.jpg"
            with open(generated_image_path, "wb") as f:
                f.write(final_image_bytes)
            print(f"Sparad: {generated_image_path.name}")

            # Steg 3: Generera och validera varianter (side och back)
            # Hitta alla originalbilder först (behövs för både generering och validering)
            original_images = find_all_product_images(image_path)

            for variant_angle in ["side", "back"]:
                print(f"\n--- Genererar {variant_angle}-variant: {image_path.name} ---")

                max_variant_attempts = 2
                final_variant_bytes = None

                for attempt in range(1, max_variant_attempts + 1):
                    print(f"  [Försök {attempt}/{max_variant_attempts}]")

                    time.sleep(3)  # Paus innan variant-generering

                    # Generera variant med originalbilder som referens
                    variant_bytes, variant_log = generate_variant(final_image_bytes, variant_angle, original_images)

                    # Printa variant-log
                    for entry in variant_log:
                        print(f"  [{entry}]")

                    # Om generering misslyckades
                    if not variant_bytes:
                        print(f"  [Generering av {variant_angle}-variant misslyckades på försök {attempt}]")
                        if attempt < max_variant_attempts:
                            time.sleep(3)
                        continue

                    # Croppa till 4:5 format
                    print(f"  [Croppar {variant_angle}-variant till 4:5 format...]")
                    variant_bytes = crop_to_4_5_ratio(variant_bytes)

                    # Paus innan validering
                    time.sleep(3)

                    # Validera mot samma originalbilder som användes för generering
                    print(f"  [Validerar {variant_angle}-variant mot {len(original_images)} originalbild(er)...]")

                    # Validera varianten
                    is_valid, validation_report = validate_generated_variant(
                        original_images,
                        variant_bytes,
                        result,
                        variant_angle
                    )

                    # Printa valideringsresultat
                    print(f"  [Validering: {'GODKÄND' if is_valid else 'UNDERKÄND'}]")
                    report_lines = validation_report.split('\n')
                    for line in report_lines[1:]:  # Skippa första raden (APPROVED/REJECTED)
                        if line.strip():
                            print(f"  [{line.strip()}]")

                    # Om varianten är godkänd - spara och avsluta
                    if is_valid:
                        final_variant_bytes = variant_bytes
                        print(f"  [{variant_angle.capitalize()}-variant godkänd på försök {attempt}]")
                        break
                    else:
                        print(f"  [{variant_angle.capitalize()}-variant underkänd på försök {attempt}]")
                        if attempt < max_variant_attempts:
                            print(f"  [Försöker igen...]")
                            time.sleep(3)

                # Spara variant om vi lyckades få en godkänd
                if final_variant_bytes:
                    variant_path = OUTPUT_DIR / f"{image_path.stem}_generated_{variant_angle}.jpg"
                    with open(variant_path, "wb") as f:
                        f.write(final_variant_bytes)
                    print(f"Sparad: {variant_path.name}")
                else:
                    print(f"  Hoppar över {variant_angle}-variant — kunde inte generera godkänd efter {max_variant_attempts} försök")

            # Steg 4: Ladda upp till Shopify (om aktiverat)
            if os.getenv("UPLOAD_TO_SHOPIFY", "false").lower() == "true":
                time.sleep(2)
                print(f"\n--- Laddar upp till Shopify: {image_path.name} ---")

                # Samla alla genererade bilder som finns
                generated_images = []

                # Huvudbild (front)
                main_img = OUTPUT_DIR / f"{image_path.stem}_generated.jpg"
                if main_img.exists():
                    generated_images.append(str(main_img))

                # Varianter (side, back)
                for variant in ["side", "back"]:
                    variant_img = OUTPUT_DIR / f"{image_path.stem}_generated_{variant}.jpg"
                    if variant_img.exists():
                        generated_images.append(str(variant_img))

                # Ladda upp om vi har minst huvudbilden
                if generated_images:
                    try:
                        product_id = upload_product_to_shopify(
                            product_name=image_path.stem,
                            analysis_file=str(OUTPUT_DIR / f"{image_path.stem}_analysis.json"),
                            generated_images=generated_images
                        )

                        if product_id:
                            print(f"✅ Produkt uppladdad till Shopify! (ID: {product_id})")
                        else:
                            print(f"⚠️  Kunde inte ladda upp till Shopify")

                    except Exception as e:
                        print(f"❌ Shopify upload fel: {e}")
                else:
                    print(f"⚠️  Inga genererade bilder att ladda upp")

        else:
            print(f"  Hoppar över {image_path.name} — kunde inte generera godkänd bild efter {max_attempts} försök")

        # Paus mellan produkter för att undvika rate limit
        if i < len(images) - 1:  # Inte efter sista bilden
            time.sleep(5)
            print(f"[Väntar 5s innan nästa produkt för att undvika rate limit...]")


if __name__ == "__main__":
    main()
