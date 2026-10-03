"""Idiomas do Torno, lidos dos mesmos arquivos que a homepage e o chat usam.

Para adicionar um idioma, veja landing/i18n/README.md.
"""

import json
import os
from functools import cache
from http.cookies import SimpleCookie
from pathlib import Path

LANG_COOKIE = "torno-lang"
I18N_DIR = Path(os.getenv("CHAINLIT_APP_ROOT", os.getcwd())) / "landing" / "i18n"


@cache
def registry() -> dict:
    return json.loads((I18N_DIR / "languages.json").read_text(encoding="utf-8"))


def default_language() -> str:
    return registry()["default"]


def language_name(code: str) -> str:
    return next(lang["name"] for lang in registry()["languages"] if lang["code"] == code)


@cache
def strings(code: str) -> dict:
    return json.loads((I18N_DIR / "locales" / f"{code}.json").read_text(encoding="utf-8"))


def text(code: str, section: str, key: str) -> str:
    return strings(code)[section][key]


def language_from_cookie(cookie_header: str | None) -> str:
    """Idioma escolhido na interface (cookie gravado pela homepage e pelo chat)."""
    codes = {lang["code"] for lang in registry()["languages"]}
    if cookie_header:
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
        except Exception:
            return default_language()
        if (morsel := cookie.get(LANG_COOKIE)) and morsel.value in codes:
            return morsel.value
    return default_language()
