import hashlib
import json
import os
import shutil
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .utils import (
    is_image_file,
    is_interrupted,
    reset_interrupt,
    reset_checked,
    increment_checked,
    print_lock,
    collect_image_files,
    format_progress,
)


def _compute_md5(filepath: Path, chunk_size: int = 65536) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_md5_safe(filepath: Path) -> tuple[Path, str]:
    try:
        return filepath, _compute_md5(filepath)
    except Exception:
        return filepath, ""


def find_duplicates(
    source_dir: Path,
    threads: int = 12,
    logger: logging.Logger = None,
):
    """Find duplicate images across DIFFERENT folders only.

    Images within the same subfolder are NEVER considered duplicates of
    each other, even if their hashes match.  Only cross-folder matches
    are reported, preserving the newest copy (by mtime) in each group.
    """
    all_files = collect_image_files(source_dir)
    total_files = len(all_files)

    if logger:
        logger.info("=" * 60)
        logger.info("Duplicate scan (cross-folder only): %s (threads: %d)", source_dir, threads)
        logger.info("Total image files: %d", total_files)
        logger.info("=" * 60)

    size_groups: dict[int, list[Path]] = defaultdict(list)
    for f in all_files:
        if is_interrupted():
            return {}
        try:
            size = f.stat().st_size
            size_groups[size].append(f)
        except OSError:
            continue

    candidates = {s: g for s, g in size_groups.items() if len(g) > 1}
    candidate_count = sum(len(g) for g in candidates.values())
    group_count = len(candidates)

    if logger:
        logger.info("Size groups: %d, files to hash: %d", group_count, candidate_count)

    if candidate_count == 0:
        return {}

    reset_checked()

    hash_map: dict[str, list[Path]] = defaultdict(list)
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {}
        for size, group in candidates.items():
            for f in group:
                if is_interrupted():
                    executor.shutdown(wait=False, cancel_futures=True)
                    return {}
                futures[executor.submit(_compute_md5_safe, f)] = f

        for future in as_completed(futures):
            if is_interrupted():
                executor.shutdown(wait=False, cancel_futures=True)
                return {}

            filepath, md5 = future.result()
            current = increment_checked()

            if md5:
                hash_map[md5].append(filepath)

            if logger:
                logger.debug("[%d/%d] hash: %s", current, candidate_count, filepath)

    duplicates = {}
    for h, files in hash_map.items():
        if len(files) <= 1:
            continue

        folder_sets: dict[str, list[Path]] = defaultdict(list)
        for f in files:
            try:
                rel = str(f.relative_to(source_dir).parent)
            except ValueError:
                rel = ""
            folder_sets[rel].append(f)

        if len(folder_sets) <= 1:
            continue

        merged: list[Path] = []
        for folder_files in folder_sets.values():
            try:
                folder_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            except OSError:
                folder_files.sort(reverse=True)
            merged.extend(folder_files)

        duplicates[h] = merged

    dup_file_count = sum(len(files) - 1 for files in duplicates.values())

    if logger:
        logger.info("Found %d duplicate groups (cross-folder), %d extra copies", len(duplicates), dup_file_count)
        logger.info("=" * 60)

    return duplicates


