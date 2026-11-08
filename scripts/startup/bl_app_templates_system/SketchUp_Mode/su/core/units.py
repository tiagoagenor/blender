# SPDX-License-Identifier: GPL-2.0-or-later
"""Model units, number formatting and parsing (owner: C). Contract: PLANO.md §2.4, §3.5-6.

Every function takes `units`: the scene's `Scene.su_units` (SU_UnitsSettings) or any object with the
same attributes (`Units` below, used by tests). `units=None` → the current scene's settings, or the
defaults when there is no scene / the property is not registered.

Decimal separator: `units.decimal` = 'SYSTEM' (default) | 'COMMA' | 'PERIOD'. SYSTEM follows the macOS
region (`defaults read -g AppleLocale`, read once and cached) → `AppleLanguages` → the app language;
`setlocale` is never called. A ',' decimal makes ';' the list separator, else ','. When parsing, '.' is
always accepted as decimal point too.

Formats follow SketchUp: "2,50m", "25,00cm", "6,00m²", "90,0°", '12,00"', "3,00'".
"""

import math
import re
import subprocess
import sys
from dataclasses import dataclass

import bpy

ORDER = 110

LENGTH_UNITS = ('M', 'CM', 'MM', 'IN', 'FT')
METERS_PER = {'M': 1.0, 'CM': 0.01, 'MM': 0.001, 'IN': 0.0254, 'FT': 0.3048, 'KM': 1000.0}
SUFFIX = {'M': "m", 'CM': "cm", 'MM': "mm", 'IN': '"', 'FT': "'"}
AREA_SUFFIX = {'M': "m²", 'CM': "cm²", 'MM': "mm²", 'IN': "pol²", 'FT': "pés²"}
# typed unit suffixes (lower case) → unit
SUFFIX_IN = {
    "m": 'M', "cm": 'CM', "mm": 'MM', "km": 'KM',
    '"': 'IN', "in": 'IN', "pol": 'IN',
    "'": 'FT', "ft": 'FT', "pe": 'FT', "pes": 'FT', "pé": 'FT', "pés": 'FT',
}

# Decimal comma by region (ISO 3166) and, as fallback, by language (ISO 639). Regions whose
# separator depends on the language (CA, CH-fr/it, BE…) are resolved by the language.
COMMA_REGIONS = frozenset((
    "BR", "PT", "AO", "MZ", "CV", "DE", "AT", "FR", "ES", "IT", "NL", "DK", "SE", "NO", "FI", "IS",
    "PL", "CZ", "SK", "HU", "RO", "BG", "GR", "TR", "RU", "UA", "BY", "KZ", "RS", "HR", "SI", "BA",
    "MK", "AL", "LT", "LV", "EE", "ID", "VN", "AR", "CL", "CO", "UY", "PY", "VE", "BO", "EC", "CR",
    "ZA", "LU", "BE", "AZ", "GE", "AM",
))
PERIOD_REGIONS = frozenset((
    "US", "GB", "IE", "AU", "NZ", "MX", "JP", "CN", "TW", "HK", "KR", "SG", "IN", "IL", "TH", "PH",
    "MY", "PE", "GT", "DO", "PR", "PK", "NG", "KE", "EG", "SA", "AE",
))
COMMA_LANGS = frozenset((
    "pt", "de", "fr", "es", "it", "nl", "da", "sv", "nb", "nn", "no", "fi", "is", "pl", "cs", "sk",
    "hu", "ro", "bg", "el", "tr", "ru", "uk", "be", "id", "vi", "ca", "eu", "gl", "hr", "sl", "sr",
    "bs", "mk", "sq", "lt", "lv", "et", "az", "ka", "hy", "kk",
))


@dataclass
class Units:
    """Plain stand-in for Scene.su_units (tests, defaults)."""
    length_unit: str = 'M'
    length_precision: int = 2
    angle_precision: int = 1
    decimal: str = 'SYSTEM'
    show_suffix: bool = True
    angle_snap: bool = True
    angle_snap_deg: float = 15.0


DEFAULTS = Units()

_system_sep = [None]       # cached system decimal separator


# ---------------------------------------------------------------------------------------------- separators
def _sep_from_locale(code):
    """',' / '.' for a locale such as 'pt_BR', 'en_BR@rg=brzzzz', 'pt-BR'; None when unknown."""
    if not code:
        return None
    code = code.strip().strip('"')
    region = ""
    if "@" in code:
        code, _, mods = code.partition("@")
        m = re.search(r"rg=([a-zA-Z]{2})", mods)
        if m:
            region = m.group(1).upper()
    parts = re.split(r"[_-]", code)
    lang = parts[0].lower()
    if not region:
        for p in parts[1:]:
            if len(p) == 2 and p.isalpha():
                region = p.upper()
                break
    if region in COMMA_REGIONS:
        return ","
    if region in PERIOD_REGIONS:
        return "."
    if lang in COMMA_LANGS:
        return ","
    if lang:
        return "."
    return None


