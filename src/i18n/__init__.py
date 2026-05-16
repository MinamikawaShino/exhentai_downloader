import locale
import sys

from .en import EN
from .zh_cn import ZH_CN
from .zh_tw import ZH_TW
from .ja import JA
from .ru import RU

LANGS = {"en": EN, "zh_cn": ZH_CN, "zh_tw": ZH_TW, "ja": JA, "ru": RU}

_current = None


def set_language(lang: str):
    global _current
    if lang and lang in LANGS:
        _current = lang
    else:
        _current = None


def get_language() -> str:
    global _current
    if _current is None:
        try:
            sys_lang = locale.getlocale()[0] or "en"
        except Exception:
            sys_lang = "en"
        if sys_lang.startswith("zh_CN") or sys_lang.startswith("zh_SG"):
            _current = "zh_cn"
        elif sys_lang.startswith("zh"):
            _current = "zh_tw"
        elif sys_lang.startswith("ja"):
            _current = "ja"
        elif sys_lang.startswith("ru"):
            _current = "ru"
        else:
            _current = "en"
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
        "ja": "日本語",
        "ru": "Русский",
    }