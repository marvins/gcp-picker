#  Automatic GCP Solver — Strategy & Plan

## Overview

The goal is a fully automatic pipeline that finds, filters, and fits Ground Control Points
without manual user interaction.  The user provides a test image and a reference source
(satellite basemap tiles, ortho mosaic, or another georeferenced image); the solver returns
a fitted projector model ready for orthorectification.

Manual GCPs remain the ground truth for validation and override, but the auto-solver handles
the heavy lifting for initial registration and for large collections where manual placement
does not scale.

## Algorithm Selection

The solver supports two complementary approaches:

### ALGO1: Keypoint-Based Matching (Classical)
- **Method**: Feature extraction (AKAZE/ORB) → descriptor matching → outlier rejection
- **Strengths**: Well-established, works well when images have good texture/contrast
- **Weaknesses**: Struggles with cross-modal (IR ↔ visible) and low-contrast imagery
- **Use Case**: Default for visible-spectrum pairs with good texture

### ALGO2: Edge-Based Genetic Algorithm Alignment
- **Method**: Sobel edge detection → differential evolution optimization → synthetic GCP extraction
- **Strengths**: More robust to radiometric domain shifts, works with lower resolution
- **Weaknesses**: Requires more GCPs for RPC fitting, slower due to GA optimization
- **Use Case**: IR ↔ visible, low-contrast, or when ALGO1 fails

Both algorithms can be selected via the `Auto_Algo` enum in the configuration. The system
automatically combines manual GCPs (if available) with algorithm-generated GCPs to solve
the appropriate projector model (Affine or RPC) based on the total GCP count.

---

### Panel: "Auto Match"
A dedicated **"Auto Match"** tab is added to the sidebar, separate from the "Ortho" tab.
The Ortho tab handles model fitting from GCPs; the Auto Match tab handles automatic GCP
discovery. The two workflows compose naturally: Auto Match produces GCPs → Ortho fits
a model from them.

The panel is **run-all-at-once**: all three stages (feature extraction, matching, outlier
rejection) execute in a single "Run Auto-Match" action. Results are displayed immediately.
The user can then adjust settings and re-run, or switch to the GCP tab to manually refine
the auto-generated points before fitting.

```
┌─ Auto Match ──────────────────────────────────────────┐
│  ── Algorithm ────────────────────────────────────     │
│  Strategy         [ ALGO1 ▼ ]  (ALGO1/ALGO2)         │
│  ☑ Use Manual GCPs as Prior                           │
│                                                       │
│  ── ALGO1: Keypoint-Based ───────────────────────     │
│  Method           [ AKAZE ▼ ]  (AKAZE/ORB)           │
│                                                       │
│  ── ALGO2: Edge-Based GA ───────────────────────     │
│  Edge Dilation   [ 3 ]                                │
│  GA Popsize      [ 15 ]                               │
│  GA Maxiter      [ 200 ]                              │
│                   (shown only when ALGO2 selected)     │
│                                                       │
│  ── Feature Extraction ──────────────────────────     │
│  Max Features     [ 2000      ]                       │
│  Pyramid Level    [ 2 ▼ ]  (runs at 1/4 res)          │
│  CLAHE Pre-proc   [ ☑ ]                               │
│                                                       │
│  ── AKAZE Parameters ───────────────────────────      │
│  Threshold        [ 0.0010 ]  (lower = more kps)      │
│  Octaves          [ 4 ]                               │
│  Octave Layers    [ 4 ]                               │
│                   (hidden when ORB selected)          │
│                                                       │
│  ── ORB Parameters  ────────────────────────────      │
│  Scale Factor     [ 1.20 ]                            │
│  Levels           [ 8 ]                               │
│  Edge Threshold   [ 31 ]                              │
│  Patch Size       [ 31 ]                              │
│                   (hidden when AKAZE selected)        │
│                                                       │
│  ── Matching ────────────────────────────────────     │
│  Ratio Test       [ 0.75 ]                            │
│  Matcher          [ FLANN ▼ ]                         │
│                                                       │
│  ── Outlier Rejection ───────────────────────────     │
│  Method           [ RANSAC ▼ ]                        │
│  Inlier Threshold [ 3.0 px ]                          │
│                                                       │
│  ── Results ─────────────────────────────────────     │
│  Candidates       —                                   │
│  Inliers          —                                   │
│  Coverage         —                                   │
│  RMSE             —                                   │
│                                                       │
│           [  Run Auto-Match  ]                        │
└───────────────────────────────────────────────────────┘
```