def _defaults_read(key):
    if sys.platform != "darwin":
        return ""
    try:
        out = subprocess.run(["/usr/bin/defaults", "read", "-g", key], capture_output=True, text=True,
                             timeout=2.0)
    except Exception:
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def _detect_system_sep():
    sep = _sep_from_locale(_defaults_read("AppleLocale"))
    if sep:
        return sep
    langs = _defaults_read("AppleLanguages")          # '(\n    "pt-BR"\n)'
    m = re.search(r'"?([A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)*)"?', langs.strip("()\n "))
    sep = _sep_from_locale(m.group(1)) if m else None
    if sep:
        return sep
    from .. import i18n
    return _sep_from_locale(i18n.language()) or ","


def system_decimal_sep():
    """Decimal separator of the macOS region (cached after the first call)."""
    if _system_sep[0] is None:
        _system_sep[0] = _detect_system_sep()
    return _system_sep[0]


def _reset_system_cache(value=None):
    """Tests: forget (or force) the cached system separator."""
    _system_sep[0] = value


def current(scene=None):
    """The active units settings (Scene.su_units) or DEFAULTS."""
    if scene is None:
        scene = getattr(bpy.context, "scene", None)
    u = getattr(scene, "su_units", None) if scene is not None else None
    return u if u is not None else DEFAULTS


def _u(units):
    return current() if units is None else units


def decimal_sep(units=None):
    d = getattr(_u(units), "decimal", 'SYSTEM')
    if d == 'COMMA':
        return ","
    if d == 'PERIOD':
        return "."
    return system_decimal_sep()


def list_sep(units=None):
    return ";" if decimal_sep(units) == "," else ","


# ---------------------------------------------------------------------------------------------- formatting
def _fmt_number(v, precision, sep):
    precision = max(0, int(precision))
    s = "{:.{p}f}".format(v, p=precision)
    if s.startswith("-") and float(s) == 0.0:
        s = s[1:]                                   # no "-0,00"
    return s.replace(".", sep) if sep != "." else s


def is_approx(v, precision):
    """True when showing `v` with `precision` decimals hides digits (SketchUp prefixes '~ ')."""
    q = round(v, max(0, int(precision)))
    return abs(v - q) > 1e-9 * max(1.0, abs(v))


def format_length(m, units=None, *, mark_approx=False):
    """Meters → '2,50m' in the model unit and precision; mark_approx → '~ 2,50m' when rounded (P1)."""
    u = _u(units)
    unit = getattr(u, "length_unit", 'M')
    v = m / METERS_PER[unit]
    prec = getattr(u, "length_precision", 2)
    s = _fmt_number(v, prec, decimal_sep(u))
    s = s + SUFFIX[unit] if getattr(u, "show_suffix", True) else s
    return "~ " + s if mark_approx and is_approx(v, prec) else s


def format_area(m2, units=None):
    """Square meters → '6,00m²' in the model unit squared."""
    u = _u(units)
    unit = getattr(u, "length_unit", 'M')
    v = m2 / (METERS_PER[unit] ** 2)
    s = _fmt_number(v, getattr(u, "length_precision", 2), decimal_sep(u))
    return s + AREA_SUFFIX[unit] if getattr(u, "show_suffix", True) else s


def format_angle(rad, units=None, *, mark_approx=False):
    """Radians → '90,0°' (mark_approx → '~ 33,7°' when rounded)."""
    u = _u(units)
    deg = math.degrees(rad)
    prec = getattr(u, "angle_precision", 1)
    s = _fmt_number(deg, prec, decimal_sep(u)) + "°"
    return "~ " + s if mark_approx and is_approx(deg, prec) else s


def format_number(v, units=None, precision=2):
    """Unitless number (scale factor, sides) with the decimal separator."""
    return _fmt_number(v, precision, decimal_sep(_u(units)))


# ---------------------------------------------------------------------------------------------- parsing
_UNUM = r"(?:\d+(?:\.\d*)?|\.\d+)"
_NUM = r"[+-]?" + _UNUM
_RE_NUMBER = re.compile(r"^" + _NUM + r"$")
_RE_FRACTION = re.compile(r"^([+-]?)(?:(\d+)\s+)?(\d+)/(\d+)$")
_RE_FEET_INCHES = re.compile(
    r"^([+-]?)(" + _UNUM + r")\s*(?:'|ft)\s*((?:\d+\s+)?\d+/\d+|" + _UNUM + r")?\s*(?:\"|in)?$")


def _normalize(text, units):
    """Strip and turn the decimal separator into '.'; ',' only when it is the decimal separator."""
    s = text.strip()
    if decimal_sep(units) == ",":
        s = s.replace(",", ".")
    return s


