# Dormer side walls (cheeks)

## Goal

On steep roofs a dormer with a horizontal ridge is shallow (a 25 mm dormer on a 60° roof is 7 mm deep). Vertical
side walls lift the dormer roof and make it deeper.

## When

- `wall_height` option: `add_additional_gable(wall_height=H)`, CLI `--additional-gable-wall-height H`.
- Not given: roofs steeper than 45° get walls as tall as the dormer's gable (W/2 at 45° pitch); others none.
- `0` forces no walls; `H > 0` gives walls on any roof.
- With walls the pitch defaults to 45° (90° apex); without, 45° or the main roof's angle if steeper (unchanged).

## Geometry (dormer frame: x along the sill, y horizontal up-slope, z up; sill on the roof top at y = 0)

- Eave line at z = H. Gable height Hg = (W/2) tan φ; ridge at z = H + Hg, ending at y_Q = (H + Hg) / tan θ.
- Front face: pentagon W wide, base lifted t·tan θ; vertical sides up to the eave line, rakes to the apex.
- Cheeks: vertical right triangles in x ∈ [0, t] and [W - t, W], from the face's rear (y = t) back to where the eave
  line meets the roof (y_w = H / tan θ): front edge vertical, top level at z = H, bottom on the roof. The sloped
  dormer roof touches a cheek top along its outer face; the wedge (t·tan φ) is inside.
- Dormer roof panels start at the eave line: side edge (resting on the cheek) from the front to y_w, valley from
  there to Q; ridge length y_Q + overhang. Without walls everything reduces to today's dormer.

## Joints

- Face ↔ cheek: corner fingers along the vertical edge, face female (notches t deep), cheek male; flush corner.
- Cheek bottom → main roof: one tab, t deep, square to the roof, through a t-thick slot in the main roof panel.
- Cheek top → dormer roof: one tab t / cos φ tall (flush with the roof's top at the outer face) into a notch in the
  roof panel's side edge, t (cos φ + tan φ) deep (the tab's shadow through the sloped slab).
- Unchanged: ridge with lap, rake tabs, face base tab; valleys glued.

## Testing

Independent 3D model with cheeks; steep (55–65°) and shallow-with-walls scenes: no penetration, cheek bottoms on the
roof, tabs inside their slot/notch and reaching the far face, valleys on the roof; default rules; CLI; mates;
random sweep.
