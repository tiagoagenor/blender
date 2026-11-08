# SPDX-License-Identifier: GPL-2.0-or-later
"""UI strings (owner: A). Contract: PLANO.md §2.4, rules §2.3-7.

    register_strings({"undo.init": {"pt_BR": "Início", "en": "Start"}, ...})
    t("undo.init")  ->  "Início"

A value may also be a plain str (= pt_BR only). Every key must start with one of the owner
prefixes below; a key registered twice raises KeyError (call register_strings from register()).
Missing language falls back to pt_BR, missing key returns the key itself.
"""

ORDER = 5

DEFAULT_LANGUAGE = "pt_BR"

# prefix -> owner (PLANO §2.3-7); `tool.<id>.*` belongs to the tool's owner.
PREFIXES = {
    "tool.": "tool owner",
    "ui.": "D", "menu.": "D", "tray.": "D",
    "vcb.": "C", "inf.": "C", "units.": "C",
    "edit.": "F", "mat.": "F",
    "view.": "G", "guide.": "G", "cam.": "G",
    "undo.": "A", "app.": "A",
}

_table = {}            # key -> {lang: text}
_language = [DEFAULT_LANGUAGE]


def register_strings(table):
    """Add strings; raises KeyError on duplicates / ValueError on bad prefix (nothing added then)."""
    new = {}
    for key, value in table.items():
        if not any(key.startswith(p) for p in PREFIXES):
            raise ValueError("i18n key {!r} has no owner prefix ({:s})".format(key, ", ".join(sorted(PREFIXES))))
        if key in _table or key in new:
            raise KeyError("i18n key registered twice: {!r}".format(key))
        if isinstance(value, str):
            value = {DEFAULT_LANGUAGE: value}
        if DEFAULT_LANGUAGE not in value:
            raise ValueError("i18n key {!r} has no {:s} text".format(key, DEFAULT_LANGUAGE))
        new[key] = dict(value)
    _table.update(new)


def unregister_strings(keys):
    for k in keys:
        _table.pop(k, None)


def has(key):
    return key in _table


def set_language(lang):
    _language[0] = lang or DEFAULT_LANGUAGE


def language():
    return _language[0]


def t(key, **fmt):
    entry = _table.get(key)
    if entry is None:
        return key
    text = entry.get(_language[0]) or entry[DEFAULT_LANGUAGE]
    if fmt:
        try:
            text = text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            pass
    return text


STRINGS_A = {
    "app.name": {"pt_BR": "SketchUp Mode", "en": "SketchUp Mode"},
    "undo.init": {"pt_BR": "Início", "en": "Start"},
    "undo.adjust": {"pt_BR": "Ajustar", "en": "Adjust"},
}


def register():
    register_strings(STRINGS_A)


def unregister():
    _table.clear()
