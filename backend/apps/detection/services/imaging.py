"""Shrink an uploaded photo before the models see it.

A phone photo is often 4000x3000 pixels (8+ MB). YOLO only looks at ~640 px, but decoding the full photo takes
tens of MB of RAM and then every resize makes more copies. On a 512 MB free server that is what pushes the process
over its limit. Keeping the longest side at 1280 px costs nothing in accuracy and saves memory and time.

Because the shrunk file is the one the detector reads AND the one the website shows, the boxes still line up.
"""
import logging

from PIL import Image, ImageOps

log = logging.getLogger("cropguard.imaging")

MAX_SIDE = 1280


def shrink_in_place(path, max_side: int = MAX_SIDE) -> None:
    """Resize (and bake in the camera rotation of) the photo at `path`. Never raises: a check must not fail on this."""
    try:
        with Image.open(path) as im:
            fmt = im.format
            im.draft("RGB", (max_side, max_side))   # JPEG only: decodes at reduced size, which is the big saving
            rotated = im.getexif().get(274, 1) not in (None, 1)   # 274 = EXIF orientation
            if max(im.size) <= max_side and not rotated:
                return
            photo = ImageOps.exif_transpose(im)
            photo.thumbnail((max_side, max_side))
            if fmt == "JPEG" or photo.mode not in ("RGB", "L", "RGBA"):
                photo = photo.convert("RGB")
            photo.save(path, format=fmt if fmt in ("JPEG", "PNG", "WEBP") else "JPEG", **({"quality": 90} if fmt != "PNG" else {}))
    except Exception:
        log.warning("could not shrink %s; using it as uploaded", path, exc_info=True)
