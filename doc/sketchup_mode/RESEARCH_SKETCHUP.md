# SketchUp UX Reference Spec (for the Blender "SketchUp mode" app template)

Researched 2026-11-08. The **current** desktop release is **SketchUp 2027.0** (27.0.264, released Oct 21 2026).
It replaced the separate Mac and Windows UIs with one **unified, Windows-style interface**.
SketchUp 2024, 2025 and 2026 are the "classic" generation: a Windows UI and a separate macOS UI.
This spec documents the classic Windows default **and** the 2027 changes.

How each claim is labelled:
- **[H]**: official help.sketchup.com page, URL given inline.
- **[QRC]**: official Quick Reference Card 2027. Windows: https://download.sketchup.com/QRC2027/HC-QRC2027-en-SU-win.pdf, Mac: https://download.sketchup.com/QRC2027/HC-QRC2027-en-SU-mac.pdf
- **[PX]**: RGB value I measured from the pixels of an official screenshot. These are the numbers to use for visual matching.
- **[F]**: SketchUp forum, SketchUcation or GitHub post.
- **[K]**: well-known SketchUp behaviour that I did not re-verify against a source in this session. Treat it as likely, not certain.

Reference images are in `ref_images/` (see §8).

---

## 0. TOP 20 must-have behaviours

1. **Middle-drag = Orbit, Shift+middle-drag = Pan, wheel = Zoom toward the cursor, double-click middle = re-center** on the clicked point. All of these work *while any tool is active* and never cancel the tool [QRC][H viewing-model].
2. **Orbit is gravity-weighted (turntable)**: blue (Z) always stays vertical. The pivot is the geometry point under the cursor when the drag starts, or the screen center over empty space [F]. Holding Ctrl (Win) / Option (Mac) lets the camera roll [H]. The 2027 QRC says Alt; see §3.
3. **Scroll up = zoom in, scroll down = zoom out**, centered on the cursor [H viewing-model].
4. **Left button always runs the current tool. Tools are click-move-click**, not drag (drag also works: "Auto Detect" click style) [H drawing prefs]. Right-click opens a context menu.
5. **Esc cancels the current operation** and stays in the tool. **Space = Select tool** from anywhere.
6. **Single-letter tool keys**: Space Select, L Line, R Rectangle, C Circle, A 2-Point Arc, P Push/Pull, F Offset, M Move, Q Rotate, S Scale, E Eraser, B Paint Bucket, T Tape Measure, O Orbit, H Pan, Z Zoom, Shift+Z Zoom Extents, G Make Component, K Back Edges, Shift+S Search, Shift+Space Lasso [H default-keyboard-shortcuts].
7. **Measurements box (VCB)** at the bottom right. Type at any time, no click into the field needed, then Enter. You can re-type the value repeatedly until the next operation. Units can be typed (`10m`, `3'6"`, `25cm`). Multiple values are comma-separated (`2m,3m`). `[x,y,z]` = absolute coordinates, `<x,y,z>` = relative [H].
8. **Inference engine** with colored snap markers and yellow ScreenTip labels. Endpoint = green dot, Midpoint = cyan dot, On Edge = red square, On Face = blue diamond, Intersection = red X, Center = blue dot. Direction lines are red/green/blue along an axis and magenta for parallel/perpendicular. Inside a group or component, every point marker turns **magenta** and the tip text gains "in Group" / "in Component" [H].
9. **Inference locking**: hold **Shift** to lock the current inference. **Arrow keys** lock a direction or plane: Right = Red (X), Left = Green (Y), Up = Blue (Z), Down = parallel/perpendicular (magenta) [H].
10. **Line tool chains segments**: each endpoint starts the next segment. A closed coplanar loop **automatically creates a face**, and drawing a line across a face **splits it** ("sticky geometry").
11. **Push/Pull**: click a face, move, click. Typing a distance + Enter makes it exact. **Double-click** another face repeats the last distance. **Ctrl (Win) / Option (Mac)** pulls a *new* face and leaves the original in place. Pushing fully through to a parallel back face cuts a hole.
12. **Move**: click a point, move, click. **Ctrl/Option toggles copy**. After a copy, typing `5x` (or `5*`) makes an external array and `/5` (or `5/`) an internal array [QRC][H measurements-box]. Alt (Win) / Cmd (Mac) = auto-fold.
13. **Rotate**: a protractor appears, colored by plane (blue protractor = rotation about Z). The clicks are: center, start of angle, end of angle. Type an angle in degrees or a slope like `3:12`. Ctrl/Option = rotate a copy, and arrays work after it.
14. **Select tool**: click selects one entity. Double-click a face selects the face plus its edges; double-click an edge selects the edge plus its faces. Triple-click selects everything connected. Ctrl = add, Shift = toggle, Ctrl+Shift = subtract. **Drag left-to-right = window** (solid rectangle, only entities fully inside). **Drag right-to-left = crossing** (dashed rectangle, anything touched). Click on empty space deselects. Double-click a group or component enters it.
15. **Selection look**: selected edges are drawn **pure blue (0,0,255)**. Selected faces get a **blue dot stipple** over their shading. Selected groups/components get a blue bounding box [PX].
16. **Default style ("Simple Style")**: front faces white (255,255,255), back faces blue-gray **(164,178,187)**, edges black about 1 px, profiles off. Sky is a **blue gradient**: about **#1EA6DD at the top, lightening to #BFE5F5 at the horizon**. Below the horizon is flat **gray background #BFBFC6 (191,191,198)** [PX][F].
17. **Axes**: red X, green Y, blue Z through the origin. Positive halves are **solid lines**, negative halves are **dotted lines**. Each axis spans the whole viewport. Color is a dark saturated **(178,0,0) / (0,178,0) / (0,0,178)** [PX].
18. **Camera**: perspective by default with **35° field of view** (vertical) [F, blog.sketchup.com]. Default view is a 3/4 aerial view of the origin with a 2D scale figure standing near it.
19. **Status bar** (bottom): geo-location pin icon, Model Info / credits icon, then the tool hint text, e.g. *"Click or drag to select objects. Shift = Add/Subtract. Ctrl = Add. Shift + Ctrl = Subtract."* The **Measurements** label and box sit at the far right [PX][H user-interface].
20. **Groups and components isolate geometry.** Loose geometry sticks to and splits other loose geometry; a group never does. Double-click enters a group's context, and the rest of the model fades. Click outside the group or press Esc to leave.

---

## 1. Default UI layout

### 1.1 Window regions, classic Windows (2023–2026)

Seen in `ref_images/sketchup_default_ui_1_win2023_simple_template.png`, SketchUp Pro 2023, Windows 11. From top to bottom:

1. **Title bar**: `Untitled - SketchUp Pro 2023` with the app icon on the left.
2. **Menu bar**: File, Edit, View, Camera, Draw, Tools, Window, Extensions, Help [H user-interface (2025 archive)].
3. A small row with a Warehouse toolbar (4 icons). It is visible in that screenshot but is not a default.
4. **Getting Started toolbar**: a single horizontal row docked at the top, about 32 px icons. Background (239,239,240) [PX].
5. **Drawing area**: the whole remaining space between the toolbar and the status bar on the left side.
6. **Default Tray** docked on the **right**, about 30% of the width in that screenshot (about 330 px of 1117). It has the title "Default Tray" and pin/close buttons. Each panel is a collapsible bar with a ▶ triangle and an ✕ on the right. The visible order is: Entity Info, Materials, Components, Styles (expanded) … [PX].
7. **Status bar** at the bottom, about 22 px high, background (240,240,240). From the left: a geo-location pin icon (grey), an ⓘ Model Info / credits icon, then the tool hint text. A divider follows, then the label **"Measurements"** and an input field at the far right [PX].

