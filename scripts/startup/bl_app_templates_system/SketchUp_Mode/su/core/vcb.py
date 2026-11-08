# SPDX-License-Identifier: GPL-2.0-or-later
"""Measurements box ("Medidas") — typed-value buffer and parser (owner: C). PLANO.md §2.4, §3.5.

    feed(ev) -> 'CONSUMED' | 'PASS' | 'APPLY' | 'CANCEL'      ev = tools.base.Ev (PRESS events)
    parse(text, schema, units=None) -> list[VCBValue]          raises ValueError when invalid
    values(schema, units=None) -> list[VCBValue] | None        parse STATE.vcb_buffer (None + vcb_error)
    take() -> str                                              buffer text, buffer cleared
    apply_text(text)                                           typed into the clickable field

feed() rules (§3.5-3): with an EMPTY buffer only digits . , - [ < / * start a value (letters PASS:
they are tool shortcuts); with a NON-EMPTY buffer every printable character goes to the buffer.
BACK_SPACE deletes one character (never "Excluir"). ESC with a buffer clears it → 'CANCEL' (the value
edit is cancelled, the tool operation is not); ESC with an empty buffer → 'PASS' (the tool cancels).
RET / NUMPAD_ENTER with a buffer → 'APPLY' (the caller parses with values()/take()); empty → 'PASS'.
Events with Ctrl or Cmd always PASS (Cmd+Z…). RELEASE events PASS.

Schemas (ToolMeta.vcb_schema) and accepted values:
  'length'   LENGTH                                   Linha (1 valor), Empurrar/puxar, Equidistância, Fita
  'length2'  LENGTH;LENGTH (one may be empty → None)  Retângulo "L;W"
  'line'     LENGTH | POINT_ABS [x;y;z] | POINT_REL <x;y;z>
  'distance' LENGTH | POINT_ABS | POINT_REL | MULTIPLY (5x, x5, *5) | DIVIDE (/5, 5/)     Mover
  'angle'    ANGLE (graus ou "3:12") | MULTIPLY | DIVIDE                                Girar, Transferidor
  'sides'    SIDES (12 ou 12s)                                                           Círculo/Polígono antes do clique
  'radius'   LENGTH (raio) | SIDES (12s)                                                 Círculo/Polígono
  'arc'      LENGTH (curvatura) | RADIUS (1r) | SEGMENTS (12s)                           Arco de dois pontos
  'segments' SEGMENTS (12 ou 12s)
  'scale'    NUMBER (1,5 / -1) or LENGTH with unit (3m), up to 3 separated (2;1;1)       Escala
  'number'   NUMBER
The list separator is units.list_sep() (';' with decimal comma, ',' with decimal point).
"""

import re
from dataclasses import dataclass
from typing import Optional

from . import units as _units

ORDER = 112

RESULTS = ('CONSUMED', 'PASS', 'APPLY', 'CANCEL')
START_CHARS = frozenset("0123456789.,-[</*")
SCHEMAS = frozenset(("length", "length2", "line", "distance", "angle", "sides", "radius", "arc",
                     "segments", "scale", "number"))


@dataclass
class VCBValue:
    kind: str                       # LENGTH ANGLE NUMBER SIDES SEGMENTS RADIUS MULTIPLY DIVIDE POINT_ABS POINT_REL
    value: Optional[float] = None   # m (LENGTH/RADIUS), rad (ANGLE), int-valued float (counts), factor (NUMBER)
    vector: Optional[tuple] = None  # POINT_ABS / POINT_REL: (x, y, z) in m (None for an empty component)
    text: str = ""

    @property
    def count(self):
        return int(self.value) if self.value is not None else None


_applier = [None]


# ---------------------------------------------------------------------------------------------- state
def _state():
    from .state import STATE
    return STATE


def buffer():
    return _state().vcb_buffer


def _set_buffer(text):
    st = _state()
    if st.vcb_buffer != text or st.vcb_error:
        st.vcb_buffer = text
        st.vcb_error = False
        st.redraw_statusbar()


