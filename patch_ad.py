from pathlib import Path
import re

content = Path("src/imgchk/dedup.py").read_text()

# We need to change find_ad_images signature