### Match_Algo Enum
Defined in `pointy/core/auto_match.py`:

```python
class Match_Algo(Enum):
    AKAZE = 'akaze'  # Default; built into OpenCV, good for aerial/IR
    ORB   = 'orb'    # Fast, no extra deps; weaker at large scale changes
    # Phase 4:
    # SUPERPOINT = 'superpoint'  # DL, requires torch
    # LIGHTGLUE  = 'lightglue'   # DL, requires torch
```

Each enum value maps to a `Feature_Extractor` subclass. Adding a new algorithm
requires only a new enum entry and a corresponding extractor implementation.

### Algo-Specific Tunable Parameters

**AKAZE** (`AKAZE_Params` dataclass):

| Parameter | Default | Range | Effect |
|---|---|---|---|
| `threshold` | 0.001 | 0.0001–0.05 | Detector response threshold — lower → more keypoints |
| `n_octaves` | 4 | 1–8 | Maximum octave evolution of the image |
| `n_octave_layers` | 4 | 1–8 | Sub-levels per scale octave |

**ORB** (`ORB_Params` dataclass):

| Parameter | Default | Range | Effect |
|---|---|---|---|
| `scale_factor` | 1.2 | 1.05–2.0 | Pyramid decimation ratio — smaller = finer scale steps |
| `n_levels` | 8 | 1–16 | Number of pyramid levels |
| `edge_threshold` | 31 | 1–64 | Border size (px) where features are not detected |
| `patch_size` | 31 | 1–64 | Patch size for oriented BRIEF descriptor |

The panel shows only the parameter group relevant to the selected algorithm;
the other group is hidden.

### Manual GCPs as Spatial Prior
When "Use Manual GCPs as Prior" is checked and manual GCPs exist for the current image:

1. **Footprint estimation**: the geographic bounding box of the manual GCPs is used to
   seed the reference chip request, replacing the cold-start fallback.
2. **Match search constraint**: pixel↔geo correspondences from manual GCPs define a
   plausible affine prior; candidate matches that violate it beyond a configurable
   tolerance (default ±500 px) are discarded before RANSAC.
3. **GCP merging**: after auto-matching succeeds, manual GCPs are merged with the
   auto-GCP candidates. Manual GCPs take priority (they are never overwritten);
   auto-GCPs fill spatial gaps. The merged set is passed to the Ortho tab for fitting.

Manual GCPs carry `source='manual'` and auto-GCPs carry `source=<Match_Algo.value>`,
using the `source` field already present on the `GCP` dataclass.

---

## Pipeline Stages

### ALGO1: Keypoint-Based Pipeline

```
Test Image  ──┐
              ├──► 1. Feature Extraction (AKAZE/ORB)
Reference   ──┘
                         │
                         ▼
              2. Feature Matching  (cross-descriptor + spatial priors)
                         │
                         ▼
              3. Outlier Rejection  (RANSAC / geometric filtering)
                         │
                         ▼
              4. Candidate GCP Set  (filtered match pairs)
                         │
                         ▼
              5. Model Fitting  (Affine/RPC from GCPs)
                         │
                         ▼
              6. Result  →  Projector + optional manual review
```

### ALGO2: Edge-Based GA Pipeline

```
Test Image  ──┐
              ├──► 1. Sobel Edge Detection
Reference   ──┘
                         │
                         ▼
              2. Differential Evolution Optimization
                         │
                         ▼
              3. Extract Synthetic GCPs (grid pattern)
                         │
                         ▼
              4. Combine with Manual GCPs (if available)
                         │
                         ▼
              5. Model Fitting (Affine/RPC based on GCP count)
                         │
                         ▼
              6. GeoTiff Generation (optional)
                         │
                         ▼
              7. Result  →  Projector + optional manual review
```

---

## ALGO2: Edge-Based GA Details

### Stage 1 — Sobel Edge Detection

Both test and reference images are converted to edge maps using Sobel gradient magnitude:
- Optional dilation to thicken edges for robustness
- Otsu thresholding to binarize edges
- Normalized cross-correlation (NCC) used as fitness metric

### Stage 2 — Differential Evolution Optimization

A genetic algorithm optimizes the parameters of the ortho model (Affine, TPS, or RPC):
- **Parameters**: Model-specific parameters extracted via `to_params()` (e.g., 6 for Affine, 16 for RPC)
- **Bounds**: Model-specific bounds (±50 pixels for translation, ±20% for scale/shear)
- **Fitness**: NCC between transformed test edges and reference edges
- **Solver**: `scipy.optimize.differential_evolution`
- **Settings**: popsize=15, maxiter=200, mutation=(0.5,1.0), recombination=0.7

