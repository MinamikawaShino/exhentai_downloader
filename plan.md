1. **Add `ad_scan_count` to library tab settings**:
   - In `src/ui/library_tab.py`, add `self.ad_scan_count_var` (default: 6) to store the number of tail images to scan for ad duplicates. Add it to the `_gather_values` and `_restore_values` methods.
   - Add a row with a label (`t("lib.ad_scan_count")`) and a `CTkEntry` for `self.ad_scan_count_var` right after the overlap threshold row.
   - Update `src/i18n/*.py` to add translations for `lib.ad_scan_count` (e.g. "Ad scan image count:" or "广告图扫描数量:").
   - When calling `scan_ad_duplicates` in `src/ui/library_tab.py`, pass this value (`ad_scan_count`).

2. **Update `find_ad_images` logic (in `src/imgchk/dedup.py`)**:
   - Change `find_ad_images` and `scan_ad_duplicates` to accept `ad_scan_count` (which sets `last_n`, defaulting to 6).
   - Change the logic to *only delete the tail files* (the `last_n` files that are matching) rather than marking the whole folder for deletion. Instead of `to_delete[delete_folder] = (kept_folder, pct)`, we need to build a list of files to move.
   - Wait, `scan_ad_duplicates` calls `move_folder_to_dedup`. If we only want to move the *files*, we shouldn't use `move_folder_to_dedup`. Instead we should use something similar to `move_duplicates` or a new function `move_ad_images_to_dedup` that moves individual files. Let's create `move_ad_images_to_dedup` and modify `scan_ad_duplicates` to use it.
   - Specifically, if `delete_folder` is marked as the one containing ad images, we just move `tail` images (or `shared` images from `tail`) of `delete_folder` to `ad_dedup_dir`.

3. **Update `test_folder_overlap` logic (in `find_folder_overlaps` inside `src/imgchk/dedup.py`)**:
   - The user requested: "重复文件夹去重功能当A/B/C文件夹中A和B文件夹内的图像任一一方和另一方的图像重复率超50%则删除图像量最少的文件夹，图像量相近（80%）则删除最早期的文件夹".
   - The current logic is:
     ```python
     if mtime_a <= mtime_b:
         delete_folder = fa
         kept_folder = fb
     else:
         delete_folder = fb
         kept_folder = fa
     ```
   - Change it to:
     ```python
     total_a = folder_total.get(fa, 0)
     total_b = folder_total.get(fb, 0)
     min_total = min(total_a, total_b)
     max_total = max(total_a, total_b)

     if max_total > 0 and (min_total / max_total) >= 0.8:
         # Similar count -> delete earliest
         if mtime_a <= mtime_b:
             delete_folder = fa
             kept_folder = fb
         else:
             delete_folder = fb
             kept_folder = fa
     else:
         # Different count -> delete fewest
         if total_a < total_b:
             delete_folder = fa
             kept_folder = fb
         elif total_b < total_a:
             delete_folder = fb
             kept_folder = fa
         else: # Should not be hit if we used < 0.8
             if mtime_a <= mtime_b:
                 delete_folder = fa
                 kept_folder = fb
             else:
                 delete_folder = fb
                 kept_folder = fa
     ```

4. **Complete Pre Commit Steps**:
   - Run verification scripts or follow testing guidelines in the repo to make sure everything works fine.

5. **Submit**:
   - Submit the changed files to the appropriate branch.
