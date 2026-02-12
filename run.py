import json
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.vision_tool import (
    analyze_product_image,
    extract_product_features,
    generate_product_description
)
from tools.image_gen_tool import generate_product_image, generate_variant
from tools.validation import validate_generated_image, validate_generated_variant
from tools.shopify_tool import upload_product_to_shopify
from tools.image_utils import crop_to_4_5_ratio
from tools.ml.ml_predictor import predict_image_settings
from tools.ml.scenario_generator import generate_photography_scenario
from logic.agent import multi_agent_debate
import os

INPUT_DIR = PROJECT_ROOT / "data" / "input"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

def find_all_product_images(base_image_path: Path) -> list:
    stem = base_image_path.stem
    parent = base_image_path.parent  
    ext = base_image_path.suffix  

    found_images = [str(base_image_path)]

    for variant in ["_back", "_side"]:
        variant_path = parent / f"{stem}{variant}{ext}"
        if variant_path.exists():
            found_images.append(str(variant_path))

    return found_images


def main():
    use_ml = os.getenv("USE_ML_PREDICTION", "false").lower() == "true"

    if use_ml:
        print("ML-DRIVEN MODE ENABLED")
    else:
        print("LEGACY MODE")
        
    all_images = sorted([f for f in INPUT_DIR.iterdir() if f.suffix in ['.png', '.jpg']])

    images = [img for img in all_images if not ("_back" in img.stem or "_side" in img.stem)]

    if not images:
        print("No images found in data/input/")
        return

    for i, image_path in enumerate(images):
        print(f"Processing: {image_path.name}")

        if use_ml:
            print("\n[1/5] Extracting product features...")
            features = extract_product_features(str(image_path))
            print(f"  Garment: {features.get('garment_type')} ({features.get('color')}, {features.get('fit')})")
            print(f"  Gender: {features.get('gender')}")
            time.sleep(3)

            print("\n[2/5] ML Prediction...")
            ml_prediction = predict_image_settings(
                features['garment_type'],
                features['color'],
                features['fit'],
                features['gender']
            )
            print(f"  Predicted conversion: {ml_prediction['predicted_conversion_rate']*100:.2f}%")
            print(f"  Settings: {ml_prediction['image_settings']['style']}, {ml_prediction['image_settings']['lighting']}")
            time.sleep(3)

            print("\n[3/5] Multi-agent debate...")
            debate_result = multi_agent_debate(
                ml_prediction,
                features
            )
            print(f"  Consensus: {debate_result['consensus_type']}")
            print(f"  Final settings: {debate_result['final_image_settings']['style']}, {debate_result['final_image_settings']['lighting']}")
            time.sleep(3)

            print("\n[4/5] Generating photography scenario")
            photography_scenario = generate_photography_scenario(
                debate_result['final_image_settings'],
                features
            )
            print("Scenario generated")

            print("\n[5/5] Generating product description")
            description = generate_product_description(
                features,
                photography_scenario
            )
            print(f"  Description: {description[:100]}...")
            
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
            print("\n[Gemini Analysis]")
            result = analyze_product_image(str(image_path))
            print(f"  Garment: {result.get('garment_type')} ({result.get('color')}, {result.get('fit')})")

        print("ANALYSIS RESULT:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        OUTPUT_DIR.mkdir(exist_ok=True)
        output_file = OUTPUT_DIR / f"{image_path.stem}_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved: {output_file.name}")

        time.sleep(3)

        print(f"Generating image: {image_path.name}")

        max_attempts = 2
        final_image_bytes = None

        for attempt in range(1, max_attempts + 1):
            print(f"Trials {attempt}/{max_attempts}")

            image_bytes, gen_log = generate_product_image(str(image_path), result)

            for entry in gen_log:
                print(f"  [{entry}]")

            if not image_bytes:
                print(f"  Generation failed at {attempt}]")
                if attempt < max_attempts:
                    time.sleep(3)
                continue

            image_bytes = crop_to_4_5_ratio(image_bytes)
            
            time.sleep(3)

            print("Validating image")
            is_valid, validation_report = validate_generated_image(
                str(image_path),
                image_bytes,
                result
            )
            
            print(f"Validering: {'Approved' if is_valid else 'Denied'}")
            report_lines = validation_report.split('\n')
            for line in report_lines[1:]:
                if line.strip():
                    print(f"  [{line.strip()}]")

            if is_valid:
                final_image_bytes = image_bytes
                print(f"Image approved on attempt {attempt}")
                break
            else:
                print(f"Image denied on attempt {attempt}")
                if attempt < max_attempts:
                    print("Trying again")
                    time.sleep(3)

        if final_image_bytes:
            generated_image_path = OUTPUT_DIR / f"{image_path.stem}_generated.jpg"
            with open(generated_image_path, "wb") as f:
                f.write(final_image_bytes)
            print(f"Saved: {generated_image_path.name}")

            original_images = find_all_product_images(image_path)

            for variant_angle in ["side", "back"]:
                print(f"Generating {variant_angle}-variant: {image_path.name}")

                max_variant_attempts = 2
                final_variant_bytes = None

                for attempt in range(1, max_variant_attempts + 1):
                    print(f"Attempt {attempt}/{max_variant_attempts}")

                    time.sleep(3)

                    variant_bytes, variant_log = generate_variant(final_image_bytes, variant_angle, original_images)

                    for entry in variant_log:
                        print(f"  [{entry}]")

                    if not variant_bytes:
                        print(f"Generation of {variant_angle}variant failed on attempt {attempt}")
                        if attempt < max_variant_attempts:
                            time.sleep(3)
                        continue

                    variant_bytes = crop_to_4_5_ratio(variant_bytes)

                    time.sleep(3)

                    print(f"Validating {variant_angle}-variant against {len(original_images)} original image(s)")

                    is_valid, validation_report = validate_generated_variant(
                        original_images,
                        variant_bytes,
                        result,
                        variant_angle
                    )
                    print(f"Validation: {'APPROVED' if is_valid else 'DENIED'}")
                    report_lines = validation_report.split('\n')
                    for line in report_lines[1:]:
                        if line.strip():
                            print(f"  [{line.strip()}]")

                    if is_valid:
                        final_variant_bytes = variant_bytes
                        print(f"{variant_angle.capitalize()}-variant approved on attempt {attempt}")
                        break
                    else:
                        print(f"  [{variant_angle.capitalize()}-variant denied on attempt {attempt}]")
                        if attempt < max_variant_attempts:
                            print("Trying again")
                            time.sleep(3)

                if final_variant_bytes:
                    variant_path = OUTPUT_DIR / f"{image_path.stem}_generated_{variant_angle}.jpg"
                    with open(variant_path, "wb") as f:
                        f.write(final_variant_bytes)
                    print(f"Saved: {variant_path.name}")
                else:
                    print(f"Skipping {variant_angle}variant. could not generate approved variant after {max_variant_attempts} attempts")

            if os.getenv("UPLOAD_TO_SHOPIFY", "false").lower() == "true":
                time.sleep(2)
                print(f"Uploading {image_path.name} to Shopify")

                generated_images = []

                main_img = OUTPUT_DIR / f"{image_path.stem}_generated.jpg"
                if main_img.exists():
                    generated_images.append(str(main_img))

                for variant in ["side", "back"]:
                    variant_img = OUTPUT_DIR / f"{image_path.stem}_generated_{variant}.jpg"
                    if variant_img.exists():
                        generated_images.append(str(variant_img))

                if generated_images:
                    try:
                        product_id = upload_product_to_shopify(
                            product_name=image_path.stem,
                            analysis_file=str(OUTPUT_DIR / f"{image_path.stem}_analysis.json"),
                            generated_images=generated_images
                        )

                        if product_id:
                            print(f"Product uploaded to Shopify with ID: {product_id}")
                        else:
                            print("Could not upload product to Shopify")
                    except Exception as e:
                        print(f"Shopify upload error: {e}")
                else:
                    print(f"No generated images to upload for {image_path.name}")

        else:
            print(f"Skipping {image_path.name} — Could not generate image after {max_attempts} attempts")

        if i < len(images) - 1:
            time.sleep(5)
            print("Waiting 5 seconds to avoid rate limit.")

if __name__ == "__main__":
    main()