### Stage 3 — Synthetic GCP Extraction

After GA converges, GCPs are extracted using a grid pattern:
- **Grid**: 4x4 points across the test image (16 synthetic GCPs)
- **Transform**: Grid points transformed using the converged ortho model
- **Geo mapping**: Transformed points mapped to geographic coordinates via reference geo transform
- **Purpose**: Provides well-distributed points for model fitting

### Stage 4 — Manual GCP Combination

Manual GCPs (if available) are combined with synthetic GCPs:
- Manual GCPs take priority (ground truth)
- Combined set used for model fitting
- Improves model accuracy when manual GCPs are available

### Stage 5 — Model Fitting

Based on total GCP count, the appropriate model is solved:
- **RPC**: ≥40 GCPs (full version) or ≥9 GCPs (simplified 9-term polynomial)
- **Affine**: ≥3 GCPs (minimum for 3-DOF affine)
- **Model selection**: Automatic based on GCP availability

### Stage 6 — GeoTiff Generation (Optional)

If a projector model is solved, a georectified GeoTiff can be generated:
- Uses `projector.warp_extent()` to get geographic bounds
- Warps image using `cv2.remap()` with projector's remap coordinates
- Saves as GeoTIFF with proper CRS and transform metadata

### GCP Extraction Strategy Discussion

**Current Approach (Grid Pattern):**
- Extracts GCPs from a regular 4x4 grid
- **Pros**: Guaranteed spatial distribution, deterministic, simple
- **Cons**: May not align with actual image features

**Alternative (Edge-Based GCPs):**
- Extract GCPs from actual edge features (corners, intersections, strong edge points)
- **Pros**: More likely to be accurate since they correspond to real features
- **Cons**: Edges can be noisy, may not be well-distributed, more complex

**Recommendation:**
- Start with grid pattern (current implementation) for reliability
- Consider hybrid approach: use edge features where available, fall back to grid
- Edge features could be extracted using Harris corner detection or edge intersection points
- This would be a future enhancement to improve GCP quality

---

## ALGO1: Keypoint-Based Details

## Stage 1 — Feature Extraction

### Detectors / Descriptors

| Method | Strengths | Weaknesses | Use Case |
|---|---|---|---|
| **AKAZE** | Non-linear scale space, good for aerial/IR, built-in OpenCV | Slower than ORB | **Default** — aerial/satellite pairs |
| **ORB** | Fast, free, binary descriptor, no extra deps | Less accurate at large scale changes | Fast fallback / real-time |
| **SuperPoint** (DL) | Excellent cross-domain matching | Requires model weights, GPU beneficial | IR ↔ visible, off-nadir |
| **LightGlue / SuperGlue** (DL) | State-of-art matching quality | Heavy inference cost | High-accuracy, batch |

### Multi-Scale Extraction
- Extract features at multiple pyramid levels (see `tiling-and-pyramids.md`).
- Pyramid level chosen based on estimated GSD ratio between test and reference.
- Limits descriptor count to a tractable number on large images.

### Reference Image Acquisition
The reference source is basemap tiles (Leaflet/WMS), so tiles covering the test image's
estimated footprint must be fetched and assembled into a single reference chip at a
comparable GSD to the test image.

- Footprint estimated from image metadata (if available) or from a prior rough model.
- Tile GSD must be within ~4× of test image GSD for reliable matching.
- Reference chip cached locally (keyed on bbox + zoom level).

---

## Stage 2 — Feature Matching

### Cross-Descriptor Matching
- Brute-force or FLANN-based nearest-neighbour in descriptor space.
- Lowe's ratio test (`0.75` default) to reject ambiguous matches.

### Spatial Priors
If a rough geographic footprint is known (e.g. from GPS/metadata or a previous manual model):
- Only consider matches within a plausible pixel-offset range.
- Reduces search space and false positives significantly.

### Cross-Modal Matching (IR ↔ Visible)
The test imagery is IR; reference tiles are visible-spectrum. Standard descriptors degrade
on cross-modal pairs. Mitigations:
- Histogram equalisation / CLAHE before extraction.
- Mutual information-based feature response instead of gradient-based.
- Deep learning matchers (SuperPoint/LightGlue) trained on multi-spectral pairs — preferred
  long-term solution.

