from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def scrape_gallery_metadata(driver) -> dict:
    result = {
        "title": "",
        "title_jp": "",
        "artist": "",
        "category": "",
        "tags": "",
        "file_count": 0,
        "file_size": "",
    }
    try:
        gj = driver.find_element(By.ID, "gj")
        result["title_jp"] = gj.text.strip()
    except NoSuchElementException:
        pass

    try:
        gn = driver.find_element(By.ID, "gn")
        result["title"] = gn.text.strip()
        if not result["title"]:
            result["title"] = result["title_jp"]
    except NoSuchElementException:
        result["title"] = result["title_jp"]

    try:
        gdc = driver.find_element(By.ID, "gdc")
        text = gdc.text.strip()
        result["file_count"] = _extract_file_count(text)
        result["file_size"] = _extract_file_size(text)
    except NoSuchElementException:
        pass

    try:
        gd2 = driver.find_element(By.ID, "gd2")
        rows = gd2.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) >= 2:
                key = tds[0].text.strip().lower()
                val = tds[1].text.strip()
                if "artist" in key:
                    result["artist"] = val
                elif "category" in key or "language" in key:
                    if result["category"]:
                        result["category"] += ", " + val
                    else:
                        result["category"] = val
    except Exception:
        pass

    tags_list = []
    try:
        tag_elems = driver.find_elements(By.CSS_SELECTOR, "#taglist td")
        for elem in tag_elems:
            text = elem.text.strip()
            if text and ":" not in text:
                tags_list.append(text)
    except Exception:
        pass

    try:
        tag_divs = driver.find_elements(By.CSS_SELECTOR, "#taglist a")
        for elem in tag_divs:
            text = elem.text.strip()
            if text and text not in tags_list:
                tags_list.append(text)
    except Exception:
        pass

    result["tags"] = ", ".join(tags_list)
    return result


def _extract_file_count(text: str) -> int:
    import re
    m = re.search(r'(\d+)\s*files?', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def _extract_file_size(text: str) -> str:
    import re
    m = re.search(r'([\d.]+\s*[GMK]B)', text, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""
