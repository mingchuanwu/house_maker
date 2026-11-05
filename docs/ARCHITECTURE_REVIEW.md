# Architecture review — findings & progress tracker

Source of truth for the architecture clean-up. Update the **Status** column as work lands.
Status: `open` · `wip` · `done` · `deferred` (with reason) · `wontfix` (with reason).

Review date: 2026-10-31. Scope: whole package (≈7.1k lines at review time).

## Goals

1. **Clean interfaces / separation of concerns** so each component can be improved without
   cascading changes.
2. **Cut-file correctness**: every pair of mating cut elements (finger ↔ groove, tab ↔ slot,
   dormer/chimney angles) must fit in position, dimension and material thickness, and this must be
   *tested*, not eyeballed.
3. **Sufficient, not bloated tests**: black-box invariants over the public API + a handful of
   pure-geometry unit tests. No giant golden files.

## Target architecture (one-way dependencies)

```
constants, exceptions
   └─ geometry         HouseGeometry (dimensions, true roof angle, panel sizes). Pure math.
        └─ components  Window/Door/Chimney/Dormer data + their own *pure* geometry
              ├─ placement   sizing, auto-placement, collision (no SVG)
              └─ model       Panel (name, cut/score/pattern layers, bbox, joint metadata)
                    ├─ joints      finger-joint engine: edge + params -> path + JointSpec
                    ├─ builders    one builder per panel kind -> Panel (walls, roof, chimney, dormer, casings)
                    │              cutout/casing registries keyed by WindowType/DoorType
                    ├─ patterns    wall/roof/brick patterns (deterministic)
                    ├─ layout      pack(list[Panel], sheet) -> placements (one packer for ALL panels)
                    └─ render      placed panels -> SVG (CSS classes, labels, viewBox from placements)
HouseMaker (facade): build model -> build panels -> layout -> render. No cached state that can go stale.
```

Rule: a lower layer never imports a higher one; builders receive plain data (not the whole
`ArchitecturalConfiguration`).

## Findings

### A. Cut-file correctness (highest priority)

| ID | Finding | Evidence | Status |
|----|---------|----------|--------|
| C-01 | Extra panels (chimney, casings, dormer) are placed outside the SVG viewBox | `svg_generator._calculate_svg_bounds` only sees main panels | done |
| C-02 | Multiple chimneys / dormers are stacked at the same x,y and overlap | `svg_generator._generate_chimney_panels` resets `base_x/current_y` per chimney | done |
| C-03 | Layout uses nominal panel size, ignoring protruding tabs (t+kerf) → neighbouring tabs can collide; spacing is not guaranteed | `geometry.calculate_layout_positions` | done |
| C-04 | Main box: gable wall side-edge length uses `z`, side walls use `z+kerf` → mating finger positions off by kerf/2 | `generate_gable_wall_panel` uses `geometry.height` | done |
| C-05 | Dormer geometry is not a valid 3D construction: depth is a free parameter, roof panels use legs `D` and `W/2` instead of rafter length and ridge length; `apex=90°` hard-coded so the pitch only equals the main roof pitch at 45°; ridge/valley edges confused (hypotenuse labelled ridge) | `dormer_geometry.py`, `AdditionalGable`, `generate_additional_gable_roof_panel` | done |
| C-06 | Dormer has no attachment features to the main roof (cut-out generator is a TODO returning `[]`) | `_generate_additional_gable_cutouts` | done |
| C-07 | Dormer front wall has no joint with the roof panels although docs say it does | `generate_additional_gable_wall_panel` | done |
| C-08 | Chimney: footprint depth is a *plan* (horizontal) depth in the maths but documented/validated as slope length (bounds check uses plan depth instead of `depth/cosθ`) | `add_chimney`, `Chimney`, `_generate_chimney_cutout` | done |
| C-09 | Chimney: roof angle re-derived from `y_kerf`/`thickness` inside `Chimney` instead of one authoritative `HouseGeometry.roof_angle` | `Chimney.__init__` | done |
| C-10 | Chimney: front/back wall height is reduced by `t`, side walls are not → tops are not coplanar | `Chimney._generate_wall_panel_dimensions` | done |
| C-11 | Chimney casing opening is not derived from the chimney's outer footprint (magic `4.1t`, `2.1t`, `l+t`) | `Chimney._generate_wall_panel_dimensions` | done |
| C-12 | Non-deterministic stone pattern: `random.seed(hash(str))` (hash randomised per process) and reseeds the global RNG | `ArchitecturalPatternGenerator._generate_stone_pattern` | done |
| C-13 | No collision check between roof features (chimney vs dormer vs chimney) | `ArchitecturalConfiguration.add_*` | done |
| C-14 | `roof_type` (hip/gambrel/…) is accepted by API+CLI but has no effect on generated panels | `RoofGeometry` unused by generators | deferred — implementing real roofs is a feature; now warns loudly and the dead `RoofGeometry` was removed |