---

## Stage 3 — Outlier Rejection

### RANSAC
Standard geometric RANSAC fitting a homography or affine model:
- Inlier threshold: 2–5 px (depends on GSD).
- Minimum sample size: 4 (homography), 3 (affine).
- Iterations: adaptive based on inlier ratio estimate.
- OpenCV `cv2.findHomography(..., cv2.RANSAC)` or `cv2.estimateAffinePartial2D`.

### MAGSAC / MAGSAC++ (Improved RANSAC)
- Soft inlier weighting instead of hard threshold.
- More robust to heteroscedastic noise (common when mixing image sources).
- Available via `pydegensac` or `kornia`.

### Progressive Sample Consensus (PROSAC)
- Samples from high-quality matches first (sorted by descriptor distance).
- Reaches good models faster than uniform RANSAC.

### Geometric Consistency Filter (post-RANSAC)
After RANSAC, verify remaining matches:
- Cross-check: match A→B and B→A must agree.
- Epipolar constraint if stereo geometry is known.
- Direction consistency: for an aerial image, longitude should increase monotonically
  with one pixel axis — flag violations (as seen with manually misplaced GCPs).

---

## Stage 4 — Candidate GCP Set

After filtering, matches are downsampled to a manageable set (e.g. 20–100 points):
- **Spatial coverage**: grid the image into N×N cells; select the best match per cell.
  Ensures GCPs span the full image extent rather than clustering.
- **Quality ranking**: rank by RANSAC inlier score + descriptor distance + spatial uniqueness.
- **Minimum set**: retain at least 6–12 well-distributed candidates before passing to model search.

---

## Stage 5 — Model Search

### Option A: Direct Least-Squares (Baseline)
Feed the filtered GCP candidates directly to `projector.solve_from_gcps()`.
Fast, deterministic. Works well if RANSAC left high-quality inliers.

### Option B: Genetic Algorithm (GA)

A GA searches for the subset of candidates that yields the lowest residual model.

**Encoding**: chromosome = binary mask over the candidate GCP set (1 = include, 0 = exclude).

**Fitness function**:
```
fitness = 1 / (RMSE + λ * penalty_for_poor_coverage)
```
where coverage penalty discourages solutions that cluster GCPs in one image region.

**Operators**:
- Selection: tournament selection (size 3–5).
- Crossover: single-point or uniform.
- Mutation: flip individual GCP inclusion bits (rate ~0.02).
- Elitism: keep top 5% of population unchanged.

**Termination**: max generations (e.g. 200) or stagnation (no improvement in 20 generations).

**Population size**: 50–100 chromosomes (tractable for 20–100 candidate GCPs).

**Libraries**: `DEAP`, `pymoo`, or custom NumPy implementation (lightweight).

### Option C: Bayesian Optimisation (BO)
Treat GCP subset selection + model hyperparameters as a black-box optimisation.
- Surrogate model: Gaussian Process over the discrete GCP inclusion space.
- Acquisition: Expected Improvement.
- Suitable when fitness evaluation is expensive (TPS/RPC fitting).
- `scikit-optimize` or `botorch`.

### Option D: Simulated Annealing
- Start with all candidates included; randomly remove/add GCPs.
- Accept worsening solutions with probability `exp(-ΔE / T)`.
- Simple to implement, good for medium candidate sets.
- No external dependencies beyond NumPy.

### Recommended Strategy
1. Try **Option A** first — if RANSAC quality is high, direct solve is sufficient.
2. If RMSE > threshold (e.g. 5 px), escalate to **GA (Option B)**.
3. Use **BO (Option C)** for RPC models where fitting is expensive and evaluations must be minimised.

---

## Stage 6 — Model Validation

After fitting, run automated checks before accepting the model:

- **Per-GCP residual**: flag GCPs with residual > 3σ; optionally auto-remove and refit.
- **Roundtrip test**: `source → geo → source` for each GCP; error should be < 0.5 px.
- **Coverage score**: compute convex hull of GCP set; flag if hull area < 50% of image area.
- **Boundary extrapolation check**: project all four image corners; flag if any land outside
  the expected geographic extent (±10% of fitted extent).
- **Cross-validation**: if ≥12 GCPs, hold out 20%, fit on 80%, report hold-out RMSE.

Results are surfaced in the `Transformation_Status_Panel` with a confidence indicator:

