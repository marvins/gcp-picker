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
| **SIFT** | Scale & rotation invariant, robust | Slow, patent-expired but needs `opencv-contrib` | General default |
| **ORB** | Fast, free, binary descriptor | Less accurate at large scale changes | Mobile / real-time |
| **AKAZE** | Non-linear scale space, good for aerial | Slower than ORB | Aerial/satellite pairs |
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

### Phase 1 — Infrastructure
- [ ] `Reference_Chip_Builder`: fetches and assembles reference tiles for a given bbox + GSD
- [ ] `Feature_Extractor` ABC: wraps OpenCV SIFT/ORB/AKAZE; returns `(keypoints, descriptors)`
- [ ] `Feature_Matcher`: ratio test + cross-check; returns raw match list
- [ ] `RANSAC_Filter`: wraps `cv2.findHomography` RANSAC; returns inlier matches
- [ ] `GCP_Candidate_Set`: spatially sampled, quality-ranked candidate list

### Phase 2 — Model Search
- [ ] Direct least-squares baseline (reuse `projector.solve_from_gcps`)
- [ ] GA solver (`DEAP` or custom) with coverage-aware fitness
- [ ] Simulated Annealing fallback (no extra dependencies)

### Phase 3 — Validation & UI
- [ ] `Model_Validator`: roundtrip, coverage, boundary, cross-validation
- [ ] Confidence indicator in `Transformation_Status_Panel`
- [ ] Auto-GCP display in GCP manager table (tagged `AUTO`, editable)
- [ ] "Auto-Solve" button in Ortho sidebar tab

### Phase 4 — Deep Learning Matching
- [ ] SuperPoint + LightGlue integration (optional `torch` extra)
- [ ] Fine-tuning pipeline on IR/visible pairs from the collection
- [ ] Fallback to classical if `torch` not available

---

## Open Questions

1. **Reference tile resolution**: What zoom level best matches the test image GSD?
   Need to compute dynamically from `geo_scale_at_center()` or image metadata.

2. **Cold start (no prior model)**: How to estimate the reference footprint before any
   model is fitted? Options: GPS metadata embedded in image, user-specified bbox, or
   brute-force tile search at coarse resolution.

3. **GA vs SA**: For typical GCP candidate sets (20–60 points), both are tractable.
   GA is more parallelisable; SA is simpler to implement. Evaluate empirically.

4. **Cross-modal training data**: Do we have enough IR/visible pairs from this collection
   to fine-tune SuperPoint/LightGlue? If not, rely on CLAHE + gradient matching initially.

5. **Confidence threshold for auto-accept**: Should the solver auto-accept high-confidence
   results silently, or always require user confirmation? Configurable per collection.

6. **Integration with model persistence**: Auto-solved models should save to the sidecar
   TOML (see `ortho-logic.md`) with a flag indicating they are auto-generated.