#### A2. Found by the physical-fit work (3D assembly model, boundary tests, randomized sweep)

| ID | Finding | Status |
|----|---------|--------|
| C-15 | **Kerf on edge fingers was wrong in both directions**: tab protruded `t+k`, notch was `t-k` deep (2k interference) and widths were not compensated (2k loose). Now: tab `f+k` wide / `t` long, notch `f-k` wide / `t` deep, slots `(f-k)x(t-k)`; after cutting every tab is exactly `f x t` and every notch/slot the same. Tests assert the *physical* part (`tests/profiles.physical`) | done |
| C-16 | **Roof ridge fits exactly only at 45°** - an inherent limit of laser cutting: the laser cuts square to the plate, so the two roof panels cannot be bevelled to meet at other angles. Shallower roofs overlap along the ridge by at most `t*cos 2θ` (e.g. 1.4 mm at 20°, t=3), steeper ones leave a wedge gap of at most `t*|tan(90°-2θ)|` on the outer face. **Accepted:** finished by hand; the assembly instructions state the amount for the chosen angle (`SVGGenerator.ridge_finishing_note`), and `test_ridge_deviation_is_the_inherent_geometric_limit` pins the deviation to these bounds so it can never silently grow | accepted (hand finishing) |
| C-17 | Chimney **casing opening cut into the up-slope wall**: the vertical walls lean away from the casing's normal by `t*tan(theta)`, so the opening must reach that much further up-slope (`Chimney.casing_upslope_extra`); placement keep-outs follow | done |
| C-18 | Dormer **face dug into the rising roof** (level base on a sloped surface). Base is now lifted by `t*tan(theta)` (smaller similar triangle), tab/slot positions follow, and the right panel gets the mirrored slot | done |
| C-19 | Dormer **ridge notches cut through the valley edge** on large dormers (right roof panel tapers to a point): fingers confined to where the panel is >= 2t wide, left (male) and right (female) layouts mirror each other | done |
| C-20 | Dormer with `roof_overhang=0` produced a degenerate outline (zero-length edge) | done |
| C-21 | **Automatic windows/doors could leave the gable outline** (second "floor" window on a narrow 65 deg gable); automatic candidates now pass the same checks as hand placement | done |
| C-22 | Exact-limit placements were rejected by floating-point rounding (1e-14); `EPS = 1e-9` in the comparisons | done |
| C-23 | `add_window/add_door(width=..)` with only one dimension silently ignored the given value | done |
| C-24 | Library warnings were attributed to `maker.py` instead of the caller (`warnings_util.warn_caller`) | done |
| C-25 | `layout.pack` crashed when no candidate position was free ("min() of empty") | done |
| C-26 | Chimney and dormer parts were drawn at nominal size and their voids (roof hole, casing opening) at nominal: after cutting parts were `kerf/2` small per edge and voids `kerf/2` large. Outlines are now offset by `kerf/2` (`geometry.offset_polygon`, `FingerJointEngine.kerf_outline`), fingers refitted onto the offset edges | done |
| C-27 | Window/door cut-outs and casings were drawn at nominal size (holes `kerf/2` large, casings `kerf/2` small). Now compensated through `kerf.py`: curves are flattened to 32-sample polylines and offset exactly (part outlines outward, holes inward); tested geometrically for every window and door type | done |
| C-28 | **Observation (design quirk):** the arched window casing is only about half a thickness wide at the apex (the outer curve is built from a control point, so its apex rises by half of the frame width). Making it uniform means `outer_height = inner_height + 3*casing_width` in `casings._generate_arched_window_casing`; the arched *door* casing should be looked at too | **done** – outer control point is now `inner_height + 3*casing_width`, apex frame = `casing_width`; reported height is the true apex; the arched door casing was already uniform (arch at the bottom, inner path starts at y=0); test assertion tightened to `t` |