| Confidence | Criteria |
|---|---|
| ✅ High | RMSE < 2 px, coverage > 70%, roundtrip < 0.5 px |
| ⚠️ Medium | RMSE 2–8 px, coverage 40–70% |
| ❌ Low | RMSE > 8 px, coverage < 40%, or boundary failure |

---

## Stage 7 — Result & Manual Review

- Fitted projector is set via `main_window.set_projector()` — same path as manual fitting.
- All auto-GCPs are added to the GCP manager table (tagged as `AUTO`).
- User can review, delete, or adjust individual auto-GCPs.
- Re-fit is triggered automatically if the user modifies the set.

---

## Cross-Modal Matching (IR ↔ Visible) — Deep Dive

This is the hardest problem for this dataset. Strategies in priority order:

1. **CLAHE pre-processing**: Contrast Limited Adaptive Histogram Equalisation on both
   images before feature extraction. Cheap, often sufficient for near-IR.

2. **Gradient-domain matching**: Convert both images to edge maps (Canny or Sobel).
   Edges are more invariant to radiometric domain shifts than raw intensity.

3. **Mutual Information keypoint response**: Use MI as the feature response function
   instead of gradient magnitude (less standard, more robust cross-domain).

4. **SuperPoint + LightGlue**: Pre-trained on varied domains; fine-tune on IR/visible pairs
   if labelled data is available. Requires `torch` dependency.

5. **Template matching at coarse resolution**: Cross-correlate downsampled images to get
   a rough translation/rotation prior, then refine with local feature matching.

---

## Performance Considerations

| Stage | Cost | Optimisation |
|---|---|---|
| Feature extraction | O(W×H) | Run at pyramid level 2–3 (1/4–1/8 res) |
| Descriptor matching | O(N²) brute-force → O(N log N) FLANN | FLANN index for N > 1000 |
| RANSAC | O(iterations × sample_size) | Adaptive stopping, PROSAC ordering |
| GA fitness eval | O(population × GCP_count × fit_cost) | Vectorised residual; cache matrix inverses |
| Reference tile fetch | Network I/O | Local tile cache (MBTiles or disk) |

---

## Implementation Plan

### Phase 0 — UI Shell ✅ Complete
The full "Auto Match" panel UI and controller skeleton are implemented.

- [x] `Match_Algo` enum + `AKAZE_Params` + `ORB_Params` + `Auto_Match_Settings` in `pointy/core/auto_match.py`
- [x] `Auto_Match_Panel` widget (`pointy/sidebar/components/auto_match_panel.py`)
  - Algorithm selector with per-algo parameter groups (AKAZE / ORB); inactive group hidden
  - "Use Manual GCPs as Prior" checkbox
  - Feature Extraction group: Max Features, Pyramid Level, CLAHE toggle
  - Matching group: Ratio Test, Matcher (Brute-force / FLANN)
  - Outlier Rejection group: Method (RANSAC / MAGSAC), Inlier Threshold
  - Results group: Candidates, Inliers, Coverage, RMSE (read-only)
  - "Run Auto-Match" button emitting `run_requested` signal
- [x] `Auto_Match_Controller` skeleton (`pointy/controllers/auto_match_controller.py`)
  - Wires `run_requested` signal; validates preconditions; logs settings; stub returns early
- [x] `Tabbed_Sidebar` gains "Match" tab; `get_auto_match_panel()` accessor
- [x] `Main_Window` instantiates and connects `Auto_Match_Controller`

### Phase 1 — Classical Matching Infrastructure

Core pipeline classes defined in `pointy/core/auto_matcher.py`:

```
Feature_Extractor (ABC)
    AKAZE_Extractor        — cv2.AKAZE_create()
    ORB_Extractor          — cv2.ORB_create()
    make_extractor()       — factory driven by Match_Algo enum

Feature_Matcher            — kNN + Lowe ratio test; BF or FLANN

Outlier_Filter (ABC)
    RANSAC_Filter          — cv2.findHomography(..., RANSAC)
    MAGSAC_Filter          — cv2.findHomography(..., USAC_MAGSAC)
    make_outlier_filter()  — factory driven by Rejection_Method enum

GCP_Candidate_Set          — NxN spatial grid; best match per cell
Match_Result               — output dataclass (pixels, geos, mask, stats)
Auto_Matcher               — orchestrates all stages; .run() entry point
```

