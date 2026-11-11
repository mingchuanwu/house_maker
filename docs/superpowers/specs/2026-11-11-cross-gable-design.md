# Cross gables (wall gables)

## Goal

A front-facing cross gable: a section of a side wall rises into a gable, with its own small roof running back at
right angles until it meets the main roof (Victorian / farmhouse look).

## Interface

- `HouseMaker.add_cross_gable(side, x, width=30, pitch=None, roof_overhang=3)`; CLI
  `--cross-gable SIDE:x=..[:width=..][:pitch=..][:overhang=..]` (repeatable). `x` is measured along the side wall
  (the wall's own coordinates, like its windows); `side` left/right selects the side wall and the roof panel above it.
- Pitch defaults to 45° (90° apex).

## Geometry

The main roof's underside rests on the side wall's outer top corner. The cross gable is a dormer whose front face is
the side wall itself and whose sill lies on the main roof's top surface along the wall's outer face:

- The side wall's top edge gets an extension over x..x+width: straight up through the main roof slab (t / cos θ),
  then the gable to the apex (Hg = width/2 · tan φ). One part with the wall.
- Two cross-roof panels like dormer roof panels (front overhang, horizontal ridge, valleys glued on the main roof,
  ridge lapped with fingers / single tab).
- The main roof gets a notch in its eave across the gable: from the eave edge to where the wall's inner face passes
  through the roof's top surface.
- Footprint scored on the main roof like a dormer's.

## Joints

Rake tabs on the wall gable's sloped edges into slots in the cross-roof panels; ridge fingers; nothing new between
wall and main roof.

## Placement

Clear of the side wall's corner joints (2t from either end), the gable-tab slots, chimneys, dormers and other cross
gables (overlap checks and fit suggestions as for dormers); counts toward the dormer-coverage warning.

## Window

A slim double-hung window in the wall gable (the dormer face window rule, with the gable as the face).

## Testing

Independent 3D model: no penetration (wall gable vs main roof notch, cross roof vs main roof and wall), valleys and
ridge end on the main roof, rake tabs in their slots; placement, CLI, window, random sweep.
