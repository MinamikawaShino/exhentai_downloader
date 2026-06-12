import sys
import tempfile
import os
import shutil
from pathlib import Path
from src.imgchk.dedup import scan_ad_duplicates, scan_folder_duplicates, find_folder_overlaps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

def create_image(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

with tempfile.TemporaryDirectory() as tmpdir:
    src = Path(tmpdir) / "src"
    dedup = Path(tmpdir) / "dedup"
    src.mkdir()
    dedup.mkdir()

    # folder A: 10 images
    folder_a = src / "A"
    for i in range(10):
        create_image(folder_a / f"img_{i:02d}.jpg", f"content_a_{i}")

    # folder B: 8 images, last 6 are same as A's last 6
    folder_b = src / "B"
    for i in range(2):
        create_image(folder_b / f"img_{i:02d}.jpg", f"content_b_{i}")
    for i in range(2, 8):
        # same content as A's img_04 to img_09
        create_image(folder_b / f"img_{i:02d}.jpg", f"content_a_{i+2}")

    # Let's adjust mtime
    os.utime(folder_a, (100, 100))
    os.utime(folder_b, (200, 200))

    print("Files in src before ad scan:")
    for root, dirs, files in os.walk(src):
        for f in files:
            print(f"  {Path(root).name}/{f}")

    # Run scan_ad_duplicates
    res = scan_ad_duplicates(src, dedup, overlap_threshold=0.5, ad_scan_count=6, threads=1, logger=logger)
    print("Result:", res)

    print("Files in dedup after ad scan:")
    for root, dirs, files in os.walk(dedup):
        for f in files:
            print(f"  {Path(root).name}/{f}")

    print("Files in src after ad scan:")
    for root, dirs, files in os.walk(src):
        for f in files:
            print(f"  {Path(root).name}/{f}")
