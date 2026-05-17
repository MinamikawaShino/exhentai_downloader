import locale
import os

from .en import EN
from .zh_cn import ZH_CN
from .zh_tw import ZH_TW
from .jp import JP
from .ru import RU

LANGS = {"en": EN, "zh_cn": ZH_CN, "zh_tw": ZH_TW, "jp": JP, "ru": RU}

_current = None


def _detect_system_language() -> str:
    candidates = []
    for getter in (
        lambda: locale.getlocale()[0],
        lambda: locale.getlocale(locale.LC_CTYPE)[0],
        lambda: locale.getdefaultlocale()[0],
    ):
        try:
            value = getter()
            if value:
                candidates.append(value)
        except Exception:
            pass
    for env_name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(value.split(":", 1)[0])

    for value in candidates:
        lang = value.lower().replace("-", "_")
        if lang.startswith(("zh_cn", "zh_sg")) or "zh_hans" in lang:
            return "zh_cn"
        if lang.startswith("zh"):
            return "zh_tw"
        if "chinese" in lang:
            if any(part in lang for part in ("china", "simplified", "singapore")):
                return "zh_cn"
            return "zh_tw"
        if lang.startswith("ja") or "japanese" in lang:
            return "jp"
        if lang.startswith("ru") or "russian" in lang:
            return "ru"
    return "en"


def set_language(lang: str):
    global _current
    if lang and lang in LANGS:
        _current = lang
    else:
        _current = None


def get_language() -> str:
    global _current
    if _current is None:
        _current = _detect_system_language()
    return _current


def t(key: str, **kwargs) -> str:
    lang = get_language()
    table = LANGS.get(lang, EN)
    text = table.get(key, EN.get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def available_languages() -> dict:
    return {
        "en": "English",
        "zh_cn": "简体中文",
        "zh_tw": "繁體中文",
        "jp": "日本語",
        "ru": "Русский",
    }
