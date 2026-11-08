# SPDX-License-Identifier: GPL-2.0-or-later
"""A: preferences backup/restore (PLANO §5.2, S-E) and the Mac mouse items of the Window keymap."""

import json
import os
import unittest

import bpy

from su import keymap, prefs


class TestPrefs(unittest.TestCase):
    def setUp(self):
        self.inputs = bpy.context.preferences.inputs
        self.saved = prefs.originals()
        prefs.backup()                 # fresh backup of the current values

    def tearDown(self):
        prefs.restore()
        prefs._orig.update(self.saved)
        prefs._save_file()

    def test_backup_file_and_restore(self):
        orig = self.inputs.use_zoom_to_mouse
        self.assertTrue(os.path.isfile(prefs.path()))
        with open(prefs.path(), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["inputs.use_zoom_to_mouse"], orig)
        self.inputs.use_zoom_to_mouse = not orig          # an owner changes it (G)
        prefs.restore()
        self.assertEqual(self.inputs.use_zoom_to_mouse, orig)
        self.assertFalse(os.path.isfile(prefs.path()))

    def test_stale_backup_wins(self):
        """A previous session died without restoring: its file holds the user's real value."""
        orig = self.inputs.invert_zoom_wheel
        prefs.restore()
        with open(prefs.path(), "w", encoding="utf-8") as f:
            json.dump({"inputs.invert_zoom_wheel": orig}, f)
        self.inputs.invert_zoom_wheel = not orig          # value left modified by the dead session
        prefs.backup()
        prefs.restore()
        self.assertEqual(self.inputs.invert_zoom_wheel, orig)

    def test_track_extra_key(self):
        self.assertTrue(prefs.track("view", "show_tooltips"))
        self.assertIn("view.show_tooltips", prefs.originals())
        self.assertFalse(prefs.track("view", "no_such_pref"))


class TestMouseItems(unittest.TestCase):
    def test_context_menu_items(self):
        items = keymap.window_items()
        cm = [(it[1]["type"], it[1]["value"], it[1].get("ctrl", False)) for it in items if it[0] == "su.context_menu"]
        self.assertIn(('LEFTMOUSE', 'CLICK', True), cm)
        self.assertIn(('RIGHTMOUSE', 'PRESS', False), cm)
        # vcb items still first
        self.assertEqual([it[0] for it in items[:5]], ["su.vcb_key"] * 5)


if __name__ == "__main__":
    unittest.main()
