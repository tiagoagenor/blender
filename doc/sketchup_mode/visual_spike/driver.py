# Screenshot driver: waits for the template to finish its setup ticks, resizes the toolbar/tray regions by
# simulated edge drags (needs --enable-event-simulate), takes a screenshot and quits.
import bpy, sys, os, traceback
OUT = sys.argv[sys.argv.index("--") + 1]
TOOLS_W = float(os.environ.get("SU_TOOLS_W", "92"))   # logical px
DIV = float(os.environ.get('SU_COORD_DIV','1'))
UI_W = float(os.environ.get("SU_UI_W", "300"))
LOG = os.path.join(os.path.dirname(OUT), "..", "raw", "driver_log.txt")
def P(*a):
    with open(LOG, "a") as f: print(*a, file=f)
Q = []
def area_regions():
    win = bpy.context.window_manager.windows[0]
    a = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
    return win, a, {r.type: r for r in a.regions}
def drag(kind):
    def f():
        win, a, R = area_regions(); ps = bpy.context.preferences.system.pixel_size
        r = R[kind]; y = r.y + r.height // 2
        if kind == 'TOOLS':
            x0 = r.x + r.width - 1; x1 = r.x + int(TOOLS_W * ps)
        else:
            x0 = r.x + 1; x1 = r.x + r.width - int(UI_W * ps) - 2
        P(kind, "before", r.x, r.width, "drag", x0, "->", x1, "win", win.width, win.height, "ps", ps)
        x0, x1, y = int(x0/DIV), int(x1/DIV), int(y/DIV)
        win.event_simulate('MOUSEMOVE', 'NOTHING', x=x0, y=y)
        f.args = (x0, x1, y)
    def g():
        win = bpy.context.window_manager.windows[0]; x0, x1, y = f.args
        win.event_simulate('LEFTMOUSE', 'PRESS', x=x0, y=y)
    def h():
        win = bpy.context.window_manager.windows[0]; x0, x1, y = f.args
        for i in range(1, 11):
            win.event_simulate('MOUSEMOVE', 'NOTHING', x=int(x0 + (x1 - x0) * i / 10), y=y)
    def k():
        win = bpy.context.window_manager.windows[0]; x0, x1, y = f.args
        win.event_simulate('LEFTMOUSE', 'RELEASE', x=x1, y=y)
    return [f, g, h, k]
def park():
    win, a, R = area_regions(); r = R['WINDOW']
    win.event_simulate('MOUSEMOVE', 'NOTHING', x=r.x + int(r.width * 0.8), y=r.y + int(r.height * 0.75))
def report():
    win, a, R = area_regions()
    P("final", {k: (v.x, v.width, v.height) for k, v in R.items()})
def shot():
    win = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=win):
        bpy.ops.screen.screenshot(filepath=OUT)
def quit_(): bpy.ops.wm.quit_blender()
Q[:] = drag('TOOLS') + drag('UI') + [park, report, None, shot, quit_]
def tick():
    if not bpy.app.driver_namespace.get("su_ready"):
        return 0.3
    if not Q: return None
    fn = Q.pop(0)
    try:
        if fn: fn()
    except Exception: P(traceback.format_exc())
    return 0.35
bpy.app.timers.register(tick, first_interval=1.0)
