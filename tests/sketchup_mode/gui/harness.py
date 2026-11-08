# SPDX-License-Identifier: GPL-2.0-or-later
"""GUI scenario harness (owner: A). PLANO.md §8.2. Started by tools/sketchup_mode/run_gui.sh:

    Blender --app-template SketchUp_Mode --enable-event-simulate --python harness.py -- <scenario> <out_dir>

A scenario is tests/sketchup_mode/gui/<scenario>.py defining `run(h)`, a GENERATOR driven by a timer:
    yield 0.3                       wait 0.3 s (one step per tick, like visual_spike/driver.py)
    yield h.until(pred, 5.0, "x")   poll pred() every 0.1 s; failed check "x" on timeout
    yield from h.drag_region_edge('TOOLS', 96)
    h.check("name", condition, detail)   assert per step (recorded; the scenario continues)
Before `run` the harness checks isolation (every user path inside /private/tmp/su_stage_*; aborts
otherwise), waits for driver_namespace["su_ready"], sends an initial ESC and checks for one window.
After `run`: perf.errors() must be 0. Writes <out_dir>/results.json ("ok": true|false) and quits.
Coordinates are always taken from region.x/y/width/height (physical px): nothing depends on the
window size (-p is ignored on this Mac; the window opens maximised).
"""

import importlib
import importlib.util
import json
import os
import sys
import time
import traceback

import bpy

sys.dont_write_bytecode = True      # no __pycache__ in the worktree (scenario modules)

HERE =os.path.dirname(os.path.abspath(__file__))
STAGE_PREFIX = "/private/tmp/su_stage_"
SU_MODULE = "bl_app_templates_system.SketchUp_Mode.su"
READY_TIMEOUT_S = float(os.environ.get("SU_READY_TIMEOUT", "60"))
SCENARIO_TIMEOUT_S = float(os.environ.get("SU_SCENARIO_TIMEOUT", "300"))
STEP_S = 0.1


class _Until:
    def __init__(self, pred, timeout, what):
        self.pred, self.timeout, self.what = pred, timeout, what
        self.t0 = None