def find_ad_images(
    source_dir: Path,
    overlap_threshold: float = 0.5,
    ad_scan_count: int = 6,
    threads: int = 12,
    logger: logging.Logger = None,
):
    """Find advertising image folders by comparing the LAST N images
    (sorted by name) across different subfolders.

    For each subfolder, takes the last ``last_n`` images (by filename
    sort), hashes them, and checks whether any pair of folders shares
    >= overlap_threshold of those hashes.  Returns a dict mapping
    folder_to_delete -> (kept_folder, overlap_pct).

    The folder with the oldest modification time is the one deleted.
    """
    last_n = ad_scan_count
    all_files = collect_image_files(source_dir)

    if logger:
        logger.info("=" * 60)
        logger.info("Ad image scan: %s (threshold: %d%%, last_n: %d)", source_dir, int(overlap_threshold * 100), last_n)

    folder_files: dict[str, list[Path]] = defaultdict(list)
    for f in all_files:
        try:
            rel = str(f.relative_to(source_dir).parent)
        except ValueError:
            rel = ""
        folder_files[rel].append(f)

    for folder in folder_files:
        folder_files[folder].sort(key=lambda f: f.name)

    folder_tail_hashes: dict[str, set[str]] = {}
    folder_tail_files: dict[str, list[Path]] = {}
    folder_mtime: dict[str, float] = {}
    folder_total: dict[str, int] = {}

    for folder, files in folder_files.items():
        tail = files[-last_n:] if len(files) >= last_n else files
        total_in_folder = len(files)
        folder_total[folder] = total_in_folder

        hash_set: set[str] = set()
        for f in tail:
            if is_interrupted():
                return {}
            _, md5 = _compute_md5_safe(f)
            if md5:
                hash_set.add(md5)
        folder_tail_hashes[folder] = hash_set
        folder_tail_files[folder] = tail

        try:
            folder_mtime[folder] = (Path(source_dir) / folder).stat().st_mtime
        except OSError:
            folder_mtime[folder] = 0.0

    to_delete: dict[str, tuple[str, int, list[Path]]] = {}
    folder_list = list(folder_tail_hashes.keys())

    for i in range(len(folder_list)):
        for j in range(i + 1, len(folder_list)):
            fa, fb = folder_list[i], folder_list[j]
            hashes_a = folder_tail_hashes[fa]
            hashes_b = folder_tail_hashes[fb]
            shared = hashes_a & hashes_b
            if not shared:
                continue

            count_a = len(hashes_a)
            count_b = len(hashes_b)
            if count_a == 0 or count_b == 0:
                continue

            shared_count = len(shared)
            ratio_a = shared_count / count_a
            ratio_b = shared_count / count_b
            max_ratio = max(ratio_a, ratio_b)

            if max_ratio >= overlap_threshold:
                mtime_a = folder_mtime.get(fa, 0)
                mtime_b = folder_mtime.get(fb, 0)
                total_a = folder_total.get(fa, 0)
                total_b = folder_total.get(fb, 0)
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

                if delete_folder not in to_delete:
                    pct = round(max_ratio * 100)
                    to_delete[delete_folder] = (kept_folder, pct, folder_tail_files[delete_folder])
                    if logger:
                        logger.info("Ad overlap: %s <-> %s (%d%%), delete older: %s",
                                    fa, fb, pct, delete_folder)

    if logger:
        logger.info("Ad scan found %d folders to delete", len(to_delete))
        logger.info("=" * 60)

    return to_delete