Remaining Phase 1 tasks:
- [ ] `Reference_Chip_Builder`: fetches and assembles reference tiles for a given bbox + GSD
- [ ] Wire `Auto_Matcher.run()` into `Auto_Match_Controller.on_run_requested()`
- [ ] Manual GCP prior integration in `Auto_Match_Controller`
  - Footprint from manual GCP bounding box → reference chip bbox
  - Pre-RANSAC spatial filtering using affine prior from manual pairs
- [ ] Convert `Match_Result` candidates → `GCP` objects with `source=Match_Algo.value`
- [ ] Push candidate GCPs into `GCP_Processor` and update GCP manager table
- [x] `Match_Results_Panel` widget in `Auto_Match_Panel`: stat chips + candidate table
- [x] `Auto_Match_Panel.update_results()` accepts `candidate_rows` list to populate table
- [ ] Wire controller → `panel.update_results()` with live `Match_Result` stats after run

### Sobel Preview Panel (TODO — needs design)

Users need to see the Sobel edge images directly in the GUI to tune `test_pre_blur`,
`ref_pre_blur`, `test_dilation`, `ref_dilation`, and `sobel_threshold` without running the
full pipeline and inspecting files in `temp/debug/`.

**Design sketch:**
- Add a "Preview Edges" button to the `Auto_Match_Panel` (or a separate debug sub-panel).
- On click, run `Sobel_Edges.detect()` on the loaded test image and reference chip using the
  current config settings (without running the GA).
- Display the resulting `float32 [0, 1]` edge images in a small side-by-side viewer — either
  a dedicated `QDialog` with two `QLabel` pixmaps, or by reusing the existing
  `Test_Image_Viewer` / reference viewer with a toggle mode.
- Overlay the current parameter values (`pre_blur`, `dilation`, `threshold`, `kernel_size`)
  as a text annotation on each preview image.
- Consider a live "sliders → preview" mode so the user can scrub parameters without
  re-running.

**Key constraint:** The preview must use the *same* `Sobel_Edge_Settings` objects that the
`Edge_Aligner` will use, derived from the parsed config, to guarantee WYSIWYG fidelity.

**Deferred until Phase 1 controller wiring is stable.**

---

### Viewer Candidate Drawing (TODO — needs design)

After `Auto_Matcher.run()` returns `Match_Result.candidate_pixels` (Nx2, full-res image
space), we want to draw those as cyan crosses on `Test_Image_Viewer`.

**What's ready:**
- `Graphics_Image_View.set_candidate_markers(pts)` / `clear_candidate_markers()` — paints
  cyan crosses at provided (x, y) scene coords on each `paintEvent`.
- `Test_Image_Viewer.set_candidate_markers(pts)` / `clear_candidate_markers()` — thin
  passthroughs to `image_view`.

**Open question — coordinate space:**
`candidate_pixels` are in full-res image coordinates (pyramid scale already applied back
in `pipeline.py` via `* scale`).  `Graphics_Image_View` scene coordinates are also
full-res image pixels (1:1 with the loaded image).  So **no extra transform is needed**
in the raw (non-orthorectified) view.  However:

- In orthorectified view (`is_orthorectified=True`), the scene shows the warped output
  grid, not the original image.  Candidate markers must be projected through the fitted
  projector to ortho-pixel space, same as `draw_gcp_points()` does.  This requires a
  fitted projector to be present — if none exists, markers are simply not drawn in ortho
  mode.
- `Auto_Match_Controller` needs access to `test_viewer` (already has it) to call
  `set_candidate_markers(result.candidate_pixels.tolist())` after a successful run.
- `clear_candidate_markers()` should be called at the start of each new run (in
  `on_run_requested` before `panel.clear_results()`).

**Deferred until controller pipeline wiring (Phase 1) is complete.**

### Phase 2 — Model Search & Merge
- [ ] Direct least-squares baseline (reuse `fit_transformation_model`)
- [ ] GA solver (`DEAP` or custom NumPy) with coverage-aware fitness
- [ ] Simulated Annealing fallback (no extra dependencies)
- [ ] GCP merge: auto-GCPs injected into `GCP_Processor` with `source=Match_Algo.value`;
  manual GCPs preserved; merged set forwarded to Ortho tab for fitting

### Phase 3 — Validation
- [ ] `Model_Validator`: roundtrip, coverage, boundary, cross-validation checks
- [ ] Confidence indicator (`✅ High / ⚠️ Medium / ❌ Low`) surfaced in results group
- [ ] Auto-GCP display in GCP manager table (tagged by `source`, editable/deletable)

