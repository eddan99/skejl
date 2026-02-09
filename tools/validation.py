import os
from google import genai
from google.genai import types

from logic.prompts import build_validation_prompt, build_variant_validation_prompt


def validate_generated_image(original_image_path: str, generated_image_raw_data: bytes, analysis: dict) -> tuple:
    """
    HUVUDFUNKTION: Kontrollerar om den genererade bilden matchar originalbilden.

    Parametrar:
      - original_image_path: Sökväg till originalbilden (t.ex. "data/input/mouse.png")
      - generated_image_raw_data: Rå bytes för den genererade bilden
      - analysis: Dict med produktinfo (för extra kontext)

    Returnerar:
      En tuple med två saker:
        - is_valid: True om plagget matchar exakt, False annars
        - validation_report: Text som förklarar varför (för debugging)
    """

    # STEG 1: Hämta API-nyckel från .env-filen
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    # STEG 2: Skapa en klient för att prata med Gemini
    gemini_client = genai.Client(api_key=api_key)

    # STEG 3: Läs originalbilden som rå data
    with open(original_image_path, "rb") as file:
        original_image_raw_data = file.read()

    # Kolla vilken typ av fil originalbilden är
    if original_image_path.endswith(".png"):
        original_image_type = "image/png"
    else:
        original_image_type = "image/jpeg"

    # Den genererade bilden är alltid JPEG (från nano-banana-pro)
    generated_image_type = "image/jpeg"

    # Hämta produktens färg och typ (för extra kontext i prompten)
    color = analysis.get("color", "unknown color")
    garment_type = analysis.get("garment_type", "garment")

    # STEG 4: Bygg prompten som ska jämföra bilderna
    validation_prompt = build_validation_prompt(color, garment_type)

    # STEG 5: Skicka båda bilderna + prompten till Gemini
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            # Först: originalbilden
            types.Part(inline_data=types.Blob(mime_type=original_image_type, data=original_image_raw_data)),
            # Sen: genererade bilden
            types.Part(inline_data=types.Blob(mime_type=generated_image_type, data=generated_image_raw_data)),
            # Sist: prompten
            types.Part(text=validation_prompt)
        ]
    )

    # STEG 6: Tolka Geminis svar
    result_text = response.text.strip()

    # Kolla om svaret börjar med "APPROVED"
    if result_text.startswith("APPROVED"):
        return True, result_text
    else:
        return False, result_text


def validate_generated_variant(original_image_paths: list, generated_variant_raw_data: bytes, analysis: dict, view_angle: str) -> tuple:
    """
    HUVUDFUNKTION: Kontrollerar om en genererad variant (side/back) matchar originalbilderna.

    Parametrar:
      - original_image_paths: Lista med sökvägar till originalbilder (1 eller flera, t.ex. ["data/input/yourturn.jpg"] eller ["data/input/yourturn_front.jpg", "data/input/yourturn_back.jpg"])
      - generated_variant_raw_data: Rå bytes för den genererade varianten
      - analysis: Dict med produktinfo (för extra kontext)
      - view_angle: "side" eller "back" - vilken vinkel som genererats

    Returnerar:
      En tuple med två saker:
        - is_valid: True om varianten matchar originalbilderna, False annars
        - validation_report: Text som förklarar varför (för debugging)
    """

    # STEG 1: Hämta API-nyckel från .env-filen
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    # STEG 2: Skapa en klient för att prata med Gemini
    gemini_client = genai.Client(api_key=api_key)

    # STEG 3: Läs alla originalbilder som rå data
    original_images_data = []
    for image_path in original_image_paths:
        with open(image_path, "rb") as file:
            original_image_raw_data = file.read()

        # Kolla vilken typ av fil det är
        if image_path.endswith(".png"):
            image_type = "image/png"
        else:
            image_type = "image/jpeg"

        original_images_data.append((original_image_raw_data, image_type))

    # Den genererade varianten är alltid JPEG (från nano-banana-pro)
    generated_image_type = "image/jpeg"

    # Hämta produktens färg och typ (för extra kontext i prompten)
    color = analysis.get("color", "unknown color")
    garment_type = analysis.get("garment_type", "garment")

    # STEG 4: Bygg prompten
    validation_prompt = build_variant_validation_prompt(color, garment_type, view_angle)

    # STEG 5: Bygg contents-listan med alla bilder
    contents = []

    # Lägg till alla originalbilder först
    for original_data, mime_type in original_images_data:
        contents.append(types.Part(inline_data=types.Blob(mime_type=mime_type, data=original_data)))

    # Lägg till den genererade varianten
    contents.append(types.Part(inline_data=types.Blob(mime_type=generated_image_type, data=generated_variant_raw_data)))

    # Lägg till prompten sist
    contents.append(types.Part(text=validation_prompt))

    # STEG 6: Skicka allt till Gemini
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents
    )

    # STEG 7: Tolka Geminis svar
    result_text = response.text.strip()

    # Kolla om svaret börjar med "APPROVED"
    if result_text.startswith("APPROVED"):
        return True, result_text
    else:
        return False, result_text
