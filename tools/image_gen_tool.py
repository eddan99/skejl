import os
from google import genai
from google.genai import types

from logic.prompts import build_image_gen_prompt, build_variant_prompt


def generate_product_image(reference_image_path: str, analysis: dict) -> tuple:
    """
    HUVUDFUNKTION: Skickar originalbilden + scenario till nano-banana-pro för att generera ny bild.

    Parametrar:
      - reference_image_path: Sökväg till originalbilden (t.ex. "data/input/mouse.png")
      - analysis: Dict med photography_scenario från Gemini (hur bilden ska se ut)

    Returnerar:
      En tuple med två saker:
        - image_raw_data: Rå bytes för den genererade bilden (eller None om misslyckades)
        - decision_log: Lista med beslut som agenten tog (för debugging)
    """

    # STEG 1: Hämta API-nyckel från .env-filen
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    # STEG 2: Skapa en klient för att prata med nano-banana-pro
    nano_banana_client = genai.Client(api_key=api_key)

    # Skapa en logg för att spåra vad agenten gör
    decision_log = []

    # STEG 3: Läs originalbilden som rå data
    # "rb" betyder: r = read (läs), b = binary (binär/rå data)
    with open(reference_image_path, "rb") as file:
        original_image_raw_data = file.read()

    # Kolla om bilden är PNG eller JPEG (behövs för API:et)
    if reference_image_path.endswith(".png"):
        image_type = "image/png"
    else:
        image_type = "image/jpeg"

    # STEG 4: Bygg prompten (instruktioner för hur den nya bilden ska se ut)
    prompt_text = build_image_gen_prompt(analysis)
    decision_log.append("Beslut: Skickar referensbild + prompt till nano-banana-pro")

    # STEG 5: Skicka originalbilden + prompt till nano-banana-pro
    # response_modalities = ["image"] betyder att vi BARA vill ha en BILD tillbaka (ingen text!)
    response = nano_banana_client.models.generate_content(
        model="nano-banana-pro-preview",
        contents=[
            # Först: originalbilden (som rå data)
            types.Part(inline_data=types.Blob(mime_type=image_type, data=original_image_raw_data)),
            # Sen: prompten (instruktioner)
            types.Part(text=prompt_text)
        ],
        config=types.GenerateContentConfig(
            response_modalities=["image"]  # BARA bild - tvingar modellen att returnera en bild
        )
    )

    # STEG 6: Kolla om svaret blockerades (safety filter)
    # response.parts = alla delar av svaret (kan vara text, bild, etc.)
    if not response.parts:
        # Ingen data i svaret = blockerad av safety filter
        feedback = getattr(response, "prompt_feedback", None)
        reason = str(feedback) if feedback else "okänd anledning"
        decision_log.append(f"Blockerad: {reason}")
        decision_log.append("Beslut: Referensbild krävs och kan inte tas bort. Hoppar över denna produkt.")
        return None, decision_log

    # STEG 7: Hämta den genererade bilden från svaret
    for part in response.parts:
        # Kolla om denna del innehåller bildata
        # hasattr() = "har objektet detta attribut?"
        if hasattr(part, "inline_data") and part.inline_data and hasattr(part.inline_data, "data"):
            # Hittad! Bilden finns i part.inline_data.data
            decision_log.append("Resultat: Bild genererad framgångsrikt")
            return part.inline_data.data, decision_log

    # Om vi kommer hit hittades ingen bild i svaret
    decision_log.append("Fel: Ingen bild i svaret")
    decision_log.append("Beslut: Hoppar över denna produkt.")
    return None, decision_log


def generate_variant(approved_image_raw_data: bytes, view_angle: str, original_image_paths: list = None) -> tuple:
    """
    HUVUDFUNKTION: Genererar en variant av en redan godkänd bild (sidovy eller bakvy).

    Parametrar:
      - approved_image_raw_data: Rå bytes för den godkända bilden (används som referens för person/miljö)
      - view_angle: "side" eller "back" - vilken vinkel vi vill ha
      - original_image_paths: Lista med sökvägar till originalbilder (för att veta hur plagget ser ut från olika vinklar)

    Returnerar:
      En tuple med två saker:
        - image_raw_data: Rå bytes för den genererade varianten (eller None om misslyckades)
        - decision_log: Lista med beslut som agenten tog
    """

    # STEG 1: Hämta API-nyckel från .env-filen
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY saknas i .env")

    # STEG 2: Skapa en klient för att prata med nano-banana-pro
    nano_banana_client = genai.Client(api_key=api_key)

    # Skapa en logg för att spåra vad agenten gör
    decision_log = []

    # STEG 3: Bygg prompten för varianten
    prompt_text = build_variant_prompt(view_angle)

    # Lägg till info om originalbilder i loggen
    if original_image_paths and len(original_image_paths) > 1:
        decision_log.append(f"Beslut: Genererar {view_angle}-variant med {len(original_image_paths)} originalbilder som referens")
    else:
        decision_log.append(f"Beslut: Genererar {view_angle}-variant baserat på godkänd bild")

    # STEG 4: Bygg contents-listan med alla bilder
    contents = []

    # Först: Lägg till alla originalbilder (om de finns)
    if original_image_paths:
        for img_path in original_image_paths:
            with open(img_path, "rb") as file:
                img_data = file.read()

            # Kolla filtyp
            if img_path.endswith(".png"):
                img_type = "image/png"
            else:
                img_type = "image/jpeg"

            contents.append(types.Part(inline_data=types.Blob(mime_type=img_type, data=img_data)))

    # Sen: den godkända bilden (person + miljö)
    contents.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=approved_image_raw_data)))

    # Sist: prompten
    contents.append(types.Part(text=prompt_text))

    # STEG 5: Skicka allt till nano-banana-pro
    response = nano_banana_client.models.generate_content(
        model="nano-banana-pro-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["image"]  # BARA bild
        )
    )

    # STEG 5: Kolla om svaret blockerades
    if not response.parts:
        feedback = getattr(response, "prompt_feedback", None)
        reason = str(feedback) if feedback else "okänd anledning"
        decision_log.append(f"Blockerad: {reason}")
        decision_log.append(f"Beslut: Hoppar över {view_angle}-variant.")
        return None, decision_log

    # STEG 6: Hämta den genererade bilden
    for part in response.parts:
        if hasattr(part, "inline_data") and part.inline_data and hasattr(part.inline_data, "data"):
            decision_log.append(f"Resultat: {view_angle.capitalize()}-variant genererad framgångsrikt")
            return part.inline_data.data, decision_log

    # Om vi kommer hit hittades ingen bild
    decision_log.append("Fel: Ingen bild i svaret")
    decision_log.append(f"Beslut: Hoppar över {view_angle}-variant.")
    return None, decision_log
