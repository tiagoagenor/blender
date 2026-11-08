# SPDX-License-Identifier: GPL-2.0-or-later
"""In-process publish/subscribe between owners (owner: A). Contract: PLANO.md §2.4.

Topics and keyword arguments:
  "load"                      file loaded (each owner ensures its own data on existing objects)
  "doc"       doc_key=...     a NEW document object was created (group, copy, 3D text, import)
  "geometry"  doc_key=...     Document.write() changed a mesh
  "selection"                 selection changed
  "tool"      old=..., new=...  active tool changed
  "undo"      direction='UNDO'|'REDO'
  "style"                     display style changed
Subscribers run in ascending `order` (ties: subscription order). An exception in a subscriber is
recorded with perf.error and the remaining subscribers still run.
"""

from . import perf

ORDER = 4

TOPICS = frozenset({"load", "doc", "geometry", "selection", "tool", "undo", "style"})

_subs = {t: [] for t in TOPICS}   # topic -> [(order, seq, fn)]
_seq = [0]


def subscribe(topic, fn, order=500):
    if topic not in TOPICS:
        raise ValueError("unknown event topic {!r}".format(topic))
    _seq[0] += 1
    _subs[topic].append((order, _seq[0], fn))
    _subs[topic].sort(key=lambda s: (s[0], s[1]))


def unsubscribe(topic, fn):
    _subs[topic][:] = [s for s in _subs[topic] if s[2] is not fn]


def emit(topic, **kw):
    if topic not in TOPICS:
        perf.error("emit: unknown event topic {!r}".format(topic))
        return
    for _order, _s, fn in list(_subs[topic]):
        try:
            fn(**kw)
        except Exception:
            perf.exception("event {:s} -> {:s}".format(topic, getattr(fn, "__qualname__", repr(fn))))


def subscribers(topic):
    return [s[2] for s in _subs[topic]]


def clear():
    for lst in _subs.values():
        lst.clear()