### Phase 4 — Deep Learning Matching
- [ ] SuperPoint + LightGlue integration (optional `torch` extra)
- [ ] `SUPERPOINT` and `LIGHTGLUE` entries added to `Match_Algo`; hidden if `torch` absent
- [ ] Fine-tuning pipeline on IR/visible pairs from the collection
- [ ] Fallback to AKAZE if `torch` not available

---

## Bug Fixes & Known Issues

### Remaining Issues — TODO

#### TODO-01 — `Edge_Aligner` requires a pre-existing `Projector`; no cold-start  🔴 High
`edge_aligner.align()` raises `ValueError("No projector model available for
optimization")` if neither the constructor nor the call-site supplies an
`initial_model`.  There is no cold-start path for the common case where no
prior model exists.

**Design direction:** Require the user to provide 1-2 manual GCPs to create a
basic/degraded Affine model that can constrain the optimization problem.  The
GA optimizer can then refine this initial affine using edge alignment.  This
is more robust than a metadata-based cold-start since it grounds the solution
in known ground control points.

#### TODO-02 — `GA_Optimizer._warp_with_model` falls back to resize for non-Affine  🔴 High
```python
else:
    return cv2.resize(image, (w, h))   # ← nonsense for RPC/TPS
```
For any non-Affine model the fitness function returns a meaningless score.
The optimizer will "converge" on garbage parameters.

**Needed:** Implement a proper remap path for RPC/TPS using
`projector.compute_remap_coordinates()`, reusing the same code path as
`transformation.warp_image()`.  Consider extracting a shared
`remap_with_projector(image, projector, output_size)` helper in
`pointy.core.transformation` and calling it from both `warp_image` and the
GA fitness function.

#### TODO-03 — GCP extraction uses model's own `pixel_to_world`; ignores ref image  🟡 Medium
`_extract_gcps_from_model` maps grid points through `model.pixel_to_world()`
but never uses `ref_geo_transform`.  This is correct for the fitted model
but discards the ability to validate against the reference chip — e.g. to
verify that the projected geo coordinates actually land in the reference tile
bounds.

**Suggested:** After extracting geo points, verify they lie within the reference
chip bounds; flag or drop points that fall outside.

#### Affine Bootstrap as a Seed for RPC / TPS Refinement

The current non-Affine path already does this implicitly: it projects the 4 test image
corners through the prior model (TPS or RPC) to produce geographic anchors, fits an Affine
to those 4 points, and hands that Affine to the GA.  The GA then refines the Affine via edge
alignment.  The question is whether the converged Affine can be used to *improve* the
subsequent RPC or TPS fit.

**What GCPs are needed for the bootstrap Affine?**

The bootstrap currently uses the prior model's own `pixel_to_world` to synthesize 4 corner
GCPs — so it requires a prior model (TPS, RPC) that already maps pixel → geo.  If no prior
model is available, the minimum real GCP requirements for the degraded cases are:

| GCPs | DOF solved | What you get |
|------|-----------|--------------|
| 1    | Translation (2) | Origin shift only — place image center at the GCP geo coordinate. Scale and rotation are assumed from metadata (GSD + north-up). |
| 2    | Translation + rotation (3) | Estimate bearing from the pixel-to-pixel vector vs geo-to-geo vector. Scale still from metadata. |
| 3    | Full Affine (6) | Unique least-squares solution — scale, rotation, shear, translation all free. This is the minimum for a properly constrained Affine. |

In practice the 1- and 2-GCP cases require a known GSD (from image metadata or the config)
to set the scale.  Without it the transform is underdetermined and the GA search bounds will
be unbounded.

**Implication for cold-start:** Rather than requiring a full prior model, we could accept
1–3 manual GCPs and construct a degraded Affine as the GA seed.  This is the design direction
noted in TODO-01.

**It can also improve an existing prior model, and here is the mechanism:**

1. **Affine → GCP grid** — after the GA converges, `_extract_gcps_from_model` samples a
   regular grid of pixel→geo pairs from the refined Affine.  These synthetic GCPs are already
   more accurate than the original prior because they have been edge-aligned.

2. **RPC seeding** — pass the synthetic GCPs as additional observations when solving the RPC
   polynomial system.  The existing RPC coefficients act as a regulariser (prior), and the
   GCPs provide the correction signal.  Concretely: solve a *delta* RPC (offset model) on top
   of the existing coefficients using the GCP residuals.

3. **TPS seeding** — re-solve the TPS directly from the synthetic GCPs.  TPS is interpolatory
   so it will pass exactly through the grid points, giving a refined warp that is consistent
   with the edge-aligned Affine in the interior and falls back to the prior near the edges.

