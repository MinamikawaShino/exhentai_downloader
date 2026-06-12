import re
with open("src/imgchk/dedup.py", "r", encoding="utf-8") as f:
    content = f.read()

# I accidentally changed folder_overlap return dict to include folder_tail_files, which caused a bug since folder_tail_files is not defined there!
# Let's fix that.
content = content.replace(
    'to_delete[delete_folder] = (kept_folder, pct, folder_tail_files[delete_folder])',
    'to_delete[delete_folder] = (kept_folder, pct)'
)

# And re-add it only for find_ad_images
content = content.replace(
    '''                if delete_folder not in to_delete:
                    pct = round(max_ratio * 100)
                    to_delete[delete_folder] = (kept_folder, pct)
                    if logger:
                        logger.info("Ad overlap: %s <-> %s (%d%%), delete older: %s",
                                    fa, fb, pct, delete_folder)''',
    '''                if delete_folder not in to_delete:
                    pct = round(max_ratio * 100)
                    to_delete[delete_folder] = (kept_folder, pct, folder_tail_files[delete_folder])
                    if logger:
                        logger.info("Ad overlap: %s <-> %s (%d%%), delete older: %s",
                                    fa, fb, pct, delete_folder)'''
)

with open("src/imgchk/dedup.py", "w", encoding="utf-8") as f:
    f.write(content)
