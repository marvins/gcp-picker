#  Automatic GCP Solver — Strategy & Plan

## Overview

The goal is a fully automatic pipeline that finds, filters, and fits Ground Control Points
without manual user interaction.  The user provides a test image and a reference source
(satellite basemap tiles, ortho mosaic, or another georeferenced image); the solver returns
a fitted projector model ready for orthorectification.

Manual GCPs remain the ground truth for validation and override, but the auto-solver handles
the heavy lifting for initial registration and for large collections where manual placement
does not scale.

---

## UI Design

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
│  Method           [ AKAZE ▼ ]                         │
│  ☑ Use Manual GCPs as Prior                           │
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

```
Test Image  ──┐
              ├──► 1. Feature Extraction
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
              5. Model Search  (GA / grid search / BO)
                         │
                         ▼
              6. Model Validation  (residuals, coverage, roundtrip)
                         │
                         ▼
              7. Result  →  Projector + optional manual review
```

---

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
- [ ] Update `Auto_Match_Panel.update_results()` with live `Match_Result` stats

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