The **Large Tool Set is NOT shown by default** on classic Windows. Only Getting Started is shown. Users enable the Large Tool Set via View > Toolbars, and it can only dock on the left [H toolbars]. A forum feature request asks for it to be the default: https://forums.sketchup.com/t/ux-have-the-large-toolset-displayed-by-default-instead-of-getting-started/60723

**Classic macOS (≤2026)** used a different layout [H mac-os-older-versions]:
- One customizable toolbar at the top of the window (View > Customize Toolbar).
- Floating "tool palettes" (View > Tool Palettes > Large Tool Set) that could not be docked.
- Panels were independent floating "dialogs", toggled from the Window menu, which could stack and snap together.
- The menu bar is the macOS global menu with an extra **SketchUp** menu (About, Settings/Preferences).

### 1.2 Window regions, SketchUp 2027 unified (Win + Mac)

Seen in `sketchup_default_ui_2_v2027_empty_scene_large_toolset.png`, `sketchup_default_ui_3_v2027_full_window.png` and `sketchup_default_ui_4_v2027_mac_menubar.png`. Sources: [H user-interface] https://help.sketchup.com/en/sketchup/user-interface and [H release notes 2027] https://help.sketchup.com/en/release-notes/sketchup-desktop-20270

- **Menu bar**:
  - Windows: File, Edit, View, Camera, Draw, Tools, **Procedures** (new in 2027), Window, Extensions, Help.
  - Mac: the same list, preceded by the SketchUp app menu.
- **Getting Started toolbar** along the top, with flat line icons in blue and red. Toolbar background **(241,241,246) #F1F1F6** [PX].
- **Model tabs**: one tab per open model with an ✕ and a "+" button. **Scene tabs** sit below them, with a magnifier/search button and a "+" button. Both are new in 2027.
- **Large Tool Set**: a 2-column vertical strip docked on the **left** in every official 2027 screenshot. The text of the help page says "appears on the right side", which contradicts its own screenshots; use the left. The selected tool is drawn as a rounded light-blue square with a blue outline.
- **Drawing area** in the center.
- **Default Tray** on the right. Title row "Default Tray" with pin and ✕. Each panel is a row with a "›" chevron (collapsed) or "⌄" (expanded), the panel name, and an ✕ box at the right.
  - Panel row background **(224,225,233)** [PX].
  - Tray body (244,247,252) [PX].
- **Status bar**: pin icon, ⓘ icon, hint text, then the Measurements field at the right. The field has an empty light box and no visible "Measurements" label in the 2027 screenshot [PX].

### 1.3 Getting Started toolbar, exact left-to-right order

**SketchUp 2023 Windows** (from the screenshot; separators shown as `|`):

`Search | Select▾ | Eraser | Line▾ | 2-Point Arc▾ | Rectangle▾ | Push/Pull | Offset | Move | Rotate | Scale | Flip | Tape Measure | Paint Bucket | Orbit | Pan | Zoom | Zoom Extents | 3D Warehouse | Extension Warehouse | Send to LayOut | Extension Manager | Account (user)▾`

Notes:
- `▾` marks a flyout:
  - Select ▾ holds Select / Lasso.
  - Line ▾ holds Line / Freehand.
  - Arc ▾ holds Arc, 2-Point Arc, 3-Point Arc, Pie.
  - Rectangle ▾ holds Rectangle, Rotated Rectangle, Circle, Polygon.
- Separators split the toolbar into groups: [Search] [Select] [Eraser, Line, Arc, Shapes] [Push/Pull … Flip] [Tape, Paint] [Orbit … Zoom Extents] [Warehouse group] [Account].

**SketchUp 2027** (from `sketchup_getting_started_toolbar_v2027.png`; floating title "Getting Started"):

`Search | Select▾ | Eraser | Line▾ | 2-Point Arc▾ | Rectangle▾ | Push/Pull | Offset | Move | Rotate | Scale | Flip | Tape Measure | Paint Bucket | Orbit | Pan | Zoom | Zoom Extents | 3D Warehouse | Extension Warehouse | Send to LayOut | Comment (Collaboration) | Account▾`

The help page lists the toolbar as "Search, Select, Eraser, Line, Arc, Rectangle, Offset, Move, Rotate, Scale, Flip, Tape Measure, Paint Bucket, Rotate, Pan, Zoom, Zoom Extents, 3D Warehouse, Extension Warehouse, Send to LayOut, Comments, User Info" [H toolbars]. That text has errors: it leaves out Push/Pull and writes "Rotate" where it means Orbit. The screenshot is authoritative.

Icon colors:
- Tool glyphs are dark navy (about (0,66,110)) and cyan-blue (about (0,158,223)), with **red (255,0,0) accents** for motion: Move arrows, Rotate, Orbit, Push/Pull arrow, Scale arrow.

### 1.4 Large Tool Set, 2 columns, exact grid (SketchUp 2027)

Read from `sketchup_large_tool_set_v2027_crop.png` and matching the QRC 2027 sheet. `—` marks a horizontal separator.

| Row | Left column | Right column |
|---|---|---|
| 1 | Select (Space) | Lasso (Shift+Space) |
| 2 | Paint Bucket (B) | Eraser (E) |
| 3 | Make Component (G) | Tag (tag tool) |
| — | | |
| 4 | Line (L) | Freehand |
| 5 | Rectangle (R) | Rotated Rectangle |
| 6 | Circle (C) | Polygon |
| 7 | Arc | 2 Point Arc (A) |
| 8 | 3 Point Arc | Pie |
| — | | |
| 9 | Move (M) | Push/Pull (P) |
| 10 | Rotate (Q) | Follow Me |
| 11 | Scale (S) | Offset (F) |
| 12 | Axes | Flip |
| — | | |
| 13 | Tape Measure (T) | Dimensions |
| 14 | Protractor | Text |
| 15 | Section Plane | 3D Text |
| — | | |
| 16 | Orbit (O) | Pan (H) |
| 17 | Zoom (Z) | Zoom Window |
| 18 | Zoom Extents (Shift+Z) | Previous |
| — | | |
| 19 | Position Camera | Walk |
| 20 | Look Around | Field of View (2027) |
| — | | |
| 21 | 3D Warehouse | Extension Warehouse |
| 22 | Send to LayOut | Comment |

Classic (2017–2026) Large Tool Set differences [K]:
- Row 1 had **Select | Make Component**, row 2 **Paint Bucket | Eraser**. There was no Lasso or Tag tool before about 2024/2025.
- **Axes and Section Plane** sat in the construction group (Tape|Dimension, Protractor|Text, Axes|3D Text) and the camera group ended with **Look Around | Section Plane**.
- The QRC 2027 printed layout places Axes|3D Text in the construction group and Flip|Field of View after it, which differs slightly from the toolbar crop. When cloning, copy the crop above.

### 1.5 Main menu bar (most important items)

