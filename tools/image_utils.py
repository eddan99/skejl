from PIL import Image
from io import BytesIO

def crop_to_4_5_ratio(image_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(image_bytes))
    width, height = img.size
    target_ratio = 4 / 5
    current_ratio = width / height
    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        new_height = height
    else:
        new_width = width
        new_height = int(width / target_ratio)
    left = (width - new_width) // 2
    top = (height - new_height) // 2
    right = left + new_width
    bottom = top + new_height
    img_cropped = img.crop((left, top, right, bottom))
    output = BytesIO()
    img_cropped.save(output, format='JPEG', quality=95)
    return output.getvalue()
