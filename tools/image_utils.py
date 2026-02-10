"""
Bildbehandlings-verktyg för att säkerställa korrekt aspect ratio
"""

from PIL import Image
from io import BytesIO


def crop_to_4_5_ratio(image_bytes: bytes) -> bytes:
    """
    Croppar en bild till 4:5 aspect ratio (vertikalt format).

    Exempel på dimensioner:
    - 1024x1280 (4:5)
    - 800x1000 (4:5)

    Args:
        image_bytes: Bilden som bytes

    Returns:
        Croppade bilden som bytes
    """
    # Läs bilden från bytes
    img = Image.open(BytesIO(image_bytes))

    width, height = img.size
    target_ratio = 4 / 5  # 0.8
    current_ratio = width / height

    print(f"  [Original storlek: {width}x{height}, ratio: {current_ratio:.2f}]")

    # Om bilden redan är 4:5 (eller nära), returnera som den är
    if abs(current_ratio - target_ratio) < 0.01:
        print(f"  [Bilden är redan 4:5, ingen crop behövs]")
        return image_bytes

    # Beräkna nya dimensioner för 4:5 crop
    if current_ratio > target_ratio:
        # Bilden är för bred, croppa bredden
        new_width = int(height * target_ratio)
        new_height = height
    else:
        # Bilden är för hög, croppa höjden
        new_width = width
        new_height = int(width / target_ratio)

    # Beräkna crop-box (croppa från mitten)
    left = (width - new_width) // 2
    top = (height - new_height) // 2
    right = left + new_width
    bottom = top + new_height

    # Croppa bilden
    img_cropped = img.crop((left, top, right, bottom))

    print(f"  [Croppade till: {new_width}x{new_height}, ratio: {new_width/new_height:.2f}]")

    # Konvertera tillbaka till bytes
    output = BytesIO()
    img_cropped.save(output, format='JPEG', quality=95)

    return output.getvalue()