[K] unless marked; Windows shortcuts shown.
- **File**: New (Ctrl+N), New from Template…, Open… (Ctrl+O), Save (Ctrl+S), Save As…, Save A Copy As…, Save As Template… [H setting-templates], Revert, Send to LayOut, 3D Warehouse ▸, Add Location… [H], Import…, Export ▸ (3D Model, 2D Graphic, Section Slice, Animation), Print… (Ctrl+P), recent files, Exit.
- **Edit**:
  - Undo (**Alt+Backspace** default, Ctrl+Z also works [H erasing-and-undoing]), Redo (Ctrl+Y on Win, Cmd+Shift+Z on Mac).
  - Cut, Copy, Paste, Paste In Place, Delete, Delete Guides [H using-guides].
  - Select All (Ctrl+A / Cmd+A), Select None / Deselect All (**Ctrl+T** on Win, **Shift+Cmd+A** on Mac [H selecting-geometry]), Invert Selection (Ctrl+Shift+I).
  - Hide, Unhide ▸ (Selected / Last / All), Lock / Unlock.
  - Make Component… (G), **Make Group** [H grouping-geometry], Close Group/Component, Intersect Faces ▸ (With Model / With Selection / With Context), Flip [H], Purge Unused [H 2026 notes].
  - A dynamic last item named after the selection, e.g. "Face", "Group" or "N Entities", with Explode etc.
- **View**: Toolbars… [H], Scene Tabs, Hidden Geometry, Hidden Objects [H softening], Section Planes, Section Cuts, Section Fill, **Axes**, **Guides**, Shadows, Fog, Edge Style ▸ (Edges, **Back Edges (K)**, Profiles, Depth Cue, Extension), Face Style ▸ (X-ray, Wireframe, Hidden Line, Shaded, Shaded With Textures, Monochrome, Photoreal Materials), Component Edit ▸ (Hide Rest of Model, Hide Similar Components), Animation ▸.
- **Camera**: Previous, Next [H viewing-model], Standard Views ▸ (Top, Bottom, Front, Back, Left, Right, Iso) [H], Parallel Projection, **Perspective** (default), Two-Point Perspective [H], Match New Photo…, Orbit (O), Pan (H), Zoom (Z), Field of View [H], Zoom Window, Zoom Extents (Shift+Z), Position Camera, Walk, Look Around, Image Igloo (I) [H shortcuts].
- **Draw**: Lines ▸ (Line, Freehand) [H freehand], Arcs ▸ (Arc, 2 Point Arc, 3 Point Arc, Pie) [H arcs], Shapes ▸ (Rectangle, Rotated Rectangle, Circle, Polygon) [H basic-shapes], Sandbox ▸.
- **Tools**: Select, Lasso, Eraser, Tag, Paint Bucket, Move, Rotate, Scale, Flip, Push/Pull, Follow Me, Offset, Solid Tools ▸, Tape Measure, Protractor, Axes, Dimensions, Text, 3D Text, Section Plane, Advanced Camera Tools ▸, Sandbox ▸.
- **Procedures** (2027 only): Procedural Follow Me, Copy Along, Procedural Solid Tools [H 2027].
- **Window**:
  - Classic Windows: Default Tray ▸ (lists each panel), Manage Trays…, New Tray…, Model Info, Preferences, 3D Warehouse, Extension Manager, Ruby Console, Component Options/Attributes.
  - 2027: Default Tray ▸, Manage Trays…, New Tray…, Close Panel or Dialog (Cmd+.), Model Info, 3D Warehouse…, Collaboration Bar, Component Options, Component Attributes [PX, older_vs_new screenshot].
  - Classic Mac: listed every dialog (Entity Info ⌘I, Materials ⇧⌘C, Components, Styles, Environments, Tags, Outliner, Scenes, Show Fonts ⌘T, Shadows, Fog, Match Photo, Soften Edges, Instructor, Overlays) [PX].
- **Extensions**: Extension Warehouse, Extension Manager, Developer ▸ (Ruby Console), installed extensions.
- **Help**: Welcome to SketchUp, Knowledge Center, Contact Us, License, Check for Update, About, Sign out [H].

### 1.6 Default Tray (panels, in order)

Panels available: Entity Info, Materials, Components, Styles, Tags, Scenes, Shadows, Fog, Match Photo, Soften Edges, Overlays, Instructor, Outliner. 2025+ adds **Environments** and 2027 adds **Hatch Patterns** [H dialog-boxes-and-trays].

Observed default-tray order:
- **2023 (Windows)**: Entity Info, Materials, Components, Styles … The rest is cut off in the screenshot. Classic order [K]: … Tags, Shadows, Scenes, Instructor.
- **2027 fresh "Untitled"** [PX]: Entity Info, Materials, Components, Styles, *(Environments, Tags, hidden behind a callout)*, Shadows, Scenes, Hatch Patterns, Soften Edges, Outliner, Instructor.
- **2027 Labs build** [PX]: Entity Info, Materials, Components, Styles, Environments, Tags Manager, Shadows, Scenes, Instructor, Hatch Pattern, Outliner.

**Recommended clone order**: Entity Info, Materials, Components, Styles, Tags, Scenes, Shadows, Soften Edges, Outliner, Instructor. All collapsed except one; Styles was expanded in the 2023 screenshot.

### 1.7 Status bar & Measurements box (VCB)

- Layout, from left: [geo pin icon][ⓘ credits/Model Info icon] | **hint text for current tool** | … | **"Measurements"** label + text field at the right [PX][H user-interface].
- On Windows the label inside/left of the box changes per tool [K]. Mac shows the label above or beside the box.

| Tool | Label in the box |
|---|---|
| Line | Length |
| Rectangle | Dimensions (`L,W`) |
| Circle / Polygon | Sides, before the first click (shows 24 or 6); Radius, after the center click |
| 2-Point Arc | Length, then Bulge |
| Arc (center) | Radius, then Angle |
| Push/Pull | Distance |
| Move | Distance |
| Offset | Distance |
| Rotate | Angle |
| Scale | Scale |
| Tape Measure | Length |
| Protractor | Angle |
| Zoom | Field of View |
| Look Around | Eye Height |

- Typing never requires focusing the box: keystrokes go to the VCB while a tool is active. Enter commits. You can re-enter and adjust the last operation until another operation starts [H basic-shapes][H using-measurements-box].
- Unit suffixes: `"` inches, `'` feet, `mm`, `cm`, `m`. Array syntax: `3x` or `3*` (external), `3/` or `/3` (internal) [H using-measurements-box].
- **Status hint texts** observed:
  - Select on Windows: "Click or drag to select objects. Shift = Add/Subtract. Ctrl = Add. Shift + Ctrl = Subtract." [PX 2023].
  - Select on Mac: "Click or drag to select objects. Shift = Add/Subtract. Option = Add. Shift + Option = Subtract." [PX 2027 Mac].
  - Others [K, approximate]:
    - Line: "Select start point." then "Select end point or enter value."
    - Push/Pull: "Pick face to push or pull. Ctrl = toggle create new starting face."
    - Move: "Select objects to move. Ctrl = toggle Copy, Alt = toggle Auto-fold…"

---

## 2. Keyboard shortcuts

### 2.1 Default tool / command shortcuts

