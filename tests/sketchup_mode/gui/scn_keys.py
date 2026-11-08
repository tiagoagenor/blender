# SPDX-License-Identifier: GPL-2.0-or-later
"""scn_keys (owner: A) — PLANO §5.1, AC-VCB-2..4: the keyboard works anywhere and never reaches Blender.

1. Static audit of the merged user keyconfig: in the keymaps the mode's UI can reach, every non-modal item
   bound to a letter, digit, punctuation, Space, Enter, ⌫ or Delete is one of ours (su.*) or allowed
   (navigation, undo/redo, file, full screen, view2d).
2. GUI sweep: A–Z, 0–9 and punctuation, with and without Shift, typed over the viewport, the tray, the Large
   Tool Set, the toolbar and the status bar → still one window, no active object, no Blender operator run
   (wm.operators unchanged), Medidas cleared with Esc.
3. `L` over the tray activates Linha (AC-VCB-2 neighbour).
4. AC-VCB-3: `N` Enter with the mouse over an LTS button, a toolbar button and the Measurements field
   re-types the last Linha segment (capture modal) — no button is pressed (the tool does not change).
5. AC-VCB-4: ⌫ with something typed deletes the digit and not the selection.
"""

import string

import bpy
from mathutils import Vector

AUDIT_KEYMAPS = ("Window", "Screen", "Frames", "User Interface", "3D View Generic", "3D View", "Object Mode",
                 "Object Non-modal", "View2D", "View2D Buttons List", "Header", "Region Context Menu",
                 "Screen Region Context Menu", "Property Editor")
PUNCT = {",": 'COMMA', ".": 'PERIOD', ";": 'SEMI_COLON', "-": 'MINUS', "/": 'SLASH', "[": 'LEFT_BRACKET',
         "]": 'RIGHT_BRACKET', "=": 'EQUAL', "'": 'QUOTE', "`": 'ACCENT_GRAVE', "\\": 'BACK_SLASH'}
DIGITS = ("ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE")
TYPED = set(string.ascii_uppercase) | set(DIGITS) | set(PUNCT.values()) | \
    {'SPACE', 'RET', 'NUMPAD_ENTER', 'BACK_SPACE', 'DEL', 'TAB'}