### B. Architecture / interfaces

| ID | Finding | Status |
|----|---------|--------|
| A-01 | `EnhancedHousePanelGenerator` is a ~1950-line god class (outlines, window/door cutouts, casings, chimney, dormer, shingles, brick) and the file is misnamed `multi_finger_joints.py` | done |
| A-02 | Generator holds a back-reference to `ArchitecturalConfiguration` (duck-typed with `hasattr`) → upward dependency; circular imports hidden as in-function imports | done |
| A-03 | Open/Closed: adding a window/door type means editing `elif` chains in 3 places | done |
| A-04 | `architectural_components.py` (1900 lines) mixes data, roof maths, placement, sizing and SVG drawing | done |
| A-05 | Decorative drawing split across 3 layers (wall patterns in components, roof/brick in generator, CSS in svg_generator) | done |
| A-06 | No `Panel` abstraction: main/chimney/dormer/casing panels each have a 60–80 line bespoke SVG emitter with two different positioning conventions | done |
| A-07 | Hard-coded panel-name lists duplicated 3×; four unrelated `get_panel_dimensions()` shapes | done |
| A-08 | `HouseGeometry` also owns the finger-joint policy table (`get_finger_joint_configuration`) and has dead `calculate_finger_joint_positions` | done |
| A-09 | Kerf modelled three ways (`x_kerf`, `get_*_kerf()`, raw) – callers must know which | done |
| A-10 | Config layer: bool-return + `print` warnings vs raising in constructors; duplicated placement validation; parallel storage (`windows` + `_custom_windows`); `clear_components` forgets chimneys | done |
| A-11 | `ArchitecturalConfiguration` exposes mutable internals (`positioner`, `sizer`, `pattern_generator`, `roof_geometry`) and `HouseMaker.change_*` reaches into them | done |
| A-12 | `HouseMaker` caches `SVGGenerator` → stale after `add_*`/`change_*`; constructs it in 5 places | done |
| A-13 | Dead / unreachable code: `WindowAssembly`, `DoorAssembly`, `style_params`, `_generate_chimney_wall_with_finger_joint`, `_generate_simple_shingles_pattern`, `_get_joint_direction` (all branches `-1`), `constants.RoofType/WindowStyle/EdgeType/...`, rotated layout (position/bounds inconsistent) | done |
| A-14 | `generate_internal_female_cutout` monkey-patched onto the class at the bottom of the file | done |
| A-15 | Two different `RoofType` enums | done |
| A-16 | CLI: hand-written string→enum maps; chimney/dormer options inconsistent with library | done |
| A-17 | Repo hygiene: 6 overlapping status `.md` files (stray `.svg` files are already git-ignored) | deferred — needs the owner to decide which status docs to keep; `HOUSE_BOX_ARCHITECTURE.md` got an "outdated" banner |
| A-18 | `get_cutting_summary` estimates with fudge factors and ignores every extra panel | done |

### C. Fitness functions (automated guards)

| ID | Guard | Status |
|----|-------|--------|
| T-01 | Output is deterministic (also across `PYTHONHASHSEED`) | done |
| T-02 | Every panel lies inside the viewBox; no two panels' *actual* cut extents overlap (with min spacing) | done |
| T-03 | Main-box seams mate: finger positions, widths, depths ≈ thickness (kerf 0 exact, kerf>0 within tolerance) | done |
| T-04 | Roof ↔ gable slot/tab alignment | done |
| T-05 | Chimney geometry vs independent 3D construction, for several roof angles | done |
| T-06 | Dormer geometry vs independent 3D construction (horizontal ridge, right-angle at apex, matching pitch) | done |
| T-07 | Dormer & chimney features mate (ridge fingers, wall tabs ↔ slots) | done |
| T-08 | Import-layer rule: lower layers never import higher ones | done |
| T-09 | API smoke: all window × door × style × shingle combinations generate valid closed paths | done |

