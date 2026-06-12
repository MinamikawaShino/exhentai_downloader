from pathlib import Path

content = Path("src/ui/library_tab.py").read_text()
# Find ad_scan definition
lines = content.splitlines()
for i, line in enumerate(lines):
    if "def _build(" in line:
        for j in range(i, i + 50):
            print(lines[j])
        break