def run(h):
    su = h.su
    imp = lambda m: __import__(su.__name__ + "." + m, fromlist=["x"])
    keymap, selection, base = imp("keymap"), imp("core.selection"), imp("tools.base")
    STATE = imp("core.state").STATE
    T = h.testing
    win, area, R = h.area_regions()
    rw, ru, rt, rh = R['WINDOW'], R.get('UI'), R.get('TOOLS'), R.get('TOOL_HEADER')

    # ---------------------------------------------------------------------------------------- 1. audit
    kc = bpy.context.window_manager.keyconfigs.user
    bad = []
    for name in AUDIT_KEYMAPS:
        km = kc.keymaps.get(name)
        if km is None or km.is_modal:
            continue
        for kmi in km.keymap_items:
            if not kmi.active or kmi.type not in TYPED:
                continue
            if kmi.idname.startswith("su.") or keymap._allowed(kmi.idname):
                continue
            mods = "".join(m for m, on in (("⌃", kmi.ctrl == 1), ("⌘", kmi.oskey == 1), ("⌥", kmi.alt == 1),
                                            ("⇧", kmi.shift == 1)) if on)
            if mods.replace("⇧", ""):           # Cmd/Ctrl/Option combos are not typed text
                continue
            bad.append("{:s}: {:s}{:s} → {:s}".format(name, mods, kmi.type, kmi.idname))
    h.check("teclas digitáveis só chegam ao modo (auditoria do keymap)", not bad, bad[:20])

    # ---------------------------------------------------------------------------------------- 2. sweep
    areas = [("viewport", lambda: h.region_xy(rw, 0.5, 0.5))]
    if ru is not None and ru.width > 40:
        areas.append(("Bandeja", lambda: h.region_xy(ru, 0.5, 0.45)))
    if rt is not None and rt.width > 20:
        areas.append(("LTS", lambda: h.region_xy(rt, 0.5, 0.5)))
    if rh is not None and rh.height > 10:
        areas.append(("toolbar", lambda: h.region_xy(rh, 0.5, 0.5)))
    areas.append(("status", lambda: (area.x + int(area.width * 0.5), max(2, area.y // 2))))
    T.reset_model()
    keys = list(string.ascii_uppercase) + list(DIGITS) + list(PUNCT.values())
    ops0 = len(bpy.context.window_manager.operators)
    for label, where in areas:
        h.move(*where())
        for shift in (False, True):
            for k in keys:
                uni = k.lower() if len(k) == 1 else None
                if k in DIGITS:
                    uni = str(DIGITS.index(k)) if not shift else None
                elif k in PUNCT.values() and not shift:
                    uni = next(c for c, t in PUNCT.items() if t == k)
                if shift and uni:
                    uni = uni.upper()
                h.key(k, unicode=uni, shift=shift)
            yield 0.4
            h.key('ESC')
            h.key('ESC')
            yield 0.3
            ws = len(bpy.context.window_manager.windows)
            d = h.state()
            h.check("{:s}{:s}: sem popup/janela, sem objeto ativo, nada rodando".format(label, " +Shift" if shift else ""),
                    ws == 1 and d["active_object"] is None and not d["running"] and d["vcb_buffer"] == "",
                    (ws, d["active_object"], d["running"], d["vcb_buffer"], d["tool"]))
    ops = [op.bl_idname for op in bpy.context.window_manager.operators][ops0:]
    foreign = [o for o in ops if not o.startswith("SU_OT_")]
    h.check("nenhum operador do Blender executado pela varredura", not foreign, foreign[:10])
    h.check("varredura não criou geometria", h.stats().get("edges", 0) == 0, h.stats().get("edges"))
    T.reset_model()

    # ---------------------------------------------------------------------------------------- 3. L over the tray
    if ru is not None and ru.width > 40:
        h.move(*h.region_xy(ru, 0.5, 0.45))
        h.key('SPACE')
        yield 0.3
        h.key('L', unicode='l')
        yield 0.4
        h.check("L sobre a Bandeja ativa Linha", h.state()["tool"] == "su.line", h.state()["tool"])

    # ---------------------------------------------------------------------------------------- 4. AC-VCB-3
    h.move(*h.region_xy(rw, 0.5, 0.5))
    h.key('L', unicode='l')
    yield 0.3
    h.glide(*h.world_xy((0.0, 0.0, 0.0)))
    yield 0.3
    h.click()
    yield 0.3
    h.glide(*h.world_xy((1.0, 0.0, 0.0)))
    yield 0.3
    h.type_text("2")
    yield 0.5
    h.key('ESC')
    yield 0.3

    def seg_len():
        s = h.stats()
        return round(s["bbox"][1][0] - s["bbox"][0][0], 4) if s.get("bbox") else None
    h.check("segmento inicial de 2 m", seg_len() == 2.0, seg_len())
    targets = []
    if rt is not None and rt.width > 20:
        targets.append(("botão do LTS", h.region_xy(rt, 0.25, 0.80)))
    if rh is not None and rh.height > 10:
        targets.append(("botão da toolbar", h.region_xy(rh, 0.30, 0.5)))
    targets.append(("campo Medidas", (area.x + area.width - 120, max(2, area.y // 2))))
    for i, (label, xy) in enumerate(targets):
        n = 3 + i
        h.move(*xy)
        yield 0.3
        h.type_text(str(n))
        yield 0.6
        h.check("`{:d}` Enter sobre o {:s} redigita (captura modal)".format(n, label), seg_len() == float(n), seg_len())
        h.check("… e não aciona o {:s} (ferramenta continua Linha)".format(label), h.state()["tool"] == "su.line",
                h.state()["tool"])
        h.check("… e nenhuma janela/popup", len(bpy.context.window_manager.windows) == 1)

    # ---------------------------------------------------------------------------------------- 5. AC-VCB-4
    h.move(*h.region_xy(rw, 0.5, 0.5))
    h.key('SPACE')
    yield 0.3
    h.glide(*h.world_xy((1.0, 0.0, 0.0)))
    yield 0.3
    h.click()
    yield 0.4
    n_sel = len(selection.get())
    h.key('ONE', unicode='1')
    h.key('COMMA', unicode=',')
    yield 0.3
    h.key('BACK_SPACE')
    yield 0.3
    d = h.state()
    h.check("⌫ com texto apaga o dígito", d["vcb_buffer"] == "1", d["vcb_buffer"])
    h.check("… e não exclui a seleção", n_sel > 0 and len(selection.get()) == n_sel and h.stats()["edges"] >= 1,
            (n_sel, len(selection.get()), h.stats()["edges"]))
    h.key('ESC')
    h.key('ESC')
    yield 0.3
