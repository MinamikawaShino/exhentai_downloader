import sys
import shutil
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .checker import is_corrupted_image
from .converter import convert_webp_to_png
from .utils import (
    is_image_file,
    is_webp_file,
    is_interrupted,
    reset_interrupt,
    reset_checked,
    increment_checked,
    get_checked,
    print_lock,
    collect_image_files,
    format_progress,
)


def process_file(
    filepath: Path,
    source_dir: Path,
    error_dir: Path,
    convert_webp: bool,
    white_bg: bool,
) -> dict:
    result = {
        "path": filepath,
        "action": "",
        "corrupted": False,
        "reason": "",
        "engine": "",
    }

    if convert_webp and is_webp_file(filepath):
        success, engine, err = convert_webp_to_png(filepath, white_bg)

        if success:
            png_path = filepath.with_suffix(".png")
            if engine == "DeleteWebP_AlreadyHadPNG":
                result["action"] = "webp_deleted_existing_png"
                result["engine"] = engine
            else:
                is_bad, bad_reason = is_corrupted_image(png_path)
                if is_bad:
                    result["action"] = "webp_converted_but_png_corrupted"
                    result["corrupted"] = True
                    result["reason"] = bad_reason
                    result["engine"] = engine
                else:
                    result["action"] = "webp_converted"
                    result["engine"] = engine
        else:
            result["action"] = "webp_convert_failed"
            result["corrupted"] = True
            result["reason"] = err
    else:
        is_bad, reason = is_corrupted_image(filepath)
        if is_bad:
            result["corrupted"] = True
            result["reason"] = reason
            result["action"] = "corrupted"
        else:
            result["action"] = "normal"

    return result


def _make_cache_entry(filepath: Path, action: str, engine: str = ""):
    try:
        st = filepath.stat()
        size, mtime = st.st_size, st.st_mtime
    except OSError:
        size, mtime = 0, 0
    status = "normal" if action == "normal" else (
        "webp_converted" if action == "webp_converted" else "corrupted"
    )
    return (str(filepath), None, size, mtime, status, None, engine or None)


def scan_directory(
    source_dirs: list[Path],
    error_dir: Path,
    log_path: Path,
    threads: int = 12,
    convert_webp: bool = False,
    white_bg: bool = False,
    progress_callback=None,
    db=None,
    db_skip: bool = False,
):
    logger = logging.getLogger(f"img_scanner_{id(source_dirs[0]) if source_dirs else 0}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.info("=" * 60)
    logger.info("Scan directories: %s (threads: %d)", [str(d) for d in source_dirs], threads)
    logger.info("Corrupted files will be moved to: %s", error_dir)
    if convert_webp:
        logger.info("WebP to PNG: enabled (white_bg: %s)", "yes" if white_bg else "no")
    if db and not db_skip:
        logger.info("DB cache: enabled")
    logger.info("=" * 60)

    all_files = []
    for sd in source_dirs:
        all_files.extend(collect_image_files(sd))
    total_discovered = len(all_files)
    webp_count = sum(1 for f in all_files if is_webp_file(f))

    cache_map = {}
    cached_skipped = 0
    if db and not db_skip:
        cache_map = {}
        for sd in source_dirs:
            cache_map.update(db.load_cache_map(str(sd)))
        files_to_scan = []
        for f in all_files:
            fp = str(f)
            if fp in cache_map:
                cached_size, cached_mtime = cache_map[fp]
                try:
                    st = f.stat()
                    if st.st_size == cached_size and st.st_mtime == cached_mtime:
                        cached_skipped += 1
                        continue
                except OSError:
                    pass
            files_to_scan.append(f)
        all_files = files_to_scan

    total_found = len(all_files)

    reset_checked()
    reset_interrupt()
    corrupted = 0
    moved = 0
    failed = 0
    webp_converted = 0
    webp_deleted_existing = 0
    corrupt_files: list[tuple[Path, str]] = []

    actual_total = total_found + cached_skipped
    cache_entries: list[tuple] = []

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {
            executor.submit(
                process_file, f, source_dir, error_dir, convert_webp, white_bg
            ): f
            for f in all_files
            if not is_interrupted()
        }

        for future in as_completed(futures):
            if is_interrupted():
                executor.shutdown(wait=False, cancel_futures=True)
                break

            res = future.result()
            current = increment_checked()

            if progress_callback:
                progress_callback(current + cached_skipped, actual_total)

            filepath = res["path"]
            action = res["action"]

            if db and not db_skip:
                cache_entries.append(_make_cache_entry(filepath, action, res.get("engine", "")))

            if action == "webp_converted":
                webp_converted += 1
                logger.info("[%d/%d] WebP->PNG success (%s): %s", current, actual_total, res["engine"], filepath)
            elif action == "webp_deleted_existing_png":
                webp_deleted_existing += 1
                logger.info("[%d/%d] PNG already exists, WebP deleted: %s", current, actual_total, filepath)
            elif res["corrupted"]:
                corrupted += 1
                if action == "webp_convert_failed":
                    corrupt_files.append((filepath, res["reason"]))
                    logger.info("[%d/%d] WebP conversion failed: %s | reason: %s", current, actual_total, filepath, res["reason"])
                elif action == "webp_converted_but_png_corrupted":
                    png_path = filepath.with_suffix(".png")
                    corrupt_files.append((png_path, res["reason"]))
                    logger.info("[%d/%d] WebP->PNG but PNG corrupted: %s -> %s | reason: %s", current, actual_total, filepath, png_path, res["reason"])
                else:
                    corrupt_files.append((filepath, res["reason"]))
                    logger.info("[%d/%d] Corrupted image: %s | reason: %s", current, actual_total, filepath, res["reason"])

    if db and not db_skip and cache_entries:
        try:
            db.insert_scan_cache(cache_entries)
            logger.info("DB cache updated, %d records written", len(cache_entries))
        except Exception as e:
            logger.error("DB cache update failed: %s", e)

    if corrupt_files:
        for filepath, reason in corrupt_files:
            if is_interrupted():
                break
            rel = filepath.name
            for sd in source_dirs:
                try:
                    rel = filepath.relative_to(sd)
                    break
                except ValueError:
                    pass
            dest = error_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(filepath), str(dest))
                moved += 1
                logger.info("Moved to: %s", dest)
            except Exception as e:
                failed += 1
                logger.error("Move failed: %s -> %s | error: %s", filepath, dest, e)

    logger.info("=" * 60)
    if is_interrupted():
        logger.info("Scan interrupted by user")
    else:
        logger.info("Scan complete")
    logger.info("Total checked: %d (cached skipped: %d)", get_checked(), cached_skipped)
    logger.info("Corrupted: %d", corrupted)
    logger.info("Moved: %d, Failed: %d", moved, failed)
    if convert_webp:
        logger.info("WebP->PNG: %d, Already had PNG: %d", webp_converted, webp_deleted_existing)
    logger.info("=" * 60)

    return {
        "total": get_checked(),
        "total_found": actual_total,
        "corrupted": corrupted,
        "moved": moved,
        "failed": failed,
        "interrupted": is_interrupted(),
        "webp_converted": webp_converted,
        "webp_deleted_existing": webp_deleted_existing,
        "cached_skipped": cached_skipped,
    }