from pathlib import Path

content = Path("src/imgchk/dedup.py").read_text()
print("mtime logic in find_folder_overlaps:")
idx = content.find("def find_folder_overlaps")
end_idx = content.find("def move_folder_to_dedup", idx)
print(content[idx:end_idx])