## How correctness is checked (no human needed)

| Layer | Where | What it proves |
|---|---|---|
| Absolute dimensions | `tests/spec.py`, `components/test_dimensions.py` | every panel size equals an independent closed form (a wrong kerf sign or overhang cannot hide in relative checks) |
| Drawn = declared | `tests/invariants.py`, `components/test_panel_invariants.py` | outlines simple + counter-clockwise through the nominal corners; fingers, slots, area and cut-outs equal the plan |
| Physical fit of joints | `components/test_box_seams.py`, `test_chimney.py`, `test_dormer.py` | mating fingers have equal position/width and depth == material thickness *as cut* |
| 3D assembly | `assembly3d.py`, `components/test_assembly_3d.py`, `test_chimney_3d.py`, `test_dormer_3d.py` | independent 3D model of the house: panels as kerf-eroded slabs never interpenetrate, tabs end flush in the slab they plug into, chimney top level, walls rest on the roof (wedge gaps are asserted numerically), extents equal the specification |
| Finger-layout policy | `test_finger_layout.py` | odd counts, symmetry, spacing, monotonic count, pinned ladder, kerf only changes widths |
| Boundaries | `test_boundaries.py`, `test_contracts.py` | every validation limit and keep-out is tested at the limit and just beyond (all four sides, every pairing) |
| Automatic placement | `test_auto_placement.py` | floor structure, sizing proportions, door/window rules, validity of what the placer produces |
| Randomized sweep | `test_random_sweep.py` | seeded random houses (dims, angle, material, kerf, style, chimneys, dormers) satisfy *all* of the above; `HOUSE_SWEEP_N=300` for a bigger run (it has already found 6 real bugs) |
| Kerf offset of cut-outs and trim | `test_kerf_compensation.py` | every window/door type (curves included): holes exactly kerf/2 smaller, trim frames kerf/2 larger, flattening accurate to 0.01 mm, no change at kerf 0, score lines untouched |
| Mates | `test_mates.py` | exact wiring + every declared edge mate lines up all its fingers |
| Review tooling | `test_review_tool.py`, `review_core_test.js`, `review_dom_smoke.js` | snapping puts mated panels together with exactly the kerf-predicted overlap |

## Design decisions made during the work

1. **One kerf policy** (C-04/A-09): every outer panel dimension is `nominal + kerf`, derived once in
   `HouseGeometry`; internal holes shrink by kerf. Gable wall side edges, floor edges, side wall edges
   now have identical lengths for the same physical seam. Finger *positions* never depend on kerf.
2. **Roof angle is exact** (C-09): peak height and rafter length derive from the same gable width
   (`y_kerf + 2t`), so the drawn slope equals the requested `--angle`; `Chimney` no longer re-derives it.
3. **Chimney model** (C-08/C-10/C-11): `width` = interior width between side walls (outer = width+2t);
   `height`/`--chimney-depth` = *plan* (horizontal) depth, matching the original diagram (`l = k/cosθ`).
   The top is level, so the **downslope wall is taller** (the old code made the up-slope wall taller).
   `chimney_height` = minimum exposure at the up-slope wall. Front/back wall bases are cut level at the
   highest roof point under them (exact `t·tanθ` correction; the old flat `-t` is right only at 45°).
   The roof panel gets the footprint *scored* plus a *through-cut* of footprint − 2·t in both directions
   (a lip of one thickness all round so the chimney cannot fall through); before, the footprint rectangle was
   drawn in the cut layer. Casing opening = footprint + 0.1t, frame = t.
4. **Dormer model** (C-05..C-07): the dormer pitch defaults to the main pitch; with a horizontal ridge
   its depth is *determined* (`footprint = H/sinθ`), so `height` is ignored with a warning. Roof panels
   are right-angled at the apex (legs = rafter, ridge), hypotenuse = valley. Ridge fingers (left male /
   right female) and face tabs ↔ roof slots are created only when the edge is ≥ 1.5 finger lengths and
   the slot fits inside the panel, so tabs never exist without a slot. Valley edges are glued; the
   footprint triangle is scored on the main roof. (The old A/B/C debug corner labels were dropped.)
