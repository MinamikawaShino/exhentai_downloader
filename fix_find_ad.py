import re
with open("src/imgchk/dedup.py", "r", encoding="utf-8") as f:
    content = f.read()

# I used total_a and total_b in find_ad_images, but they are not defined there!
# Let's fix that. In find_ad_images, we have folder_total.
# We need to define total_a and total_b.
old = """            if max_ratio >= overlap_threshold:
                mtime_a = folder_mtime.get(fa, 0)
                mtime_b = folder_mtime.get(fb, 0)
                min_total = min(total_a, total_b)
                max_total = max(total_a, total_b)"""

new = """            if max_ratio >= overlap_threshold:
                mtime_a = folder_mtime.get(fa, 0)
                mtime_b = folder_mtime.get(fb, 0)
                total_a = folder_total.get(fa, 0)
                total_b = folder_total.get(fb, 0)
                min_total = min(total_a, total_b)
                max_total = max(total_a, total_b)"""

content = content.replace(old, new, 1) # Only replace the first one (in find_ad_images)

with open("src/imgchk/dedup.py", "w", encoding="utf-8") as f:
    f.write(content)
