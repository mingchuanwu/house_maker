# In-house 3D viewer (`--3d view`)

## Goal

Visual inspection of the assembled house — finger joints, slots, casings against the roof — in one
self-contained HTML file, with no install and no external app (Blender, Sawhorse, slicers). Viewing only, no
editing. `review/` stays the 2D cut-sheet review; this is a separate tool for the house you just generated.

## Entry points

- CLI: `--3d` gains the choice `view`, which writes `<output stem>.view.html` next to the SVG
  (e.g. `house_box.view.html`). `--3d all` writes 3mf, stl, glb **and** view. The default stays `3mf`.
- API: `HouseMaker.generate_view(filename=None)` returns the page as `str` or writes it.
- Make: `make view` generates the default house with `--3d view` and opens the page.

## Architecture

New package `viewer3d/`, laid out like `review/` (template + CSS + two scripts inlined by Python):

| File | Purpose |
|---|---|
| `viewer3d/payload.py` | Model → JSON payload: for every part its name, group, material colour, vertices, triangles, and the outward unit normal of its panel frame. Depends on `model3d` (`house_frames`, `panel_solid`), nothing on the SVG side. |
| `viewer3d/page.py` | `build_page(payload) -> str`: inlines CSS, scripts and the payload (`</` escaped) into `viewer.html`. |
| `viewer3d/viewer.html`, `viewer.css` | Layout: toolbar, outliner (left), WebGL canvas, status bar. |
| `viewer3d/viewer_core.js` | Pure functions, no DOM/WebGL: 4×4 matrices, orbit camera (target, yaw, pitch, distance, ortho/persp), standard views, picking ray, feature-edge extraction, explode offsets, section-plane maths, distinct per-part colours. Exported for Node tests. |
| `viewer3d/viewer_app.js` | WebGL rendering, input, outliner and toolbar; uses only `viewer_core.js`. |

Engine: hand-written WebGL 1 (no three.js). Coordinates are the model's: millimetres, Z up.

### Payload

```json
{"title": "house_box", "units": "mm",
 "parts": [{"name": "gable_wall_front", "group": "walls", "color": [222,184,135],
            "normal": [1,0,0], "vertices": [x,y,z, ...], "triangles": [i,j,k, ...]}]}
```

Groups: `floor`, `walls`, `roof`, `casings`, `chimney`, `dormer` (from the part name, same rules as
`model3d.part_color`). Casings and chimney/dormer parts use the frame normal of their own panel.

## Features

- **Navigation** (trackpad first, mouse too): two-finger scroll orbits, Shift+scroll pans, pinch (ctrl+wheel)
  zooms; left-drag orbits, right-drag or Shift+drag pans, wheel zooms. Zoom goes toward the cursor.
  Double-click a surface: orbit around that point. `F` frames the selection (or everything).
- **Standard views**: Front, Back, Left, Right, Top, Bottom, Iso buttons; keys 1/3/7 (Ctrl: opposite side),
  0 iso; `5` toggles perspective/orthographic. Front looks along −X at the `gable_wall_front` (x = length).
- **Outliner**: parts grouped as above, each row with show/hide (eye) and isolate (solo); a group row toggles
  the whole group. Clicking a row or a part in the canvas selects it (highlighted in both); Esc deselects;
  `H` hides the selection, Alt+H shows all.
- **Colours**: distinct colour per part (default) or material colours (wood/roof/brick/trim).
- **Exploded view**: slider 0–20 mm; each part moves by `explode × normal`; casings move with their wall
  plus an extra 0.5× so they separate from it.
- **Section plane**: axis X/Y/Z, position slider over the model's extent, flip. Fragments on the cut side are
  discarded in the shader; back faces seen through the cut draw in a flat hatch colour, so cut material reads
  as solid.
- **Display**: X-ray with opacity slider (blended, no depth write), feature edges on/off (dihedral > 20°,
  plus boundary edges), wireframe on/off.
- **Status bar**: selected part name and triangle count, world position under the cursor in mm.

## Error handling

- No WebGL: the canvas area shows "WebGL is not available in this browser" instead of a blank page.
- Missing/empty payload: "No parts in this model".

## Testing

- Python (`tests/test_viewer3d.py`): payload has one entry per model part with matching vertex/triangle
  counts, indices in range, unit normals, known groups; the page contains the payload and no unreplaced
  `/*__…__*/` markers and no `</script>` inside the data; `--3d view` and `--3d all` write the page;
  `generate_view()` returns a string.
- Node (`tests/viewer3d_core_test.js`, run from pytest like `review_core_test.js`): matrix inverse/multiply,
  orbit camera keeps the target fixed and clamps pitch, standard views look along the stated axes, picking ray
  through the screen centre hits the target, edge extraction on a cube gives 12 edges, explode offsets,
  section plane keep/discard sign.
- Manual checklist for what cannot run headless (drawing, input): orbit/pan/zoom with trackpad and mouse,
  each view button, hide/isolate, explode, section on each axis, X-ray, edges.

## Out of scope

Editing geometry, measurement tool, saving camera views, embedding in `review.html`, live reload.
