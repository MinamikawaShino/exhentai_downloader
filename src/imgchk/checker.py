from pathlib import Path

from PIL import Image, UnidentifiedImageError


def is_corrupted_image(filepath: Path) -> tuple[bool, str]:
    try:
        with Image.open(filepath) as img:
            img.verify()
    except UnidentifiedImageError:
        return True, "Unrecognized image format"
    except Exception as e:
        return True, str(e)

    try:
        with Image.open(filepath) as img:
            img.load()
    except Exception as e:
        return True, f"Load failed: {e}"

    try:
        with Image.open(filepath) as img:
            img.transpose(Image.FLIP_LEFT_RIGHT)
    except Exception as e:
        return True, f"Pixel data error: {e}"

    return False, ""