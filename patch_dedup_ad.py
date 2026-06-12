with open("src/imgchk/dedup.py", "r", encoding="utf-8") as f:
    content = f.read()

# Modify scan_ad_duplicates signature
content = content.replace(
    """def scan_ad_duplicates(
    source_dir: Path,
    folder_dedup_dir: Path,
    overlap_threshold: float = 0.5,
    threads: int = 12,
    logger: logging.Logger = None,
):""",
    """def scan_ad_duplicates(
    source_dir: Path,
    folder_dedup_dir: Path,
    overlap_threshold: float = 0.5,
    ad_scan_count: int = 6,
    threads: int = 12,
    logger: logging.Logger = None,
):"""
)

# Modify find_ad_images call inside scan_ad_duplicates
content = content.replace(
    'to_delete = find_ad_images(source_dir, overlap_threshold, threads, logger)',
    'to_delete = find_ad_images(source_dir, overlap_threshold, ad_scan_count, threads, logger)'
)

# Modify find_ad_images signature
content = content.replace(
    """def find_ad_images(
    source_dir: Path,
    overlap_threshold: float = 0.5,
    threads: int = 12,
    logger: logging.Logger = None,
):""",
    """def find_ad_images(
    source_dir: Path,
    overlap_threshold: float = 0.5,
    ad_scan_count: int = 6,
    threads: int = 12,
    logger: logging.Logger = None,
):"""
)

# Modify find_ad_images inside
content = content.replace('last_n = 6', 'last_n = ad_scan_count')

# Add move_ad_images_to_dedup function right before scan_ad_duplicates
new_func = """
def move_ad_images_to_dedup(
    folder_rel: str,
    kept_folder: str,
    overlap_pct: int,
    tail_files: list[Path],
    source_dir: Path,
    folder_dedup_dir: Path,
    logger: logging.Logger = None,
) -> tuple[int, int]:
    moved = 0
    failed = 0
    dest_folder = folder_dedup_dir / folder_rel

    for src in tail_files:
        if not src.exists():
            continue
        try:
            rel = src.relative_to(source_dir)
            dest = folder_dedup_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest = dest.parent / f"{dest.stem}_{int(datetime.now().timestamp())}{dest.suffix}"
            shutil.move(str(src), str(dest))
            moved += 1
        except Exception as e:
            failed += 1
            if logger:
                logger.error("Ad image move failed: %s -> %s", src, e)

    if logger and moved > 0:
        logger.info("Ad images moved from %s (%d%% overlap with %s): %d files", folder_rel, overlap_pct, kept_folder, moved)

    return moved, failed

"""

# We need to change the return type of find_ad_images to include the tail_files to delete
# The return dict of find_ad_images was: to_delete[delete_folder] = (kept_folder, pct)
# We will change it to: to_delete[delete_folder] = (kept_folder, pct, folder_tail_files[delete_folder])

# In find_ad_images, let's capture folder_tail_files
content = content.replace(
    'folder_tail_hashes: dict[str, set[str]] = {}',
    'folder_tail_hashes: dict[str, set[str]] = {}\n    folder_tail_files: dict[str, list[Path]] = {}'
)

content = content.replace(
    'folder_tail_hashes[folder] = hash_set',
    'folder_tail_hashes[folder] = hash_set\n        folder_tail_files[folder] = tail'
)

content = content.replace(
    'to_delete[delete_folder] = (kept_folder, pct)',
    'to_delete[delete_folder] = (kept_folder, pct, folder_tail_files[delete_folder])'
)

# Replace scan_ad_duplicates logic
old_scan_loop = """    for folder_rel, (kept, pct) in sorted(to_delete.items()):
        if is_interrupted():
            break
        ok, _ = move_folder_to_dedup(
            folder_rel, kept, pct, source_dir, folder_dedup_dir, logger
        )
        if ok:
            moved += 1
        else:
            failed += 1"""

new_scan_loop = """    for folder_rel, (kept, pct, tail_files) in sorted(to_delete.items()):
        if is_interrupted():
            break
        m, f = move_ad_images_to_dedup(
            folder_rel, kept, pct, tail_files, source_dir, folder_dedup_dir, logger
        )
        moved += m
        failed += f"""

content = content.replace(old_scan_loop, new_scan_loop)

# insert the move_ad_images_to_dedup function right before scan_ad_duplicates
content = content.replace("def scan_ad_duplicates(", new_func + "def scan_ad_duplicates(")

with open("src/imgchk/dedup.py", "w", encoding="utf-8") as f:
    f.write(content)
