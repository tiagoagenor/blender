# SPDX-License-Identifier: GPL-2.0-or-later
"""Error counter and timing spans (owner: A).

`error()` is the single sink for "this should never happen" problems: import/register failures,
exceptions in draw layers, event subscribers and tool controllers. `scn_smoke` (and every gate)
fails when `errors() > 0`. Performance is deferred (PLANO §7): spans only accumulate, no budgets.
"""

import sys
import time
import traceback
from contextlib import contextmanager

ORDER = 0

_errors = []
_spans = {}   # name -> [count, total_s, max_s]


def error(msg):
    """Record an error (printed to stderr, counted by errors())."""
    msg = str(msg)
    _errors.append(msg)
    print("[su] ERROR:", msg, file=sys.stderr)


def exception(where):
    """Record the exception currently being handled, with traceback."""
    error("{:s}\n{:s}".format(where, traceback.format_exc()))


def errors():
    return len(_errors)


def messages():
    return list(_errors)


def reset():
    _errors.clear()
    _spans.clear()


@contextmanager
def span(name):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        s = _spans.setdefault(name, [0, 0.0, 0.0])
        s[0] += 1
        s[1] += dt
        if dt > s[2]:
            s[2] = dt


def spans():
    return {k: {"count": v[0], "total_s": v[1], "max_s": v[2]} for k, v in _spans.items()}