5. **Errors**: configuration methods raise `PlacementError` (reason included) instead of printing and
   returning `False`; `add_*` return the created component. Chimney/dormer placement is checked against
   panel margins, gable-tab slots and other roof features (C-13).
6. **Rotated layout removed** (A-13): its positions and bounds were inconsistent and nothing used it.
   Layout now packs *actual* cut extents (tabs included) plus label space with a guaranteed gap.
7. **Unimplemented roof types warn** (C-14) rather than silently producing a gable roof.
8. **Physical kerf model** (C-15): the laser removes `kerf` centred on the drawn line, so the drawn path is the nominal
   shape offset outward from its material by `kerf/2`: outer dimensions `+k`, edge tab `f+k` x `t`, edge notch `f-k` x `t`,
   slots `(f-k)x(t-k)`, voids (roof hole, casing opening) `k` smaller. One place implements it: `FingerJointEngine` +
   `geometry.offset_polygon`. Mating tests compare the *as-cut* parts with no kerf tolerance.
9. **Everything standing on the rising roof is cut level at the highest roof point under its thickness** (chimney front/back
   walls, dormer face): a flat base cannot follow the slope across the part's thickness, so it leaves a wedge gap of
   `t*sin(theta)` under the down-slope face instead of digging in. Asserted numerically in the 3D tests.
