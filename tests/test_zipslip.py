import os
import zipfile
import shutil
import tempfile
from src.utils.integrity import extract_zip

def test_zipslip():
    # Setup temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        extract_dir = os.path.join(temp_dir, "extract_test")
        os.makedirs(extract_dir, exist_ok=True)

        zip_path = os.path.join(temp_dir, "malicious.zip")
        evil_file_path = os.path.join(temp_dir, "evil.txt")

        # Determine the relative path to go out of extract_dir and into temp_dir
        # Since extract_dir is temp_dir/extract_test, `../evil.txt` will target temp_dir/evil.txt

        with zipfile.ZipFile(zip_path, "w") as zf:
            # We add a file with path traversal
            # Note: newer python prevents this via writestr with ../
            # so we might have to construct ZipInfo manually or just try it
            zinfo = zipfile.ZipInfo("../evil.txt")
            zf.writestr(zinfo, "malicious content")

            # Add a safe file just to be sure it extracts
            zf.writestr("safe.txt", "safe content")

        print("Created malicious zip at", zip_path)

        # Try to extract it
        success = extract_zip(zip_path, extract_dir)
        print("Extraction success:", success)

        # Check if the safe file exists
        safe_file_exists = os.path.exists(os.path.join(extract_dir, "safe.txt"))
        print("Safe file exists:", safe_file_exists)

        # Check if the evil file exists outside the extract dir
        evil_file_exists = os.path.exists(evil_file_path)
        print("Evil file exists at", evil_file_path, ":", evil_file_exists)

        assert safe_file_exists, "Safe file was not extracted"
        assert not evil_file_exists, "Zip Slip vulnerability still present!"

        print("Success! Vulnerability is mitigated.")

    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_zipslip()
