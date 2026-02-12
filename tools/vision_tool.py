import os
import json
from pathlib import Path
from google import genai
from google.genai import types

from logic.prompts import (
    build_analysis_prompt,
    build_feature_extraction_prompt,
    build_description_prompt
)
from tools.taxonomy import normalize_product_features

# Var finns products.json? (i data/input/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_JSON = PROJECT_ROOT / "data" / "input" / "products.json"


def load_product_data(image_path: str) -> dict:
    """
    Läser products.json och hittar produkten som matchar bildens filnamn.

    Exempel:
      - Bilden heter "mouse.png"
      - I products.json finns en produkt med "image": "mouse.jpg"
      - Vi matchar på "mouse" (utan .png/.jpg)
    """
    # Path().stem tar bort filändelsen: "mouse.png" → "mouse"
    filename_without_extension = Path(image_path).stem

    # Öppna products.json och läs alla produkter
    with open(PRODUCTS_JSON, "r", encoding="utf-8") as file:
        all_products = json.load(file)

    # Leta igenom alla produkter
    for product in all_products:
        product_filename = Path(product["image"]).stem

        if product_filename == filename_without_extension:
            return product  # Hittad! Returnera produktens metadata

    # Om vi kommer hit hittades ingen produkt
    raise ValueError(f"Ingen produkt hittades för: {image_path}")


def parse_gemini_response(gemini_text: str) -> dict:
    """
    Gemini svarar med text. Denna funktion gör om texten till en Python-dict.

    Problem: Gemini lägger ibland till ```json ... ``` runt JSON:en
    Lösning: Ta bort första och sista raden om de innehåller ```
    """
    text = gemini_text.strip()

    # Kolla om svaret börjar med ``` (markdown code-fence)
    if text.startswith("```"):
        # Dela upp i rader: ["```json", "{...}", "```"]
        lines = text.split("\n")
        # Ta bort första och sista raden: bara "{...}" kvar
        text = "\n".join(lines[1:-1])

    # Försök göra om text till Python-dict
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Om det misslyckas, returnera ett error-objekt istället
        return {"error": "Failed to parse JSON", "raw": gemini_text}


def analyze_product_image(image_path: str, brand_identity: str = None) -> dict:
    """
    HUVUDFUNKTION: Skickar bild + metadata till Gemini för analys.

    Parametrar:
      - image_path: Sökväg till bildfilen (t.ex. "data/input/mouse.png")
      - brand_identity: Valfri text om varumärkets ton (None = använd default)

    Returnerar:
      En dict med: gender, garment_type, fit, photography_scenario, description
    """

    # STEG 1: Hämta API-nyckel från .env-filen
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    # STEG 2: Skapa en klient för att prata med Gemini
    gemini_client = genai.Client(api_key=api_key)

    # STEG 3: Läs bildfilen som rå data (binär data = 0:or och 1:or)
    # "rb" betyder: r = read (läs), b = binary (binär/rå data)
    # "as file" betyder: kalla filen för "file" medan den är öppen
    with open(image_path, "rb") as file:
        image_raw_data = file.read()  # Läs hela bilden som rå bytes

    # Kolla om bilden är PNG eller JPEG (behövs för API:et)
    if image_path.endswith(".png"):
        image_type = "image/png"
    else:
        image_type = "image/jpeg"

    # STEG 4: Hämta produktens metadata från products.json
    product_metadata = load_product_data(image_path)

    # STEG 5: Bygg prompten som ska skickas till Gemini
    prompt_text = build_analysis_prompt(product_metadata, brand_identity)

    # STEG 6: Skicka bilden + prompten till Gemini
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            # Först: bilden (som rå data)
            types.Part(inline_data=types.Blob(mime_type=image_type, data=image_raw_data)),
            # Sen: prompten (som text)
            types.Part(text=prompt_text)
        ]
    )

    # STEG 7: Gör om Geminis textsvar till en Python-dict
    return parse_gemini_response(response.text)


def extract_product_features(image_path: str) -> dict:
    """
    NY FUNKTION för ML-driven flow: Extraherar produkt-features från bild.

    Skillnad mot analyze_product_image():
    - Genererar INTE photography_scenario (det görs senare av ML + debate)
    - Genererar INTE description (görs senare med generate_product_description)
    - Normaliserar features med taxonomy.py för konsistens

    Returnerar:
        Dict med: image, art_nr, color, fit, composition, gender, garment_type, title
    """
    # Hämta API-nyckel
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    # Skapa Gemini-klient
    gemini_client = genai.Client(api_key=api_key)

    # Läs bildfilen
    with open(image_path, "rb") as file:
        image_raw_data = file.read()

    # Bestäm bildtyp
    if image_path.endswith(".png"):
        image_type = "image/png"
    else:
        image_type = "image/jpeg"

    # Hämta produktmetadata
    product_metadata = load_product_data(image_path)

    # Bygg feature extraction prompt (UTAN photography_scenario)
    prompt_text = build_feature_extraction_prompt(product_metadata)

    # Skicka till Gemini
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part(inline_data=types.Blob(mime_type=image_type, data=image_raw_data)),
            types.Part(text=prompt_text)
        ]
    )

    # Parse svar
    features = parse_gemini_response(response.text)

    # Normalisera features för konsistens med conversion_db
    try:
        features = normalize_product_features(features)
    except ValueError as e:
        print(f"Warning: Normalization failed: {e}")
        # Continue without normalization if it fails

    return features


def generate_product_description(
    product_features: dict,
    photography_scenario: dict,
    brand_identity: str = None
) -> str:
    """
    NY FUNKTION för ML-driven flow: Genererar produktbeskrivning.

    Anropas EFTER att photography_scenario har finaliserats av ML + debate.

    Parametrar:
        product_features: Features från extract_product_features()
        photography_scenario: Final scenario från scenario_generator
        brand_identity: Valfri varumärkesidentitet

    Returnerar:
        Produktbeskrivning som string
    """
    # Hämta API-nyckel
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    # Skapa Gemini-klient
    gemini_client = genai.Client(api_key=api_key)

    # Bygg description prompt
    prompt_text = build_description_prompt(
        product_features,
        photography_scenario,
        brand_identity
    )

    # Skicka till Gemini (text-only, ingen bild behövs)
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_text
    )

    # Returnera beskrivningen direkt som text
    return response.text.strip()