class Harness:
    def __init__(self, scenario, out_dir):
        self.scenario = scenario
        self.out_dir = out_dir
        self.checks = []
        self.exception = None
        self.t_start = time.monotonic()
        self.done = False
        self._gen = None
        self._log = open(os.path.join(out_dir, "harness_log.txt"), "a", encoding="utf-8")

    # ------------------------------------------------------------------ basics
    def log(self, *a):
        print("[harness]", *a, file=self._log, flush=True)

    @property
    def su(self):
        return importlib.import_module(SU_MODULE)

    def check(self, name, cond, detail=""):
        ok = bool(cond)
        self.checks.append({"name": name, "ok": ok, "detail": str(detail) if not ok or detail else ""})
        self.log("CHECK", "ok  " if ok else "FAIL", name, detail if not ok else "")
        return ok

    def until(self, pred, timeout=5.0, what="condition"):
        return _Until(pred, timeout, what)

    # ------------------------------------------------------------------ window / regions
    def window(self):
        return bpy.context.window_manager.windows[0]

    def area_regions(self):
        """(window, largest VIEW_3D area, {region.type: region})."""
        win = self.window()
        areas = [a for a in win.screen.areas if a.type == 'VIEW_3D']
        if not areas:
            return win, None, {}
        a = max(areas, key=lambda a: a.width * a.height)
        return win, a, {r.type: r for r in a.regions}

    # ------------------------------------------------------------------ input (window coordinates, physical px)
    _mouse = (0, 0)

    def event(self, type, value='NOTHING', x=None, y=None, **kw):
        """Simulated event; without x/y it happens at the current (last moved-to) mouse position."""
        win = self.window()
        if x is None:
            x, y = self._mouse
        win.event_simulate(type, value, x=int(x), y=int(y), **kw)

    def move(self, x, y):
        self._mouse = (int(x), int(y))
        self.event('MOUSEMOVE', 'NOTHING', x, y)

    def glide(self, x, y, steps=6):
        """Several mouse moves from the current position to (x, y) (real-ish drag/hover path)."""
        x0, y0 = self._mouse
        for i in range(1, steps + 1):
            self.move(x0 + (x - x0) * i / steps, y0 + (y - y0) * i / steps)

    def key(self, type, unicode=None, **kw):
        if unicode:
            self.event(type, 'PRESS', unicode=unicode, **kw)
        else:
            self.event(type, 'PRESS', **kw)
        self.event(type, 'RELEASE', **kw)

    def type_text(self, text, enter=True):
        """Type characters (+ Enter) at the current mouse position."""
        testing = importlib.import_module(SU_MODULE + ".testing")
        for ch in text:
            self.key(testing.key_type(ch), unicode=ch)
        if enter:
            self.key('RET')

    def click(self, x=None, y=None, **kw):
        if x is not None:
            self.move(x, y)
        self.event('LEFTMOUSE', 'PRESS', **kw)
        self.event('LEFTMOUSE', 'RELEASE', **kw)

    def world_xy(self, co):
        """Window coordinates (physical px) of world point `co` in the main 3D view."""
        from bpy_extras import view3d_utils
        win, area, R = self.area_regions()
        r = R['WINDOW']
        rv3d = area.spaces.active.region_3d
        p = view3d_utils.location_3d_to_region_2d(r, rv3d, co)
        return r.x + int(round(p.x)), r.y + int(round(p.y))

    # ------------------------------------------------------------------ colour probes
    def load_png(self, path):
        """(width, height, numpy float array [h, w, 4]) of a PNG (rows bottom-up, like window y)."""
        import numpy as np
        img = bpy.data.images.load(path, check_existing=False)
        w, h = img.size
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        bpy.data.images.remove(img)
        return w, h, px.reshape(h, w, 4)

    def probe(self, shot, x, y, r=2):
        """Mean sRGB 0–255 around window pixel (x, y) of a screenshot loaded with load_png."""
        w, h, px = shot
        win = self.window()
        sx, sy = w / max(1, win.width * bpy.context.preferences.system.pixel_size), \
            h / max(1, win.height * bpy.context.preferences.system.pixel_size)
        cx, cy = int(x * sx), int(y * sy)
        patch = px[max(0, cy - r):cy + r + 1, max(0, cx - r):cx + r + 1, :3]
        return [int(round(float(c) * 255)) for c in patch.reshape(-1, 3).mean(axis=0)]

    @staticmethod
    def color_close(got, want, tol):
        return got is not None and all(abs(a - b) <= tol for a, b in zip(got, want))

    # ------------------------------------------------------------------ su hooks
    @property
    def testing(self):
        return importlib.import_module(SU_MODULE + ".testing")

    def state(self):
        return self.testing.state_dump()

    def stats(self, doc_key=None):
        return self.testing.doc_stats(doc_key)

    def install_fakes(self):
        """B/C/D modules not merged yet → the unit-test fakes (tests/sketchup_mode/unit/fakes.py)."""
        unit = os.path.join(os.path.dirname(HERE), "unit")
        if unit not in sys.path:
            sys.path.insert(0, unit)
        fakes = importlib.import_module("fakes")
        names = fakes.install(SU_MODULE)
        self.log("fakes installed:", names)
        return names

    def region_xy(self, region, fx, fy):
        """Window coordinates of the point at fractions (fx, fy) of `region`."""
        return region.x + int(region.width * fx), region.y + int(region.height * fy)

    def drag_region_edge(self, kind, width_logical):
        """Resize the TOOLS/UI region of the 3D view by a simulated edge drag (visual_spike/driver.py)."""
        win, area, R = self.area_regions()
        r = R[kind]
        ps = bpy.context.preferences.system.pixel_size
        y = r.y + r.height // 2
        if kind == 'TOOLS':
            x0, x1 = r.x + r.width - 1, r.x + int(width_logical * ps)
        else:
            x0, x1 = r.x + 1, r.x + r.width - int(width_logical * ps) - 2
        self.move(x0, y)
        yield 0.35
        self.event('LEFTMOUSE', 'PRESS', x0, y)
        yield 0.35
        for i in range(1, 11):
            self.move(x0 + (x1 - x0) * i / 10, y)
        yield 0.35
        self.event('LEFTMOUSE', 'RELEASE', x1, y)
        yield 0.35

    def park_mouse(self):
        win, area, R = self.area_regions()
        r = R.get('WINDOW')
        if r is not None:
            self.move(*self.region_xy(r, 0.8, 0.75))

    def screenshot(self, path):
        win = self.window()
        with bpy.context.temp_override(window=win):
            bpy.ops.screen.screenshot(filepath=path)

    # ------------------------------------------------------------------ isolation / preflight
    def isolation_problems(self):
        paths = {k: bpy.utils.user_resource(k) for k in ("CONFIG", "SCRIPTS", "DATAFILES", "EXTENSIONS")}
        paths["USER"] = bpy.utils.resource_path('USER')
        paths["tempdir"] = bpy.app.tempdir
        return {k: v for k, v in paths.items() if not os.path.realpath(v).startswith(STAGE_PREFIX)}

    def _preflight(self):
        bad = self.isolation_problems()
        self.check("isolated user paths", not bad, bad)
        if bad:
            return
        self.check("app template is SketchUp_Mode",
                   bpy.context.preferences.app_template == "SketchUp_Mode",
                   bpy.context.preferences.app_template)
        self.check("seeded userpref.blend loaded (prefs auto-save off)",
                   not bpy.context.preferences.use_preferences_save)
        yield self.until(lambda: bpy.app.driver_namespace.get("su_ready"), READY_TIMEOUT_S, "su_ready")
        self.key('ESC')
        yield 0.3
        self.check("single window (no extra window/popup)", len(bpy.context.window_manager.windows) == 1,
                   len(bpy.context.window_manager.windows))

    def _postflight(self):
        try:
            perf = importlib.import_module(SU_MODULE + ".perf")
            n = perf.errors()
            self.check("perf.errors() == 0", n == 0, "\n".join(perf.messages()))
        except Exception:
            self.check("perf importable", False, traceback.format_exc())

    # ------------------------------------------------------------------ driver
    def _program(self, scenario_run):
        yield from self._preflight()
        if all(c["ok"] for c in self.checks):
            yield from scenario_run(self)
        self._postflight()

    def start(self, scenario_run):
        self._gen = self._program(scenario_run)
        self._waiting = None
        # persistent: scenarios may load files / switch app templates (S-E)
        bpy.app.timers.register(self._tick, first_interval=1.0, persistent=True)
        bpy.app.timers.register(self._watchdog, first_interval=SCENARIO_TIMEOUT_S, persistent=True)

    def _tick(self):
        if self.done:
            return None
        try:
            w = self._waiting
            if w is not None:
                if w.t0 is None:
                    w.t0 = time.monotonic()
                if w.pred():
                    self._waiting = None
                elif time.monotonic() - w.t0 > w.timeout:
                    self._waiting = None
                    self.check("until: " + w.what, False, "timeout {:.1f}s".format(w.timeout))
                    self._gen.close()
                    self._postflight()
                    self.finish()
                    return None
                else:
                    return STEP_S
            delay = next(self._gen)
            if isinstance(delay, _Until):
                self._waiting = delay
                return STEP_S
            return max(STEP_S if delay is None else float(delay), 0.01)
        except StopIteration:
            self.finish()
            return None
        except Exception:
            self.exception = traceback.format_exc()
            self.log("EXCEPTION", self.exception)
            self.finish()
            return None

    def _watchdog(self):
        if not self.done:
            self.check("scenario finished in time", False, "watchdog {:.0f}s".format(SCENARIO_TIMEOUT_S))
            self.finish()
        return None

    def results(self):
        perf_errors, perf_messages, failed = None, [], []
        try:
            perf = importlib.import_module(SU_MODULE + ".perf")
            perf_errors, perf_messages = perf.errors(), perf.messages()
            failed = self.su.failed_modules()
        except Exception:
            pass
        ok = (bool(self.checks) and all(c["ok"] for c in self.checks)
              and self.exception is None and perf_errors == 0)
        return {
            "scenario": self.scenario,
            "ok": ok,
            "checks": self.checks,
            "exception": self.exception,
            "perf_errors": perf_errors,
            "perf_messages": perf_messages,
            "failed_modules": failed,
            "duration_s": round(time.monotonic() - self.t_start, 2),
            "blender": bpy.app.version_string,
        }

    def finish(self):
        if self.done:
            return
        self.done = True
        res = self.results()
        with open(os.path.join(self.out_dir, "results.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
        with open(os.path.join(self.out_dir, "status.txt"), "w", encoding="utf-8") as f:
            f.write("PASS\n" if res["ok"] else "FAIL\n")
        self.log("RESULT", "ok" if res["ok"] else "FAILED")
        self._log.close()
        bpy.ops.wm.quit_blender()


def _load_scenario(name):
    path = os.path.join(HERE, name + ".py")
    spec = importlib.util.spec_from_file_location("su_scn_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    # With an app template the splash flag comes from the TEMPLATE's userpref (BKE_blender_userdef_app_template_data_swap),
    # not from the seeded userpref.blend. --python runs before WM_init_splash_on_startup, so turning it off here
    # suppresses the splash for this run (preferences auto-save is off in the seed: nothing is persisted).
    bpy.context.preferences.view.show_splash = False
    argv = sys.argv[sys.argv.index("--") + 1:]
    scenario, out_dir = argv[0], argv[1]
    os.makedirs(out_dir, exist_ok=True)
    h = Harness(scenario, out_dir)
    try:
        mod = _load_scenario(scenario)
        run = mod.run
    except Exception:
        h.exception = traceback.format_exc()
        bpy.app.timers.register(lambda: h.finish(), first_interval=1.0)
        return
    h.start(run)


main()
