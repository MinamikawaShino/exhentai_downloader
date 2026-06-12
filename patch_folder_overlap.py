import re

with open("src/imgchk/dedup.py", "r", encoding="utf-8") as f:
    content = f.read()

old_logic = """            if max_ratio >= overlap_threshold:
                mtime_a = folder_mtime.get(fa, 0)
                mtime_b = folder_mtime.get(fb, 0)

                if mtime_a <= mtime_b:
                    delete_folder = fa
                    kept_folder = fb
                else:
                    delete_folder = fb
                    kept_folder = fa

                if delete_folder not in to_delete:"""

new_logic = """            if max_ratio >= overlap_threshold:
                mtime_a = folder_mtime.get(fa, 0)
                mtime_b = folder_mtime.get(fb, 0)
                min_total = min(total_a, total_b)
                max_total = max(total_a, total_b)

                if max_total > 0 and (min_total / max_total) >= 0.8:
                    if mtime_a <= mtime_b:
                        delete_folder = fa
                        kept_folder = fb
                    else:
                        delete_folder = fb
                        kept_folder = fa
                else:
                    if total_a < total_b:
                        delete_folder = fa
                        kept_folder = fb
                    elif total_b < total_a:
                        delete_folder = fb
                        kept_folder = fa
                    else:
                        if mtime_a <= mtime_b:
                            delete_folder = fa
                            kept_folder = fb
                        else:
                            delete_folder = fb
                            kept_folder = fa

                if delete_folder not in to_delete:"""

content = content.replace(old_logic, new_logic)

with open("src/imgchk/dedup.py", "w", encoding="utf-8") as f:
    f.write(content)
