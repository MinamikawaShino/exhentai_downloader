from PIL import Image

Image.MAX_IMAGE_PIXELS = None

import warnings

warnings.filterwarnings(
    "ignore", message="Image size", category=Image.DecompressionBombWarning
)

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".tiff", ".tif", ".svg", ".ico", ".avif", ".heic",
    ".heif", ".eps", ".psd", ".raw", ".cr2", ".nef",
    ".orf", ".sr2", ".dng", ".ppm", ".pgm", ".pbm",
    ".pcx", ".tga", ".pcd", ".dds", ".cur",
}

WEBP_EXTENSIONS = {".webp"}

DEFAULT_THREADS = 12