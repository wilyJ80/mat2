import json
from pathlib import Path

import pytest

from mat2 import chat, i18n

ROOT = Path(__file__).resolve().parents[1]


def keys(data: dict, prefix: str = "") -> set[str]:
    out = set()
    for key, value in data.items():
        out |= keys(value, f"{prefix}{key}.") if isinstance(value, dict) else {prefix + key}
    return out


LANGUAGES = [lang["code"] for lang in i18n.registry()["languages"]]


def test_default_language_is_registered():
    assert i18n.default_language() in LANGUAGES


@pytest.mark.parametrize("code", LANGUAGES)
def test_every_language_has_the_same_texts_as_the_default(code):
    assert keys(i18n.strings(code)) == keys(i18n.strings(i18n.default_language()))


@pytest.mark.parametrize("code", LANGUAGES)
def test_every_language_has_a_chainlit_translation(code):
    translation = ROOT / ".chainlit" / "translations" / f"{code}.json"
    english = json.loads((ROOT / ".chainlit" / "translations" / "en-US.json").read_text(encoding="utf-8"))
    assert keys(json.loads(translation.read_text(encoding="utf-8"))) == keys(english)


@pytest.mark.parametrize(
    ("cookie", "expected"),
    [
        ("torno-lang=en-US", "en-US"),
        ("outro=1; torno-lang=pt-BR; x=y", "pt-BR"),
        ("torno-lang=xx-XX", i18n.default_language()),
        ("", i18n.default_language()),
        (None, i18n.default_language()),
        ("lixo;;=", i18n.default_language()),
    ],
)
def test_language_from_cookie(cookie, expected):
    assert i18n.language_from_cookie(cookie) == expected


@pytest.mark.parametrize("code", LANGUAGES)
def test_system_prompt_names_the_selected_language(code):
    prompt = chat.system_prompt(code)
    assert i18n.language_name(code) in prompt
    assert "{language}" not in prompt


def test_landing_keys_exist_in_every_language():
    import re

    html = (ROOT / "landing" / "index.html").read_text(encoding="utf-8")
    used = set(re.findall(r'data-i18n="([^"]+)"', html))
    for attrs in re.findall(r'data-i18n-attr="([^"]+)"', html):
        used |= {pair.split(":")[1] for pair in attrs.split(";")}
    for code in LANGUAGES:
        missing = used - i18n.strings(code)["landing"].keys()
        assert not missing, f"{code}: {sorted(missing)}"