def clear():
    _set_buffer("")


def take():
    """Return the buffer text and clear it."""
    text = _state().vcb_buffer
    clear()
    return text


# ---------------------------------------------------------------------------------------------- feed
def feed(ev):
    """Route one keyboard event to the buffer. See module doc for the rules."""
    if ev.value not in ('PRESS', 'NOTHING') or ev.ctrl or ev.alt_action:
        return 'PASS'
    buf = _state().vcb_buffer
    if ev.type in ('RET', 'NUMPAD_ENTER'):
        return 'APPLY' if buf else 'PASS'
    if ev.type == 'BACK_SPACE':
        if not buf:
            return 'PASS'
        _set_buffer(buf[:-1])
        return 'CONSUMED'
    if ev.type == 'ESC':
        if not buf:
            return 'PASS'
        clear()
        return 'CANCEL'
    ch = ev.unicode or ""
    if len(ch) != 1 or not ch.isprintable():
        return 'PASS'
    if not buf and ch not in START_CHARS:
        return 'PASS'
    _set_buffer(buf + ch)
    return 'CONSUMED'


def set_applier(fn):
    """A (tool_ops) installs fn(text) -> bool, called by apply_text (the clickable field)."""
    _applier[0] = fn


def apply_text(text):
    """Text typed into the clickable Measurements field: same path as typing + Enter."""
    text = (text or "").strip()
    if not text:
        return 'PASS'
    _set_buffer(text)
    fn = _applier[0]
    if fn is not None:
        fn(text)
    return 'APPLY'


def values(schema, units=None):
    """Parse the current buffer; on error set STATE.vcb_error and return None."""
    st = _state()
    try:
        return parse(st.vcb_buffer, schema, units)
    except ValueError:
        st.vcb_error = True
        st.redraw_statusbar()
        return None


# ---------------------------------------------------------------------------------------------- parse
_RE_MULT = re.compile(r"^(?:(\d+)\s*[x×*]|[x×*]\s*(\d+))$", re.IGNORECASE)
_RE_DIV = re.compile(r"^(?:/\s*(\d+)|(\d+)\s*/)$")
_RE_COUNT = re.compile(r"^(\d+)\s*s$", re.IGNORECASE)
_RE_RADIUS = re.compile(r"^(.+?)\s*r$", re.IGNORECASE)


def _split(text, units):
    return [p.strip() for p in text.split(_units.list_sep(units))]


def _mult(s):
    m = _RE_MULT.match(s)
    if m:
        n = int(m.group(1) or m.group(2))
        if n < 1:
            raise ValueError("multiplier must be >= 1")
        return VCBValue('MULTIPLY', float(n), text=s)
    m = _RE_DIV.match(s)
    if m:
        n = int(m.group(1) or m.group(2))
        if n < 1:
            raise ValueError("divisor must be >= 1")
        return VCBValue('DIVIDE', float(n), text=s)
    return None


def _count(s, kind, minimum, bare):
    m = _RE_COUNT.match(s)
    if m is None and bare and s.isdigit():
        n = int(s)
    elif m is not None:
        n = int(m.group(1))
    else:
        return None
    if n < minimum:
        raise ValueError("{:s} must be >= {:d}".format(kind.lower(), minimum))
    return VCBValue(kind, float(n), text=s)


def _length(s, units):
    return VCBValue('LENGTH', _units.parse_length(s, units), text=s)


def _point(s, units):
    kind = 'POINT_ABS' if s[0] == "[" else 'POINT_REL'
    close = "]" if kind == 'POINT_ABS' else ">"
    if not s.endswith(close):
        raise ValueError("unterminated point {!r}".format(s))
    parts = _split(s[1:-1], units)
    if len(parts) != 3:
        raise ValueError("a point needs 3 coordinates: {!r}".format(s))
    vec = tuple(_units.parse_length(p, units) if p else None for p in parts)
    if kind == 'POINT_ABS' and None in vec:
        raise ValueError("absolute point needs 3 coordinates: {!r}".format(s))
    return VCBValue(kind, vector=vec, text=s)


