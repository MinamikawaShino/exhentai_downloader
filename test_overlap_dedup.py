import sys
import tempfile
import os
from pathlib import Path
from src.imgchk.dedup import find_folder_overlaps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

def create_image(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

with tempfile.TemporaryDirectory() as tmpdir:
    src = Path(tmpdir) / "src"
    src.mkdir()

    # case 1: count A = 10, count B = 20, same files. diff count -> delete A
    folder_a = src / "A"
    folder_b = src / "B"
    for i in range(10):
        create_image(folder_a / f"img_{i:02d}.jpg", f"content_{i}")
        create_image(folder_b / f"img_{i:02d}.jpg", f"content_{i}")
    for i in range(10, 20):
        create_image(folder_b / f"img_{i:02d}.jpg", f"content_{i}")

    os.utime(folder_a, (200, 200))
    os.utime(folder_b, (100, 100))

    overlaps = find_folder_overlaps(src, logger=logger)
    print("case 1 overlap (should delete A, 50% overlap, different counts):", overlaps)

    # case 2: count A = 18, count B = 20. similar count -> delete earliest
    # we need to re-create to test it correctly, or we can just add 8 more files to A
    for i in range(10, 18):
        create_image(folder_a / f"img_{i:02d}.jpg", f"content_{i}")

    os.utime(folder_a, (200, 200))
    os.utime(folder_b, (100, 100))

    overlaps = find_folder_overlaps(src, logger=logger)
    print("case 2 overlap (should delete B, earliest, similar counts):", overlaps)