10. **Chimney casing** reaches `t*tan(theta)` further up-slope than down-slope (the walls lean away from the casing's normal).
11. **Dormer ridge fingers** only where the panel is >= 2t wide; the right panel's layout is the mirror of the left one's.

## Behaviour changes to be aware of

* Chimney/dormer panel shapes changed (intended; see decisions 3–4). All other panels are unchanged
  at kerf 0 and differ by ≤ kerf elsewhere (consistent kerf, decision 1).
* `HouseMaker.add_chimney/add_additional_gable/add_window/add_door` raise `PlacementError` on failure
  and return the component on success.
* `SVGGenerator(use_rotated_layout=...)` removed; `HouseGeometry.get_finger_joint_configuration`,
  `*_kerf` duplicates, `RoofGeometry`, `WindowAssembly/DoorAssembly`, `style_params` removed.
* `architectural_components.py` / `architectural_config.py` / `multi_finger_joints.py` were split into the
  modules listed in the README (a copy of the pre-refactor working tree is in
  `../house_maker_pre_refactor_backup/`).
* Edge-finger kerf compensation changed (decision 8): finger geometry in existing cut files differs from earlier output
  by `kerf` in tab/notch width and depth. Chimney/dormer outlines and the chimney roof hole are kerf-offset now.
* Window/door cut-outs are drawn kerf/2 smaller and trim frames kerf/2 larger (curves are now written as 32-sample polylines instead of Bezier commands whenever kerf > 0; at kerf 0 the original paths are untouched).
* The dormer front face is a smaller triangle (decision 9); the chimney casing opening is longer up-slope (decision 10).
* Automatic windows/doors that would not fit (margins, gable slope, neighbours) are now dropped instead of placed.
* `HouseMaker` validates geometry on construction (`validate_geometry`, previously never called).

## Change log

* 2026-10-31 · all · Initial review, tracker, test suite (723 tests, ~1.5 s), `Panel`→layout→render pipeline,
  joint engine with planned `JointSpec`s, builders per panel kind, cutout/casing/pattern modules,
  chimney + dormer geometry rewritten from explicit 3D models, config API cleaned up.
* 2026-10-31 · T-02 · Added `tests/test_visual_gallery.py` (opt-in `--svg-dir`, writes SVGs + index.html). It exposed a packer crash (no free candidate position with many panels); fixed in `layout.pack` and covered by `tests/test_layout.py`.
* 2026-10-31 · review follow-up · Independent review confirmed the maths and fixed: sheet overflow (document now ≤ material width), wall components checked against the gable outline and each other, chimney casing frame included in margins/overlap checks, roof features rejected when the style has no roof, joint planning judged on the length fingers actually occupy + builder validates geometry, label-aware slot sizing, dead code removed (see `tests/test_review_regressions.py`).
* 2026-10-31 · chimney joints + component tests · Chimney walls now have finger joints: front/back walls carry male tabs on both vertical edges, side walls carry matching female notches on their end edges (flush corners), matched in 3D height above the roof; chimney uses its own finger length (≤ shortest wall / 3, glued if that is < 2 thicknesses). Tests reorganised into `tests/components/` (window, door, chimney, dormer, box_seams, wall_style) with SVG output via `--svg-dir` and a shared `inspect` fixture.
* 2026-10-31 · human review tooling · `mates.py` (declared mating edges + tab↔slot pairs with finger-aligning shifts), `review/` package: self-contained `review.html` (drag/rotate/flip, snap-to-mate, pure-JS overlap analysis with kerf-expected interference, tab-in-slot ghosts, measure, annotated pins attached to panel/edge/finger/slot), JSON export → `python -m house_maker.review collect`. Verified in node: all 50 declared edge mates snap with every finger coinciding and measured overlap = kerf-predicted interference; page logic verified end-to-end in jsdom (select/drag/rotate/flip/snap/note/export). Not yet exercised in a real Safari/Firefox session.

## Test-strength baseline (mutation testing, 2026-11-05)

Branch coverage of the library is 90%, but a mutation run (`tools/mutate.py`: one AST change at a time in a copy
of the package - flipped operators, constants, comparisons - then the suite) kills only **576/1221 = 47%**
of mutants. Raw results: `docs/mutation_baseline_2026-11-05.json`.

| module | mutants | killed | score |
|---|---|---|---|
| `placement.py` | 293 | 28 | 9% |
| `panel.py` | 23 | 8 | 34% |
| `config.py` | 100 | 40 | 40% |
| `casings.py` | 109 | 49 | 44% |
| `joints.py` | 80 | 38 | 47% |
| `components.py` | 72 | 35 | 48% |
| `layout.py` | 40 | 23 | 57% |
| `dormer_geometry.py` | 34 | 20 | 58% |
| `render.py` | 36 | 22 | 61% |
| `mates.py` | 33 | 21 | 63% |
| `cutouts.py` | 117 | 76 | 64% |
| `geometry.py` | 56 | 37 | 66% |
| `builders/dormer.py` | 68 | 45 | 66% |
| `assembly.py` | 13 | 9 | 69% |
| `svgpath.py` | 49 | 36 | 73% |
| `builders/chimney.py` | 64 | 56 | 87% |
| `builders/box.py` | 34 | 33 | 97% |

Root causes of surviving mutants (what to fix in the tests):
1. absolute dimensions are never asserted (only relations between panels), so common-mode errors pass (e.g. `x_kerf = x - k`);
2. drawn geometry is not cross-checked against the declared plan (slot paths, dormer face outline, footprint triangle, casing outlines, `Panel.area/cut_length`);
3. boundary/validation conditions (`<` vs `<=`, `or` vs `and`) in components, config keep-outs, layout spacing, joint thresholds;
4. finger-layout policy (count ladder, gaps, symmetry, `single_joints`) has no property tests;
5. wiring/indexing of mates and slots is only checked by count;
6. automatic window/door placement heuristics have almost no specified invariants (placement.py 10%).


## Open / next

1. (done) Ridge at angles other than 45° is an accepted, quantified limit that needs hand finishing (C-16); window/door kerf compensation is done (C-27).
2. (done) Arched window casing apex thickness (C-28).
3. **Mutation testing** - paused at the owner's request (the earlier full run exhausted memory). Baseline above (47%) is from before items 1-6; re-measure with the lighter approach discussed (run only the tests that cover the mutated line, one worker, per module). `tools/mutate.py` now refuses more than 3 workers and checks free memory first.
4. Chimney base and casing are glued to the roof (a vertical tab through a sloped roof needs a skewed slot); dormer valleys likewise. Dormers still use the global finger length - the chimney's scaled-finger rule could give small dormers joints too.
5. `roof_slot_rects` lives in `HouseGeometry` because both `config` (avoid slots) and the box builder need it; it is joint policy and could move to a small shared module.
6. C-14 real roof types; A-17 doc consolidation (owner decision).
7. Review page: first real Safari/Firefox session may surface UI polish; feedback -> regression-test conversion is manual for now (a `review triage` command could generate failing-test skeletons from collected pins).