def parse(text, schema, units=None):
    """Parse typed text for a tool schema. Returns a non-empty list of VCBValue; ValueError if invalid."""
    if schema not in SCHEMAS:
        raise ValueError("unknown VCB schema {!r}".format(schema))
    s = (text or "").strip()
    if not s:
        raise ValueError("empty value")

    if schema in ("line", "distance") and s[0] in "[<":
        return [_point(s, units)]
    if schema in ("distance", "angle"):
        v = _mult(s)
        if v is not None:
            return [v]

    if schema == "length":
        return [_length(s, units)]
    if schema == "line":
        return [_length(s, units)]
    if schema == "distance":
        return [_length(s, units)]
    if schema == "length2":
        parts = _split(s, units)
        if len(parts) > 2 or not any(parts):
            raise ValueError("expected 'L{:s}W': {!r}".format(_units.list_sep(units), s))
        return [_length(p, units) if p else VCBValue('LENGTH', None, text="") for p in parts]
    if schema == "angle":
        return [VCBValue('ANGLE', _units.parse_angle(s, units), text=s)]
    if schema in ("sides", "segments"):
        kind = 'SIDES' if schema == "sides" else 'SEGMENTS'
        v = _count(s, kind, 3 if kind == 'SIDES' else 1, bare=True)
        if v is None:
            raise ValueError("expected a count: {!r}".format(s))
        return [v]
    if schema == "radius":
        v = _count(s, 'SIDES', 3, bare=False)
        return [v if v is not None else _length(s, units)]
    if schema == "arc":
        v = _count(s, 'SEGMENTS', 1, bare=False)
        if v is not None:
            return [v]
        m = _RE_RADIUS.match(s)
        if m:
            return [VCBValue('RADIUS', abs(_units.parse_length(m.group(1), units)), text=s)]
        return [_length(s, units)]
    if schema == "scale":
        parts = _split(s, units)
        if len(parts) > 3 or not all(parts):
            raise ValueError("expected up to 3 scale factors: {!r}".format(s))
        out = []
        for p in parts:
            head, unit = _units.split_unit(p)
            if unit is not None:
                out.append(_length(p, units))
            else:
                f = _units.parse_number(head, units)
                if f == 0.0:
                    raise ValueError("scale factor 0")
                out.append(VCBValue('NUMBER', f, text=p))
        return out
    if schema == "number":
        return [VCBValue('NUMBER', _units.parse_number(s, units), text=s)]
    raise ValueError("unhandled schema {!r}".format(schema))


STRINGS = {
    "vcb.measurements": {"pt_BR": "Medidas", "en": "Measurements"},
    "vcb.length": {"pt_BR": "Comprimento", "en": "Length"},
    "vcb.distance": {"pt_BR": "Distância", "en": "Distance"},
    "vcb.angle": {"pt_BR": "Ângulo", "en": "Angle"},
    "vcb.radius": {"pt_BR": "Raio", "en": "Radius"},
    "vcb.sides": {"pt_BR": "Lados", "en": "Sides"},
    "vcb.bulge": {"pt_BR": "Curvatura", "en": "Bulge"},
    "vcb.segments": {"pt_BR": "Segmentos", "en": "Segments"},
    "vcb.dimensions": {"pt_BR": "Dimensões", "en": "Dimensions"},
    "vcb.scale": {"pt_BR": "Escala", "en": "Scale"},
    "vcb.slope": {"pt_BR": "Inclinação", "en": "Slope"},
    "vcb.fov": {"pt_BR": "Campo de visão", "en": "Field of View"},
    "vcb.eye_height": {"pt_BR": "Altura dos olhos", "en": "Eye Height"},
    "vcb.invalid": {"pt_BR": "Valor inválido", "en": "Invalid value"},
}


def register():
    from .. import i18n
    i18n.register_strings(STRINGS)


def unregister():
    from .. import i18n
    i18n.unregister_strings(STRINGS)
    _applier[0] = None
