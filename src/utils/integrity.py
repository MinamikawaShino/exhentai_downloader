import os
import zipfile
import hashlib


def verify_zip_integrity(filepath: str) -> bool:
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            bad = zf.testzip()
            return bad is None
    except Exception:
        return False


def extract_zip(filepath: str, extract_to: str = None) -> bool:
    if extract_to is None:
        extract_to = os.path.splitext(filepath)[0]
    os.makedirs(extract_to, exist_ok=True)
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            for member in zf.infolist():
                target_path = os.path.join(extract_to, member.filename)
                if os.path.exists(target_path):
                    continue
                zf.extract(member, extract_to)
        return True
    except Exception:
        return False


def file_checksum(filepath: str, algo: str = "md5") -> str:
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