**Limits of the approach:**

- The Affine bootstrap is a *rigid* model (6 DOF).  If the true distortion is nonlinear
  (e.g. radial lens distortion, terrain relief), the Affine will absorb the mean shift but
  leave residuals.  The GCP grid extracted from it will carry those residuals into the
  RPC/TPS re-solve.
- 4 corners give a sparse constraint for a high-order RPC.  The GA's full GCP grid
  (currently 4×4 = 16 points) is far better — use that, not just the bootstrap corners.
- For TPS this is fine: 16 well-spread control points give a good thin-plate solution.
  For RPC the system is overdetermined (80 coefficients, 16 observations) so regularisation
  is required — consider fixing all coefficients except the bias/translation offsets.

**Recommended implementation order:**
1. RPC delta-offset solve from Affine-derived GCPs (small change, high payoff).
2. TPS re-solve from Affine-derived GCPs (already almost implemented — just wire it up).
3. Iterative refinement: re-run edge alignment with the updated RPC/TPS as the new prior.

---

#### TODO-RPC — Direct RPC parameter optimization in GA  🔴 High

The GA currently bootstraps an `Affine` from RPC corner projections when the initial model is
an RPC.  This loses the RPC's geometric accuracy and converges on a coarser solution.

**Design direction:** Implement `RPC.to_params()` / `RPC.from_params()` exposing a compact
offset vector over the rational polynomial coefficients (bias offsets on numerator/denominator
coefficients are sufficient — typically 10–20 free parameters).  Update `_affine_param_bounds`
in `ga_optimizer.py` to accept any model type and dispatch to a model-specific bounds function.
**Start here** — RPC is the highest-value model type for the aerial/satellite imagery this tool
targets.

#### TODO-TPS — Direct TPS refinement support  🟡 Medium

TPS has no compact parameter vector (it is defined by its control-point weights), so direct GA
optimisation is not practical.

**Design direction:** After the GA converges on a bootstrap Affine, use the synthetic GCPs
extracted from that Affine to re-solve the TPS.  The refinement loop then becomes:
1. Bootstrap Affine → GA → refined Affine
2. Extract GCP grid from refined Affine
3. Re-solve TPS from updated GCPs
4. Validate TPS RMSE; iterate if needed

Tackle after RPC support is stable.

---

## Open Questions

1. **Reference tile resolution**: What zoom level best matches the test image GSD?
   Need to compute dynamically from `geo_scale_at_center()` or image metadata.

2. **Cold start (no prior model)**: How to estimate the reference footprint before any
   model is fitted?
   - **Resolved (partially)**: if manual GCPs exist, their geographic bounding box is used.
   - **Remaining**: when no manual GCPs exist — options are GPS metadata embedded in image,
     user-specified bbox in the Auto Match panel, or brute-force tile search at coarse
     resolution. A "Set Footprint" control in the panel may be needed.

3. **GA vs SA**: For typical GCP candidate sets (20–60 points), both are tractable.
   GA is more parallelisable; SA is simpler to implement. Evaluate empirically in Phase 2.

4. **Cross-modal training data**: Do we have enough IR/visible pairs from this collection
   to fine-tune SuperPoint/LightGlue? If not, rely on CLAHE + gradient matching initially.
   Deferred to Phase 4.

5. **Confidence threshold for auto-accept**: Resolved — the solver never silently auto-accepts.
   Results always appear in the Auto Match panel; the user explicitly switches to the Ortho
   tab and hits "Fit" to commit. High-confidence results are highlighted but not force-applied.

6. **Integration with model persistence**: Auto-solved models follow the same sidecar path
   as manually fitted models (`image.png.ortho.json`). The `source` field on each auto-GCP
   (`source=Match_Algo.value`) records the algorithm used. No separate flag is needed in
   the sidecar; GCP provenance is carried in the GCP sidecar (`image.png.gcps.json`).

7. **Settings persistence**: Should Auto Match panel settings (algo, ratio test, threshold,
   etc.) persist between sessions? Likely yes — store in `collection_config.toml` under a
   new `[auto_match]` section, or as a per-image sidecar setting. TBD.

8. **Partial re-run**: Should the user be able to run only the outlier rejection step with
   new threshold settings without re-running feature extraction (which is the slowest step)?
   The run-all-at-once design keeps the UI simple; caching extracted features between runs
   would enable partial re-runs without complicating the UI.