def parse_number(text, units=None):
    """'2,5' → 2.5 (also '1/2', '3 1/2'). ValueError when it is not a number."""
    s = _normalize(text, units)
    if _RE_NUMBER.match(s):
        return float(s)
    m = _RE_FRACTION.match(s)
    if m:
        sign, whole, num, den = m.groups()
        if float(den) == 0.0:
            raise ValueError("division by zero in {!r}".format(text))
        v = (float(whole) if whole else 0.0) + float(num) / float(den)
        return -v if sign == "-" else v
    raise ValueError("not a number: {!r}".format(text))


def split_unit(text):
    """'250cm' → ('250', 'CM'); '2,5' → ('2,5', None). The suffix is matched case-insensitively."""
    s = text.strip()
    low = s.lower()
    for suf in sorted(SUFFIX_IN, key=len, reverse=True):
        if low.endswith(suf) and len(low) > len(suf):
            head = s[:len(s) - len(suf)].rstrip()
            if head and (head[-1].isdigit() or head[-1] in ".,"):
                return head, SUFFIX_IN[suf]
    return s, None


def parse_length(text, units=None):
    """Typed length → meters. Accepts '2,5', '2.5', '250cm', '25mm', '3m', '12"', "3'", "5'6\"",
    '1/2"', '3 1/2"'. No suffix = model unit. ValueError when invalid."""
    u = _u(units)
    s = _normalize(text, u)
    if not s:
        raise ValueError("empty length")
    m = _RE_FEET_INCHES.match(s)
    if m and m.group(3):
        sign, ft, inch = m.groups()
        v = float(ft) * METERS_PER['FT'] + parse_number(inch, Units(decimal='PERIOD')) * METERS_PER['IN']
        return -v if sign == "-" else v
    head, unit = split_unit(s)
    if unit is None:
        unit = getattr(u, "length_unit", 'M')
    return parse_number(head, Units(decimal='PERIOD')) * METERS_PER[unit]


def parse_angle(text, units=None):
    """Typed angle → radians. '30', '30°', '-45,5' (degrees) or slope 'rise:run' ('3:12' → atan(3/12)).
    ValueError when invalid."""
    s = _normalize(text, _u(units))
    if not s:
        raise ValueError("empty angle")
    if ":" in s:
        rise, _, run = s.partition(":")
        r = parse_number(rise, Units(decimal='PERIOD'))
        n = parse_number(run, Units(decimal='PERIOD'))
        if n == 0.0 and r == 0.0:
            raise ValueError("invalid slope {!r}".format(text))
        return math.atan2(r, n)
    if s.endswith("°"):
        s = s[:-1].rstrip()
    elif s.lower().endswith("deg"):
        s = s[:-3].rstrip()
    return math.radians(parse_number(s, Units(decimal='PERIOD')))


# ---------------------------------------------------------------------------------------------- settings
class SU_UnitsSettings(bpy.types.PropertyGroup):
    """Scene.su_units — "Janela › Informações do modelo › Unidades"."""
    length_unit: bpy.props.EnumProperty(
        name="Unidade", default='M',
        items=(('M', "Metros", ""), ('CM', "Centímetros", ""), ('MM', "Milímetros", ""),
               ('IN', "Polegadas", ""), ('FT', "Pés", "")))
    length_precision: bpy.props.IntProperty(name="Precisão", default=2, min=0, max=6)
    angle_precision: bpy.props.IntProperty(name="Precisão do ângulo", default=1, min=0, max=6)
    decimal: bpy.props.EnumProperty(
        name="Separador decimal", default='SYSTEM',
        items=(('SYSTEM', "Do sistema", ""), ('COMMA', "Vírgula", ""), ('PERIOD', "Ponto", "")))
    show_suffix: bpy.props.BoolProperty(name="Mostrar unidade", default=True)
    angle_snap: bpy.props.BoolProperty(name="Ajuste de ângulo", default=True)
    angle_snap_deg: bpy.props.FloatProperty(name="Ângulo de ajuste", default=15.0, min=0.1, max=180.0)


STRINGS = {
    "units.m": {"pt_BR": "Metros", "en": "Meters"},
    "units.cm": {"pt_BR": "Centímetros", "en": "Centimeters"},
    "units.mm": {"pt_BR": "Milímetros", "en": "Millimeters"},
    "units.in": {"pt_BR": "Polegadas", "en": "Inches"},
    "units.ft": {"pt_BR": "Pés", "en": "Feet"},
    "units.precision": {"pt_BR": "Precisão", "en": "Precision"},
    "units.angle_snap": {"pt_BR": "Ajuste de ângulo", "en": "Angle snapping"},
}


def register():
    from .. import i18n
    i18n.register_strings(STRINGS)
    bpy.utils.register_class(SU_UnitsSettings)
    bpy.types.Scene.su_units = bpy.props.PointerProperty(type=SU_UnitsSettings)


def unregister():
    from .. import i18n
    i18n.unregister_strings(STRINGS)
    if hasattr(bpy.types.Scene, "su_units"):
        del bpy.types.Scene.su_units
    bpy.utils.unregister_class(SU_UnitsSettings)