Official list, identical letter keys on Win and Mac [H https://help.sketchup.com/en/default-keyboard-shortcuts]:

| Tool | Key |
|---|---|
| Select | **Space** |
| Lasso Select | **Shift+Space** |
| Paint Bucket | **B** |
| Eraser | **E** |
| Line | **L** |
| Rectangle | **R** |
| Circle | **C** |
| 2 Point Arc | **A** |
| Move | **M** |
| Push/Pull | **P** |
| Rotate | **Q** |
| Scale | **S** |
| Offset | **F** |
| Tape Measure | **T** |
| Orbit | **O** (also middle-drag) |
| Pan | **H** (also Shift+middle-drag) |
| Zoom | **Z** (also scroll wheel) |
| Zoom Extents | **Shift+Z** |
| Make Component | **G** |
| Image Igloo | **I** |
| Back Edges (view toggle) | **K** |
| Search | **Shift+S** |

**No default shortcut** [H measuring-angles][QRC]: Polygon, Freehand, Rotated Rectangle, Arc (center), 3-Point Arc, Pie, Follow Me, Flip, Protractor, Dimensions, Text, 3D Text, Axes, Section Plane, Zoom Window, Previous, Position Camera, Walk, Look Around, Make Group, Hide.

Edit and other commands:

| Command | Windows | Mac | Source |
|---|---|---|---|
| Undo | Alt+Backspace (default); Ctrl+Z also works | Cmd+Z | [H] |
| Redo | Ctrl+Y | Cmd+Shift+Z | [myarchitectai] |
| Select All | Ctrl+A | Cmd+A | [H] |
| Deselect All | Ctrl+T | Shift+Cmd+A | [H] |
| Invert Selection | Ctrl+Shift+I | — | [K] |
| Cut / Copy / Paste | Ctrl+X / C / V | Cmd+X / C / V | [K] |
| Delete selection | Delete | Delete | [K] |
| New / Open / Save / Print | Ctrl+N / O / S / P | Cmd+N / O / S / P | [K] |

Unverified Mac-specific camera shortcuts [F]: Walk = Cmd+/, Look Around = Cmd+. ; Cmd+. is "Close Panel or Dialog" in the 2027 Window menu.

Older third-party claims, unconfirmed:
- Windows: Ctrl+Shift+W = Zoom Window; Ctrl+Shift+E = Zoom Extents.
- Mac: Cmd+1…6 = standard views.

### 2.2 Modifiers inside tools

Official QRC 2027 tables. Win key / Mac key.

| Tool | Modifier / input | Effect |
|---|---|---|
| **Select** | Ctrl / Option | add to selection |
| | Shift | toggle add/subtract |
| | Ctrl+Shift / Shift+Option | subtract |
| **Lasso** | Shift | add/subtract |
| | Alt / Option | add |
| | Shift+Alt / Shift+Option | subtract |
| **Line (L)** | Shift | lock current inference direction ([H] and Mac QRC; the Win QRC says "Alt") |
| | Arrows | Up = blue, Right = red, Left = green, Down = parallel/perpendicular |
| | type value + Enter | length |
| | Alt / Cmd *after the first click* | cycle linear inferences: All On → All Off → Parallel/Perpendicular only [H drawing-basics] |
| **Rectangle (R)** | Alt / Option | draw from center (2027) |
| | `L,W` + Enter | dimensions |
| | `-24,-24` | negative values flip direction [H] |
| | Shift | lock Square / Golden Section inference [H] |
| **Rotated Rectangle** | Shift | lock direction/plane |
| | Alt / Cmd | lock the plane for the first edge, or set the protractor baseline |
| | `width,angle` + Enter | width and angle (e.g. `90,20`) |
| **Circle (C)** | Shift | lock inferences |
| | `N` + Enter before drawing (or `Ns` after) | number of sides (default **24**) |
| | number + Enter after drawing | radius |
| **Polygon** | `N` + Enter | sides (default **6**, min 3) [K] |
| | number + Enter | radius |
| **2 Point Arc (A)** | number + Enter | bulge |
| | `Nr` + Enter | radius |
| | `Ns` + Enter | segments (arc default **12** segments [H arcs]) |
| | Ctrl+ `+` / `-` (Option on Mac) | more / fewer segments |
| | `Nc` | base segments on a circle of N sides [H] |
| **Push/Pull (P)** | Ctrl / Option | push/pull a copy of the face (new starting face; original stays) |
| | double-click a face | repeat last distance |
| | Ctrl/Option + double-click | stack another extrusion of the same distance [H] |
| | number + Enter | distance |
| **Offset (F)** | Alt / Cmd | allow overlaps |
| | number + Enter | distance |
| | double-click another face | repeat the same offset [H] |
| **Move (M)** | Ctrl / Option | toggle copy (multiple consecutive copies) |
| | Shift | lock inference direction |
| | Alt / Cmd | auto-fold |
| | Arrows | axis lock |
| | distance + Enter | distance; `[x,y,z]` absolute, `<x,y,z>` relative coordinates |
| | after a copy: `Nx` / `N*` | external array of N |
| | after a copy: `/N` / `N/` | internal array of N |
| | Alt / Cmd while hovering a group | cycle bounding-box grips: corners, edge midpoints, face centers, center [H moving] |
| **Rotate (Q)** | Ctrl / Option | rotate a copy (arrays then work) |
| | Shift | lock plane |
| | Alt / Cmd | free the protractor from the plane |
| | arrows | pick plane |
| | angle + Enter | angle |
| | `rise:run` | slope |
| | drag from vertex | define a custom axis (fold) |
| **Scale (S)** | Ctrl / Option | scale about center |
| | Shift | uniform (toggle) |
| | `1.5` + Enter | factor |
| | `10m` | length |
| | `2,1,1` | per axis |
| **Flip** | Ctrl / Option | copy mode |
| | Alt / Cmd | axes mode |
| | Arrows | Left green, Right red, Up blue |
| **Follow Me** | Alt / Cmd | use the face perimeter as the path |
| **Eraser (E)** | Shift | hide |
| | Ctrl / Option | soften + smooth |
| | Ctrl+Shift (Win) / Option+Shift (Mac) | unsoften / unsmooth (help says Alt/Cmd) |
| **Paint Bucket (B)** | Ctrl / Option | fill all matching *adjacent* faces |
| | Shift | replace the material on all matching faces in the model |
| | Ctrl+Shift / Option+Shift | replace on the same object |
| | Alt / Cmd (hold) | sample material (eyedropper) |
| **Tape Measure (T)** | Ctrl / Option | toggle guide creation ↔ measure only (cycles Guide Line → Guide Point → Measure [H measuring-distance]) |
| | arrows | axis lock |
| | measure, type a new length, Enter | resize the model (with a confirmation dialog) |
| **Protractor** | Ctrl / Option | toggle guide creation |
| | arrows | lock plane |
| | Shift | lock plane |
| | Alt / Cmd | move off-plane |
| **Orbit (O)** | Shift (hold) | Pan |
| | Ctrl/Option ([H]) or Alt ([QRC 2027]) | disable gravity (allow roll) |
| | double-click | center view on the point |
| **Zoom (Z)** | Shift + drag | change FOV |
| | type `35` or `50mm` | FOV in degrees or focal length in mm |

---

## 3. Mouse navigation

Sources: [QRC 2027 "Middle Button (Wheel)"], [H viewing-model] https://help.sketchup.com/en/sketchup/viewing-model, [H using-your-mouse] https://help.sketchup.com/en/sketchup/using-your-mouse

| Input | Action |
|---|---|
| **Scroll wheel** | Zoom. **Scroll up = zoom in, down = zoom out.** "When you zoom by scrolling, SketchUp uses your cursor as the zoom's center point" [H viewing-model]. |
| **Middle-button drag** | Orbit (temporary; returns to the current tool on release) |
| **Shift + middle drag** | Pan |
| **Middle + left buttons held** | Pan [H using-your-mouse] |
| **Double-click middle** | Re-center the view on the clicked point [QRC]. With the Orbit tool, double-click centers the model [H]. |
| **Left button** | Current tool |
| **Right click** | Context menu (entity-specific: Entity Info, Erase, Hide, Make Group, Make Component, Intersect Faces, Reverse Faces, Explode, Select ▸ …) |

Conflict on the scroll-zoom pivot: the "Using Your Mouse" page says that with another tool active, scrolling zooms about the screen center. The "Viewing a Model" page and community reports say it zooms about the cursor. Users experience **zoom toward the cursor**; implement that.

**Zoom speed** is proportional to the distance to the geometry under the cursor: fast when far, slow when near [H]. The **Zoom tool's drag** (click-drag up = in, down = out) zooms about the **screen center**.

**Orbit details**:
- Gravity-weighted turntable: rotate about world Z (blue) for horizontal mouse motion and about the camera's horizontal axis for vertical motion. Vertical edges stay vertical [H].
- Holding Ctrl (Win) / Option (Mac) "suspends the Orbit tool's built-in sense of gravity" and allows roll [H]. The QRC 2027 says Alt/Option for this.
- Pivot: the 3D point under the cursor at the start of the drag (on geometry). Over empty space it is the screen-center target. This comes from community observation, not official docs [F https://forums.sketchup.com/t/orbit-pivot-point/68455].

**One-button mouse / trackpad**:
- Classic Mac: hold Ctrl+Cmd + click = orbit; Ctrl+Cmd+Shift = pan [H].
- 2027 (Win + Mac): one-finger trackpad gesture + **Ctrl+Alt (Cmd on Mac)** = Orbit; **Shift+Ctrl+Alt (Cmd+Shift on Mac)** = Pan [H 2027 release notes].
- Mac trackpad: two-finger scroll zooms, pinch zooms [K].

**Camera**:
- **Perspective** by default [H].
- **Field of view 35°**, measured vertically (SketchUp blog: "default FOV is 35 degrees"; some posts say Make used 30°) [F].
- FOV range 1–120°. Typing `50mm` sets a focal length.

**Default view** (Simple template, from the 2023 and 2027 screenshots):
- 3/4 aerial perspective; the origin sits slightly left of center in the lower half.
- The **red axis runs toward the viewer to the lower right**; the **green axis recedes to the upper right**; blue points straight up.
- The horizon is about 30–40% down from the top of the viewport.
- A 2D "scale figure" component (a person, e.g. 2023: woman with cat; 2027: man with cane) stands near the origin on the negative-X side [PX].

---

## 4. Templates, default style and colors

### 4.1 Templates

Preferences > Template lists [PX templates screenshot][H setting-templates]:
- "**Simple** — Units: Inches / Meter — general user modeling template with basic styling and simple colors"
- "**Architectural** — Inches / Millimeter / Centimeter — conceptual design development". Its thumbnails show a light gray/white background with no blue sky.
- Others [K]: Construction Documentation, Interior Design, Landscape Architecture, Urban Planning, Woodworking, 3D Printing.

The Simple Template's style is "**Simple Style**", described as "Default face colors. Blue sky and gray background color." [PX 2023 Styles panel].

### 4.2 Measured default colors (Simple Style)

| Element | RGB | Hex | Source |
|---|---|---|---|
| Sky at top of default view (2023) | (30,166,221) | #1EA6DD | [PX] |
| Sky at top of default view (2027) | (64,179,226) | #40B3E2 | [PX] (the top of the viewport sits closer to the horizon in that view) |
| Sky at horizon / Horizon color | **(191,229,245)** | **#BFE5F5** | [PX] identical in 2023 & 2027 |
| Sky gradient | Smooth, roughly linear vertical gradient from the horizon color up to the sky color. It plateaus at the horizon color in the last few pixels above the horizon. In 2023: R rises ~1/px over 160 px. | | [PX] |
| Below horizon (background, Ground OFF) | **(191,191,198)** | **#BFBFC6** | [PX] |
| Front face | (255,255,255) | #FFFFFF | [F][PX] |
| Back face | **(164,178,187)** | **#A4B2BB** | [F] SketchUcation rendering_options dump; openskp PR #398 decoding Untitled.skp |
| Edges ("Foreground") | (0,0,0), about 1 px | #000000 | [F][PX] |
| Selection / Highlight | **(0,0,255)** (dump shows (0,1,255)) | #0000FF | [F][PX] |
| Selected-face stipple | (0,1,255) dots in an every-other-pixel checker over the face | | [PX] |
| Guides (construction lines) | black, dashed | | [F] ConstructionColor (0,0,0) |
| Active section plane | (255,135,0) | orange | [F] |
| Locked group/component | (255,0,0) | red | [F] |
| Axes | **(178,0,0) / (0,178,0) / (0,0,178)**; positive solid, negative dotted | | [PX] |
| Parallel/perpendicular inference | (255,0,255) magenta | | [H accessibility][PX] |
| Tangent inference | cyan (about (0,255,255)) | | [H accessibility][PX] |

Default shading of white front faces (camera light, "Use sun for shading" off): the face facing the camera is 255, a side face about **(210,210,210)**, a top face seen obliquely about **(160,160,160)** [PX selected-face image].

Old pre-2015 template values, for reference only, from a 2010 forum dump [F https://community.sketchucation.com/topic/122364]: Background (204,204,201), Sky (198,205,208), Ground (210,208,185) with GroundTransparency 50, DrawGround false, DrawHorizon true.

Background settings [H customizing-models-background-styles]: Background color, Sky (checkbox + color), **Horizon** (color that blends into the sky), Ground (checkbox + color, transparency), Show ground from below.

**"Horizon blue like a sky" recipe for the clone**:
- Above the horizon line (a world-space horizon at the camera's eye level, infinitely far), draw a vertical gradient: #BFE5F5 at the horizon → #1EA6DD near the top of the screen. In the default view that spans about 10–11° of elevation.
- Below the horizon, fill flat #BFBFC6. Ground is off, so the background color shows.
- Looking down past the horizon shows only gray; looking up shows only blue.

### 4.3 Edge / face style defaults

Options [H edge-styles, face-style]:
- Edges: Edges, Back Edges (dashed hidden edges, toggled with K), Profiles (thickness in px), Depth Cue, Extension, Endpoints, Jitter, Color (All Same / By Material / By Axis).
- Faces: Wireframe, Hidden Line, Shaded, Shaded with Textures, Shaded All Same, Photoreal; X-Ray; Material transparency; Ambient Occlusion.

Simple Style defaults [K][PX]: Edges ON, Profiles OFF, everything else off, Color = All Same (black), Face style = Shaded with Textures.

Some other styles use **Profiles 2–3 px**. The **Architectural** template style uses Profiles at about 2 px.

### 4.4 Axes

- Red = X, Green = Y, Blue = Z.
- Positive direction is a solid line; negative is a dotted line. They extend to the viewport edges.
- The origin inference shows as a dark dot labelled "Origin" [H][PX].
- Axis colors are configurable in Preferences > Accessibility, as are parallel/perpendicular (magenta) and tangent (cyan) [H accessibility https://help.sketchup.com/en/sketchup/accessibility-0].

---

## 5. Inference engine

Source: [H] https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts, plus [H tips-and-tricks] and pixel sampling of the official icons. Contact sheets: `ref_images/sketchup_inference_point_markers_sheet.png` and `sketchup_inference_linear_markers_sheet.png`.

**ScreenTip** style: black text on pale yellow **(255,255,220) #FFFFDC** with a 1 px black border. It appears to the lower right of the cursor. Text is ~11–13 px sans.

### 5.1 Point inferences (marker drawn at the snapped point, roughly 8–10 px)

| ScreenTip text | Marker | Color [PX] |
|---|---|---|
| **Endpoint** | filled circle | green **(95,149,64)** #5F9540 |
| **Midpoint** (also arc midpoint) | filled circle | cyan **(49,192,200)** #31C0C8 ("light blue dot" [H]) |
| **On Edge** | filled square | red **(187,31,37)** #BB1F25 |
| **On Face** | filled diamond | blue **(17,95,159)** #115F9F |
| **Intersection** | X cross | red **(187,31,37)** |
| **Center** | filled circle | blue **(17,96,160)** |
| **Guide Point** | filled circle | dark slate **(53,52,70)** |
| **On Line** (on a guide line) | filled square | red (187,31,37) |
| **Origin** | dark circle at the axis origin | dark gray |
| **Endpoint / Origin in Component** | circle | purple/magenta (115,90,165) |
| **On Section** | blue diamond with white outline | (on a section plane) |
| **Intersection with Hidden Section** | small red X | |

Inside groups/components, **all point markers are magenta** and the tip gets "in Group" / "in Component" appended [H].

The tips page simplifies these colors: green circle = endpoints, blue circle = midpoints, blue diamond = on face, red X = intersections, red square = on line/edge [H tips-and-tricks].

### 5.2 Linear inferences (dotted or colored line + ScreenTip)

| ScreenTip | Appearance |
|---|---|
| **On Red Axis** / **On Green Axis** / **On Blue Axis** | The rubber-band line itself turns red/green/blue (the axis color), drawn thick when snapped. "Click and drag as you draw to see." |
| **From Point** | A thin **dotted line** from a referenced point to the cursor, colored by the axis direction (red/green/blue) |
| **Through Point** (or "Constrained on Line" with Shift) | Locks direction through a second point |
| **Parallel to Edge** | Line turns **magenta**, and the referenced edge highlights magenta |
| **Perpendicular to Edge** | Magenta |
| **Perpendicular to Face** | Magenta |
| **Extend Edge** | Magenta dotted extension of an existing edge |
| **Tangent at Vertex** | Cyan arc preview |

Hovering ("pausing") over a point for a moment makes it a priority reference, so From Point dotted lines appear from it [H].

### 5.3 Shape inferences

- **Square** and **Golden Section**: a diagonal dashed line with blue dots, plus the tip "Square" / "Golden Section". Shift locks it.
- **Half Circle**, **Quarter Circle**, **Three-Quarter Circle** for arcs.
- Arc/circle **Center** inference appears when hovering the curve [H].

### 5.4 Locking

- Shift = lock the current direction or plane. While locked, the line is drawn **thicker**.
- Right arrow = Red, Left arrow = Green, Up arrow = Blue, Down arrow = parallel/perpendicular toggle (magenta).
- Shift+Alt (Win) / Shift+Cmd (Mac) also locks the inferred face plane [H].
- A plane lock for tools like Circle, Rotate or Protractor shows as the colored tool gizmo: blue protractor = horizontal (XY) plane, red = YZ, green = XZ.

### 5.5 Cursors

- Select = arrow, with **+ / − / ±** badges for Ctrl / Ctrl+Shift / Shift [H selecting-geometry].
- Line = **pencil** (red pencil, dark tip; the hot spot is the pencil tip).
- Freehand / arcs = pencil + curve.
- Rectangle, Circle, Polygon = pencil + shape glyph.
- Push/Pull = box with red up-arrow.
- Move = 4-way red arrows.
- Rotate = protractor.
- Scale = box with arrow.
- Eraser = eraser.
- Paint Bucket = bucket; Alt/Cmd shows an eyedropper.
- Tape Measure = tape (with a "+" when in guide mode).
- Protractor = protractor.
- Orbit = two red circular arrows.
- Pan = hand.
- Zoom = magnifier.
- Text = arrow with a text box.
- Dimension = arrow.
- Display Crosshairs (Preferences > Drawing) adds RGB axis-colored crosshairs to the cursor [H].

---

## 6. Tool behaviour step by step

- **Select** (Space): see §0 #14. Clicking empty space clears the selection. **Selection persists across tool switches**, and tools like Move or Rotate operate on a pre-selection [H tips]. Double-clicking a group or component enters it: the rest of the model fades and a dashed bounding box appears. Click outside or Esc exits [H grouping].
- **Lasso** (Shift+Space): drawing **clockwise** = crossing (partial inclusion); **counter-clockwise** = window. Click-click segments, double-click to finish [H selecting-geometry][H drawing prefs].
- **Line** (L) [H drawing-basics]:
  1. Click the start point; a rubber-band line follows the cursor and is colored by inference.
  2. Click the end point. The next segment starts automatically ("Continue line drawing" default ON).
  3. Typing a length + Enter sets the last segment's length.
  4. **Esc** ends the chain.
  5. Clicking back onto the start point of a coplanar loop **creates a face** and ends the chain.
  6. Drawing across a face splits it. Re-drawing over an edge of a deleted face heals the face.
- **Rectangle** (R): click corner 1, move, click corner 2. It is drawn on the inferred plane: ground, an axis plane, or an existing face. Type `L,W` + Enter. Square / Golden Section inferences appear. 2027: Alt/Option draws from the center. Rotated Rectangle is a 3-click variant (edge, then width/angle via protractor).
- **Circle** (C): the VCB shows **Sides = 24**; type a number to change it. Click the center; the circle's plane follows the inferred face or arrow lock. Move and click to set the radius, or type a radius + Enter. It creates a face. The circle stays editable in Entity Info (radius, segments).
- **Polygon**: same as Circle, default **6 sides** [K]. A pushed polygon shows hard facet edges, while a circle is smoothed.
- **Arc tools** (default **12 segments** [H]):
  - **2 Point Arc (A)**: click start, click end (or type the chord length), move perpendicular to set the bulge (or type it), click. Then you can type `Nr` radius / `Ns` segments. It snaps to Half Circle and Tangent at Vertex (cyan).
  - **Arc** (center): click center (protractor shown), click start (dotted radius line), click end or type an angle.
  - **3 Point Arc**: start, pivot point, end.
  - **Pie**: like Arc, but makes a closed pie face.
- **Freehand**: press, drag, release. Creates a curve entity.
- **Push/Pull** (P) [H]:
  1. Hover a face; it is pre-highlighted (blue stipple). You can also pre-select it.
  2. Click it.
  3. Move; the face extrudes along its normal and the VCB shows Distance.
  4. Click to finish, or type a distance + Enter. Negative values push.
  5. Pushing exactly to an opposite parallel face cuts a hole; the tip reads "Offset Limited to…".
  6. Double-click repeats the last distance. Ctrl/Option makes a new starting face.
  7. Extruding a face whose border has arcs creates smooth/soft side edges.
- **Offset** (F): click a face (or pre-selected coplanar connected edges), move inward or outward, click, or type a distance. Overlaps are eliminated unless Alt/Cmd is used. Double-click another face repeats.
- **Follow Me**: pre-select the path edges, activate the tool, click the profile face. Or click the face and drag along the edges (the path highlights in red), then click. Alt/Cmd uses the face perimeter as the path (e.g. lathe or round-over). 2027 adds a Procedural variant.
- **Move** (M) [H]:
  1. Hover: on an unselected entity it highlights. Groups and components show bounding-box corner grips.
  2. Click a reference point; the selection, or the entity under the cursor, is picked.
  3. Move with inferences. The VCB shows Distance.
  4. Click the destination, or type a distance or coordinates.
  - Ctrl/Option before or during the move copies; then `Nx` or `/N` makes arrays.
  - Moving vertices, edges or faces of loose geometry *stretches* connected geometry (sticky). Alt/Cmd allows auto-fold.
  - Arc midpoints and endpoints can be dragged to edit arcs.
- **Rotate** (Q) [H flipping-...-rotating]:
  1. Select the entities.
  2. The cursor is a protractor colored by plane: blue = rotate about Z.
  3. Click 1 sets the center/vertex. Click 2 sets the start of the angle (the protractor arm). Move the cursor; it snaps to 15° ticks when near the protractor. Click 3 or type an angle.
  - Click-drag from the first point to set a custom axis (fold). Ctrl/Option copies. Hover over groups to see rotation grips.
- **Scale** (S): a **yellow bounding box with green grips** appears around the selection. Click a grip and it turns red with its opposite grip. Move; the VCB shows the factor, e.g. "1.00" or "Red, Green Scale". Click or type.
  - Corner grips = uniform by default (Shift toggles).
  - Edge / face grips = 2-axis / 1-axis.
  - Ctrl/Option = about the center.
- **Eraser** (E): click an edge to delete it plus any face that depended on it. Click-drag over edges highlights them blue and deletes them on release. Faces cannot be clicked directly; erase a face via its context menu or the Delete key. Shift = hide, Ctrl/Option = soften/smooth, Ctrl+Shift = unsoften.
- **Paint Bucket** (B): pick a material in the Materials panel and click faces. Painting a group or component paints its "default"-material faces. Alt/Cmd samples. Ctrl = connected matching faces, Shift = all matching faces in the model. "Default" material restores the front/back colors [H applying-materials].
- **Tape Measure** (T):
  - Default mode = **create guide lines** (cursor shows "+").
  - Click on an edge, then move off it: a dashed infinite **guide line** parallel to the edge. Type a distance or click.
  - Click a point, then another point: a **guide point** with a dashed leader.
  - Ctrl toggles Measure-only mode.
  - Measuring and then typing a new length rescales the model, after a confirmation dialog.
  - Guides are infinite, dashed, and can be erased, hidden, or all removed with Edit > Delete Guides [H using-guides].
- **Protractor**: click a vertex (the protractor is colored by plane), click a baseline point, move to the angle, click. This creates an angled guide line. Ticks every 15°, precision 0.1° [H measuring-angles].
- **Dimensions**: click start and end points (or click an edge), pull the dimension out perpendicular, click to place.
  - Defaults: slash endpoints, text aligned to the dimension, auto-updates when geometry changes [H text-dims].
- **Text**: click empty space for **screen text**. Click an entity, move, and click for **leader text**, whose default content is the area, length, or component name. Enter twice or click outside to finish.
- **3D Text**: a dialog (text, font, height, extruded) then places a group with Move.
- **Orbit / Pan / Zoom**: see §3. **Zoom Extents** (Shift+Z) fits the whole model. **Zoom Window**: drag a rectangle to fill the view. **Previous** / **Next** step back and forward through camera views.
- **Axes**: click origin, red direction, green direction to relocate the drawing axes.
- **Flip**: three semi-transparent planes appear through the selection; click a plane to mirror. Ctrl = copy. Hovering a face gives a custom magenta plane.

---

## 7. "Sticky geometry" model

Sources: [H drawing-basics], [H grouping-geometry], [H dividing-splitting-and-exploding], [H softening].

- The primitives are **edges** (line segments) and **faces** (planar polygons bounded by edges, with holes allowed). Curves, arcs and circles are polylines grouped as one selectable "curve" entity. Smoothed and softened faces form a "surface".
- **Auto face creation**: whenever edges form a **closed, coplanar loop**, a face is created automatically. Redrawing one edge of a deleted face recreates it.
- **Auto split / merge**:
  - Edges that cross or touch are split at intersections.
  - A line drawn across a face splits the face into two faces.
  - A closed loop drawn on a face creates an inner face, which can be pushed or pulled as a hole.
  - Erasing a dividing edge merges coplanar faces.
  - Deleting an edge deletes the faces that depended on it. Deleting a face keeps its edges.
- **Stickiness**: loose geometry that touches shares vertices and edges. Moving one part stretches the connected parts.
- **Groups** (Edit > Make Group, or right-click) and **components** (G) wrap geometry in an isolated context: it does not merge with outside geometry. Double-click to edit inside; outside geometry is faded (the "hide rest of model" option is available). Component instances share their definition, so editing one edits all [H grouping-geometry].
- **Face orientation**: each face has a front (white) and a back (blue-gray) side. Context menu > Reverse Faces flips it. Push/Pull extrusions orient the outside as front.
- **Hidden vs soft**: Hide hides the edge only. Soften/Smooth (Eraser + Ctrl, or the Soften Edges panel with an angle slider) joins faces into a smooth-shaded surface [H softening].

---

## 8. Reference images

### 8.1 Downloaded (verified with `file` as real PNGs), in `ref_images/`

1. **`sketchup_default_ui_1_win2023_simple_template.png`** (1117×718). The help-center screenshot of SketchUp Pro 2023 on Windows, via the Wayback Machine 2025 snapshot of https://help.sketchup.com/sites/help.sketchup.com/files/images/su-user-interface.png. It has numbered callouts 1–6.
   - Shows the classic default: title bar, menu bar, Getting Started toolbar on one row, a Warehouse mini-toolbar, and the Default Tray on the right (Entity Info, Materials, Components, Styles expanded with "Simple Style").
   - The status bar reads "Click or drag to select objects. Shift = Add/Subtract. Ctrl = Add. Shift + Ctrl = Subtract." with the **Measurements** label and box at the bottom right.
   - Viewport: blue gradient sky (#1EA6DD top → #BFE5F5 horizon), gray #BFBFC6 below the horizon, RGB axes with dotted negative halves, and a 2D woman-with-cat scale figure left of the origin.
   - **Best reference for the classic Windows look.**
2. **`sketchup_default_ui_2_v2027_empty_scene_large_toolset.png`** (1255×1006), from https://images.ctfassets.net/yd21npj2ir9g/83fbc58dc138603ce675ee/db8347832567ff769aa1eb8a03fd60dd/image_sketchup_interface_toolbar_example.png (help "Toolbars").
   - SketchUp 2027 ("SketchUp Labs" build) with an **empty scene**: just the sky gradient (#40B3E2 top → #BFE5F5), flat gray #BFBFC6 ground/background, and the three axes.
   - Many toolbars at the top (Views, Styles, Edit, Construction, Sandbox, Getting Started, …), the **Large Tool Set** as 2 columns on the left, and the **Default Tray** on the right (Entity Info, Materials, Components, Styles, Environments, Tags Manager, Shadows, Scenes, Instructor, Hatch Pattern, Outliner).
   - Bottom docked toolbars: Shadows sliders, Warehouse, Standard (New/Open/Save/Cut/Copy/Paste/Erase/Undo/Redo/Print/Info), Tags dropdown "Untagged", Measurements box, Principal.
   - **Best reference for the clean viewport colors.**
3. **`sketchup_default_ui_3_v2027_full_window.png`** (2994×2012), from https://images.ctfassets.net/yd21npj2ir9g/5b4dff15e18ee3b39cdd12/a793cf545072f9f151085e8275d43647/image-sketchup-user-interface.png
   - SketchUp 2027 on Mac with the London Library sample model. Shows the Getting Started toolbar and other toolbars across the top, model tabs plus scene tabs, the Large Tool Set (2 columns, left), and the Default Tray (right) with Materials expanded.
   - Status bar: "Click or drag to select objects. Shift = Add/Subtract. Option = Add. Shift + Option = Subtract."
   - Chrome color #F1F1F6; panel header rows #E0E1E9.
4. **`sketchup_default_ui_4_v2027_mac_menubar.png`** (1175×901), from https://images.ctfassets.net/yd21npj2ir9g/1co5tiNiNafbimUMIJlL2I/679eb3cce08f9687f8e68b1fe26f037b/image-sketchup-2027-interface.png
   - The same 2027 UI with the macOS global menu bar: SketchUp, File, Edit, View, Camera, Draw, Tools, Procedures, Window, Extensions, Help.
   - The Default Tray has Shadows expanded (UTC, Time/Date sliders, Light 80 / Dark 45, "Use sun for shading" off, On faces / On ground on).
5. **`sketchup_getting_started_toolbar_v2027.png`** (1850×306), from https://images.ctfassets.net/yd21npj2ir9g/379b1e13823e838ac17f09/812d47539980c5925e67ba39fe988a52/image_sketchup_toolbar.png
   - The floating "Getting Started" toolbar alone, over the sky and gray background. **Exact icon order** (see §1.3); icons are navy/cyan with red accents.
6. **`sketchup_status_bar_v2027.png`** (3260×874), from https://images.ctfassets.net/yd21npj2ir9g/2K4kYAzlpheKBcm4D7MvYH/77c2089a837e8fcf6bbcbbc178000f43/image-sketchup-interface-statusbar.png
   - Zoomed status bar: pin, ⓘ, hint text, divider, Measurements box at the right with a resize grip.
7. **`sketchup_large_tool_set_v2027_crop.png`** (145×1520). My crop of image 3, showing the Large Tool Set grid used for §1.4.
8. **`sketchup_inference_point_markers_sheet.png`** and **`sketchup_inference_linear_markers_sheet.png`**. Contact sheets I built from the official inference icons on the drawing-basics help page (`SketchUp-Creating-Drawing-Basics8..30.png` on images.ctfassets.net). They show each marker and ScreenTip: pencil cursor, yellow tips, colored markers, magenta parallel/perpendicular lines, and cyan tangent.
9. **`sketchup_selected_face_default_style.png`** (573×404), from https://images.ctfassets.net/yd21npj2ir9g/381296354274201d9bb650/fa5cbc09ec9951564845a210c05e7d1e/su-select-double-click-face.png
   - Default-style box on the gray background. The double-click-selected face shows a **blue (0,1,255) dot stipple** and **blue edges**. Unselected face shading: 255 / 210 / 160.

### 8.2 Other useful image URLs (not downloaded)

- 2027 fresh Untitled window with a callout over the toolbar: https://images.ctfassets.net/yd21npj2ir9g/2jB189zIIuFqcdAeH1IwIB/644a545f19ce619a3decd09e560c00cc/image-sketchup-interface-toolbars.png
- Old vs new Mac Window menu: https://images.ctfassets.net/yd21npj2ir9g/7qD5T2pL8a5CNyJxPh5hPU/e59f056c0380f4364e639ffb56d1ebb3/image_sketchup_older_vs_new_interface.png
- Trays / panels: https://images.ctfassets.net/yd21npj2ir9g/9e87abfd51da33ef2984b9/9b82a0c26164b8ecea128ce98634f9e1/image_dialog_boxes_trays.png
- Tray docking: https://images.ctfassets.net/yd21npj2ir9g/6IWEq0XcPOurchW1WOMsqV/1d1ca96bc967e564241a8ca8f9cc9bb4/image_tray_position.png
- Templates list: https://images.ctfassets.net/yd21npj2ir9g/510a7e3e4cc8539681f7e2/ff6083d6ba60d15208fb307783b8a7df/SketchUp_GettingStarted_Interface_Templates2.png
- Horizon-color hero: https://images.ctfassets.net/yd21npj2ir9g/dee2d28294a6029dd225fd/63dd3e48554e1fd0b038eca60b25d809/su-horizon-color-hero.png
- Styles panel (faces): https://images.ctfassets.net/yd21npj2ir9g/d62680e5d684bbd12ca57b/c32e55f381db5685d0e1b46222526349/desktop-materials-styles-panel-edit-faces.png
- Styles panel (edges): https://images.ctfassets.net/yd21npj2ir9g/5e99ac159137cfc4afb96c/790bd3ea3a8a63692810a4ee14d6a9ed/desktop-materials-styles-panel-edit-edges.png
- Profiles example: https://images.ctfassets.net/yd21npj2ir9g/2faa8327850a84bec6bf8c/6876c8b31c58e2c5ba444712140173db/su-3000109-profiles.png
- Back edges example: https://images.ctfassets.net/yd21npj2ir9g/83ea2ec6f22e1f7a1ecd9f/e2185466044ff1a379f888c4d7bcf6f0/su-3000109-back-edges.png
- Midpoint inference example: https://images.ctfassets.net/yd21npj2ir9g/7b1d96ca6531fa426624c1/e56671a1fbf361980416f5acff6ee8ee/SketchUp-Creating-Drawing-Basics22.png (and the whole …Basics8–35 series)
- QRC 2027 page 1 (Large Tool Set icon sheet): https://download.sketchup.com/QRC2027/HC-QRC2027-en-SU-win.pdf

---

## 9. Conflicts / open questions noted

- **Orbit "no gravity" modifier**: [H viewing-model] says Ctrl (Win) / Option (Mac). [QRC 2027] says Alt (Win) / Option (Mac).
- **Line inference lock**: [H] and the Mac QRC say Shift. The Windows QRC 2027 says "Alt: lock in current inference direction", which is probably a typo. Alt on Windows cycles linear inference modes [H].
- **Scroll-zoom pivot**: the cursor ([H viewing-model]) vs the screen center when another tool is active ([H using-your-mouse]). Real-world behavior is the cursor.
- **Large Tool Set side in 2027**: the text says "right side"; every screenshot shows it on the left. Classic Windows allows docking on the left only.
- **Default FOV**: 35° (blog, help quote) vs 30° (some forum posts, for Make vs Pro).
- **Back-face color (164,178,187)** is confirmed by two community sources (an API dump and file decoding), not by an official page.
- **Sky "top" color** depends on the camera pitch and viewport. Measured values: #1EA6DD (2023 view) and #40B3E2 (2027 view). The horizon (#BFE5F5) and the gray (#BFBFC6) are identical in both.
