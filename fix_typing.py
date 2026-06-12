import re
with open("src/imgchk/dedup.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'to_delete: dict[str, tuple[str, int]] = {}',
    'to_delete: dict[str, tuple[str, int, list[Path]]] = {}',
    1 # only the first one which is in find_ad_images
)

with open("src/imgchk/dedup.py", "w", encoding="utf-8") as f:
    f.write(content)