def move_duplicates(
    duplicates: dict,
    source_dir: Path,
    dedup_dir: Path,
    manifest_path: Path,
    logger: logging.Logger = None,
    db=None,
):
    dedup_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    db_entries = []
    entry_id = 0
    moved = 0
    failed = 0

    if logger:
        logger.info("=" * 60)
        logger.info("Moving duplicates to: %s", dedup_dir)

    total_dup = sum(len(files) - 1 for files in duplicates.values())

    for hash_val, files in sorted(duplicates.items()):
        if is_interrupted():
            break

        kept = files[0]
        for dup_file in files[1:]:
            if is_interrupted():
                break

            entry_id += 1
            try:
                rel_path = dup_file.relative_to(source_dir)
            except ValueError:
                rel_path = Path(dup_file.name)

            dest = dedup_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            if dest.exists():
                conflict = dest.parent / f"{dest.stem}_{entry_id}{dest.suffix}"
                dest = conflict

            try:
                file_size = dup_file.stat().st_size
            except OSError:
                file_size = 0

            try:
                shutil.move(str(dup_file), str(dest))
                moved += 1
                entries.append({
                    "id": entry_id,
                    "hash": hash_val,
                    "original_path": str(dup_file),
                    "stored_path": str(dest),
                    "kept_path": str(kept),
                    "file_size": file_size,
                    "status": "moved",
                })
                db_entries.append((hash_val, str(dup_file), str(dest), str(kept), file_size))
                if logger:
                    logger.info("[#%d] Moved: %s -> %s (kept: %s)", entry_id, dup_file, dest, kept)
            except Exception as e:
                failed += 1
                entries.append({
                    "id": entry_id,
                    "hash": hash_val,
                    "original_path": str(dup_file),
                    "stored_path": "",
                    "kept_path": str(kept),
                    "file_size": file_size,
                    "status": "move_failed",
                    "error": str(e),
                })
                if logger:
                    logger.error("[#%d] Move failed: %s -> %s - %s", entry_id, dup_file, dest, e)

    if db and db_entries:
        try:
            db.insert_duplicates(db_entries)
            if logger:
                logger.info("DB written, %d records", len(db_entries))
        except Exception as e:
            if logger:
                logger.error("DB write failed: %s", e)

    manifest = {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_dir": str(source_dir),
        "dedup_dir": str(dedup_dir),
        "total_groups": len(duplicates),
        "total_duplicates": total_dup,
        "moved": moved,
        "failed": failed,
        "entries": entries,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    if logger:
        logger.info("Manifest saved to: %s", manifest_path)
        logger.info("Move complete: success %d, failed %d", moved, failed)
        logger.info("=" * 60)

    return {
        "total_groups": len(duplicates),
        "total_duplicates": total_dup,
        "moved": moved,
        "failed": failed,
        "manifest_path": str(manifest_path),
        "entries": entries,
    }


def scan_duplicates(
    source_dir: Path,
    dedup_dir: Path,
    manifest_dir: Path,
    threads: int = 12,
    logger: logging.Logger = None,
    db=None,
):
    reset_interrupt()

    duplicates = find_duplicates(source_dir, threads, logger)
    if not duplicates or is_interrupted():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_path = manifest_dir / f"dedup_{timestamp}.json"

    result = move_duplicates(duplicates, source_dir, dedup_dir, manifest_path, logger, db)
    return result


def restore_from_manifest(
    manifest_path: Path,
    selected_ids: list[int] = None,
    logger: logging.Logger = None,
    progress_callback=None,
):
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    entries = manifest.get("entries", [])
    restored = 0
    skipped = 0
    failed = 0

    if logger:
        logger.info("=" * 60)
        logger.info("Restoring duplicates from manifest: %s", manifest_path)

    target_entries = entries
    if selected_ids is not None:
        id_set = set(selected_ids)
        target_entries = [e for e in entries if e["id"] in id_set]

    for idx, entry in enumerate(target_entries):
        if is_interrupted():
            break

        if progress_callback:
            progress_callback(idx + 1, len(target_entries))

        if entry["status"] != "moved":
            skipped += 1
            continue

        stored_path = Path(entry["stored_path"])
        original_path = Path(entry["original_path"])

        if not stored_path.exists():
            failed += 1
            if logger:
                logger.error("[#%d] File not found: %s", entry["id"], stored_path)
            continue

        original_path.parent.mkdir(parents=True, exist_ok=True)

        if original_path.exists():
            skipped += 1
            if logger:
                logger.warning("[#%d] Target already exists, skipping: %s", entry["id"], original_path)
            continue

        try:
            shutil.move(str(stored_path), str(original_path))
            entry["status"] = "restored"
            restored += 1
            if logger:
                logger.info("[#%d] Restored: %s -> %s", entry["id"], stored_path, original_path)
        except Exception as e:
            failed += 1
            if logger:
                logger.error("[#%d] Restore failed: %s -> %s - %s", entry["id"], stored_path, original_path, e)

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    if logger:
        logger.info("Restore complete: success %d, skipped %d, failed %d", restored, skipped, failed)
        logger.info("=" * 60)

    return {"restored": restored, "skipped": skipped, "failed": failed}


def move_to_trash(
    entries_data: list[dict],
    trash_dir: Path,
    logger: logging.Logger = None,
    progress_callback=None,
    db=None,
):
    trash_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    failed = 0
    db_ids = []

    total = len(entries_data)
    for idx, entry in enumerate(entries_data):
        if is_interrupted():
            break

        if progress_callback:
            progress_callback(idx + 1, total)

        stored_path = Path(entry["stored_path"])
        if not stored_path.exists():
            failed += 1
            if logger:
                logger.error("[#%d] File not found: %s", entry.get("id"), stored_path)
            continue

        try:
            rel = stored_path.relative_to(stored_path.anchor and stored_path.parents[-2] or stored_path.parent)
        except ValueError:
            rel = stored_path.name

        dest = trash_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest = trash_dir / f"{dest.stem}_{idx + 1}{dest.suffix}"

        try:
            shutil.move(str(stored_path), str(dest))
            moved += 1
            db_ids.append(entry["id"])
            if logger:
                logger.info("[#%d] Moved to trash: %s -> %s", entry.get("id"), stored_path, dest)
        except Exception as e:
            failed += 1
            if logger:
                logger.error("[#%d] Move failed: %s -> %s - %s", entry.get("id"), stored_path, dest, e)

    if db and db_ids:
        try:
            db.delete_duplicate_records(db_ids)
            if logger:
                logger.info("Deleted %d DB records", len(db_ids))
        except Exception as e:
            if logger:
                logger.error("DB operation failed: %s", e)

    if logger:
        logger.info("Trash move complete: success %d, failed %d", moved, failed)

    return {"moved": moved, "failed": failed}


def find_folder_overlaps(
    source_dir: Path,
    duplicates: dict = None,
    overlap_threshold: float = 0.5,
    logger: logging.Logger = None,
) -> dict:
    """Find folders that overlap by >= overlap_threshold (default 50%).

    Uses cross-folder duplicates (same-folder matches are excluded).
    For each pair of folders, if the ratio of shared hashes to total
    files in either folder exceeds the threshold, the OLDER folder
    (by mtime) is marked for deletion.

    Returns: {folder_to_delete: (kept_folder, overlap_pct)}
    """
    if duplicates is None:
        duplicates = find_duplicates(source_dir, logger=logger)

    if not duplicates:
        return {}

    folder_total: dict[str, int] = defaultdict(int)
    for root, _dirs, filenames in os.walk(source_dir):
        for fn in filenames:
            fp = Path(root) / fn
            if is_image_file(fp):
                try:
                    rel = str(fp.relative_to(source_dir).parent)
                except ValueError:
                    rel = ""
                folder_total[rel] += 1

    folder_hashes: dict[str, set[str]] = defaultdict(set)
    for h, files in duplicates.items():
        for f in files:
            try:
                rel = str(f.relative_to(source_dir).parent)
            except ValueError:
                rel = ""
            folder_hashes[rel].add(h)

    folder_mtime: dict[str, float] = {}
    for folder in folder_total:
        try:
            folder_mtime[folder] = (Path(source_dir) / folder).stat().st_mtime
        except OSError:
            folder_mtime[folder] = 0.0

    to_delete: dict[str, tuple[str, int]] = {}
    folder_list = list(folder_hashes.keys())

    for i in range(len(folder_list)):
        for j in range(i + 1, len(folder_list)):
            fa, fb = folder_list[i], folder_list[j]
            hashes_a = folder_hashes[fa]
            hashes_b = folder_hashes[fb]
            shared = hashes_a & hashes_b
            if not shared:
                continue

            total_a = folder_total.get(fa, 0)
            total_b = folder_total.get(fb, 0)
            if total_a == 0 or total_b == 0:
                continue

            shared_count = len(shared)
            ratio_a = shared_count / total_a
            ratio_b = shared_count / total_b
            max_ratio = max(ratio_a, ratio_b)

            if max_ratio >= overlap_threshold:
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

                if delete_folder not in to_delete:
                    pct = round(max_ratio * 100)
                    to_delete[delete_folder] = (kept_folder, pct)

    if logger:
        logger.info("Folder overlaps found: %d (threshold: %d%%)", len(to_delete), int(overlap_threshold * 100))

    return to_delete


def move_folder_to_dedup(
    folder_rel: str,
    kept_folder: str,
    overlap_pct: int,
    source_dir: Path,
    folder_dedup_dir: Path,
    logger: logging.Logger = None,
) -> tuple[bool, str]:
    src = source_dir / folder_rel
    if not src.exists():
        return False, "Source folder does not exist"

    dest = folder_dedup_dir / folder_rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        dest = folder_dedup_dir / f"{folder_rel}_{int(datetime.now().timestamp())}"

    try:
        shutil.move(str(src), str(dest))
        msg = f"Duplicate folder: {folder_rel} ({overlap_pct}% overlap with {kept_folder}) -> {dest}"
        if logger:
            logger.info("%s", msg)
        return True, ""
    except Exception as e:
        msg = f"Folder move failed: {src} -> {dest} - {e}"
        if logger:
            logger.error("%s", msg)
        return False, msg


def scan_folder_duplicates(
    source_dir: Path,
    folder_dedup_dir: Path,
    overlap_threshold: float = 0.5,
    logger: logging.Logger = None,
):
    reset_interrupt()

    duplicates = find_duplicates(source_dir, logger=logger)
    if not duplicates or is_interrupted():
        if logger:
            logger.info("No duplicates found, cannot analyze folder overlaps")
        return {"folders_moved": 0, "failed": 0}

    overlaps = find_folder_overlaps(source_dir, duplicates, overlap_threshold, logger)

    if not overlaps:
        if logger:
            logger.info("No folders with >=%d%% overlap found", int(overlap_threshold * 100))
        return {"folders_moved": 0, "failed": 0}

    if logger:
        logger.info("Found %d folders with >=%d%% overlap", len(overlaps), int(overlap_threshold * 100))

    folder_dedup_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    failed = 0

    for folder_rel, (kept, pct) in sorted(overlaps.items()):
        if is_interrupted():
            break
        ok, _ = move_folder_to_dedup(
            folder_rel, kept, pct, source_dir, folder_dedup_dir, logger
        )
        if ok:
            moved += 1
        else:
            failed += 1

    if logger:
        logger.info("Folder dedup complete: moved %d, failed %d", moved, failed)

    return {"folders_moved": moved, "failed": failed}



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

def scan_ad_duplicates(
    source_dir: Path,
    folder_dedup_dir: Path,
    overlap_threshold: float = 0.5,
    ad_scan_count: int = 6,
    threads: int = 12,
    logger: logging.Logger = None,
):
    """Scan for advertising image folders by comparing last 6 images.

    Finds folders where the last 6 images (by name) overlap >= threshold,
    then moves the older folder to dedup_dir.
    """
    reset_interrupt()

    to_delete = find_ad_images(source_dir, overlap_threshold, ad_scan_count, threads, logger)
    if not to_delete or is_interrupted():
        if logger:
            logger.info("No ad-image folders found")
        return {"folders_moved": 0, "failed": 0}

    folder_dedup_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    failed = 0

    for folder_rel, (kept, pct, tail_files) in sorted(to_delete.items()):
        if is_interrupted():
            break
        m, f = move_ad_images_to_dedup(
            folder_rel, kept, pct, tail_files, source_dir, folder_dedup_dir, logger
        )
        moved += m
        failed += f

    if logger:
        logger.info("Ad dedup complete: moved %d, failed %d", moved, failed)

    return {"folders_moved": moved, "failed": failed}