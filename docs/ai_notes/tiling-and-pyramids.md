#  Tiling & Image Pyramid Plan

## Problem Statement

The current pipeline loads the full-resolution source image (e.g. 20K×20K) into memory as a single NumPy array and renders it directly via `QGraphicsView`. This creates several bottlenecks:

- **Memory**: A 20K×20K 3-band uint8 image is ~1.2 GB uncompressed. 16-bit or float images are 2×–4× larger.
- **Initial display latency**: The whole array must be decoded before anything appears.
- **Ortho warp**: The remap operates on the full array; TPS/RPC per-pixel loops over 400M+ pixels.
- **Panning/zooming**: The `QGraphicsView` scales the full pixmap on every render, which is slow at low zoom levels where most pixels are discarded.
- **Future**: Multi-image collections, 16-bit sensors, and stereo pairs will multiply these costs.

---

## Concepts

### Image Pyramid (Overview)
A pre-computed stack of progressively downsampled versions of the source image:

```
Level 0  →  20000 × 20000  (full resolution)
Level 1  →  10000 × 10000  (1/2)
Level 2  →   5000 ×  5000  (1/4)
Level 3  →   2500 ×  2500  (1/8)
Level 4  →   1250 ×  1250  (1/16)
Level 5  →    625 ×   625   (1/32)
```

The viewer selects the appropriate level based on the current zoom factor — no wasted decoding of pixels that will never be displayed.

### Tiling
Each pyramid level is divided into fixed-size tiles (e.g. 256×256 or 512×512). Only tiles that intersect the current viewport are decoded and rendered. This bounds memory usage regardless of image size.

### Existing Standard Formats
- **GeoTIFF with internal overviews** (`COMPRESS=LZW`, `TILED=YES`, `BLOCKXSIZE=512`) — GDAL-native, already in use via `rasterio` for terrain.
- **Cloud Optimised GeoTIFF (COG)** — overviews + tiling + HTTP range request support; ideal for remote imagery.
- **MBTiles / XYZ tiles** — SQLite-backed tile store; good fit for the Leaflet reference viewer.
- **Zarr** — chunked N-dimensional array format, good for hyperspectral / time-series.

---

## Proposed Architecture

### Tier 1 — In-Process Pyramid (Short Term)

Build a lightweight pyramid in memory on image load, without changing file formats.

**Implementation**:
1. After async load, downsample the full array into a `dict[int, np.ndarray]` pyramid using `cv2.pyrDown` or `cv2.resize`.
2. Store in `Test_Image_Viewer` alongside `original_image`.
3. `update_display` selects the best pyramid level for the current `zoom_factor`:
   ```
   level = max(0, floor(log2(1.0 / zoom_factor)))
   ```
4. Render the selected level's tile covering the viewport rather than the whole array.
5. GCP pixel coordinates stay in level-0 (full-res) space; scale by `2^level` before drawing on the selected level.

**Pros**: No format changes, works with existing PNG/TIFF inputs, implemented entirely in `test_image_viewer.py` + `graphics_image_view.py`.

**Cons**: Pyramid lives in RAM; ~1.2 GB × 1.33 overhead ≈ 1.6 GB for a full 6-level pyramid.

---

### Tier 2 — Tile Cache with Lazy Decoding (Medium Term)

Replace the full-array load with a tile cache that decodes only what is visible.

**Key components**:

- **`Tile_Cache`** (`tmns` or `pointy.core`) — LRU cache mapping `(level, tile_x, tile_y)` → `np.ndarray`
- **`Tile_Source`** (abstract base) — `get_tile(level, tx, ty) -> np.ndarray | None`
  - `TIFF_Tile_Source` — reads from GeoTIFF overviews via `rasterio.open(...).read(window=...)`
  - `PNG_Tile_Source` — slices the in-memory array (Tier 1 fallback)
  - `COG_Tile_Source` — range-request enabled for remote files
- **`Graphics_Image_View`** — calls `Tile_Source.get_tile()` per visible tile on `paintEvent`, composites into the scene.

**Memory bound**: cache size is configurable (e.g. 256 tiles × 512² × 3 bytes ≈ 200 MB).

**Viewport tile calculation**:
```python
viewport_rect = self.mapToScene(self.viewport().rect()).boundingRect()
tx_min = int(viewport_rect.left()  / tile_size)
tx_max = int(viewport_rect.right() / tile_size) + 1
ty_min = int(viewport_rect.top()   / tile_size)
ty_max = int(viewport_rect.bottom()/ tile_size) + 1
```

---

### Tier 3 — COG + Remote Streaming (Long Term)

- Convert source imagery to COG on ingest (GDAL `gdal_translate` with `-co TILED=YES -co COMPRESS=LZW -co COPY_SRC_OVERVIEWS=YES`).
- Stream tiles over HTTP using GDAL's `/vsicurl/` virtual filesystem or `rasterio` with `GDAL_HTTP_FETCH_BUFFERSIZE`.
- Enables cloud-hosted collections without full local copies.

---

## Ortho Warp Integration

With a pyramid in place, the ortho warp can be dramatically sped up for non-Affine projectors:

### Sparse Grid + Interpolation (TPS/RPC)
Instead of calling `projector.geographic_to_source()` for every output pixel:

1. Build a coarse grid (e.g. every 64th output pixel) → compute source pixel coords via projector.
2. Interpolate the full dense `map_x` / `map_y` from the sparse grid using `scipy.interpolate.RegularGridInterpolator` or `cv2.resize`.
3. Pass dense maps to `cv2.remap` as normal.

**Speedup estimate**: For a 64× sparse grid, projector calls drop from 400M to ~97k. Interpolation is vectorised and fast.

### Downsampled Warp Preview
For interactive ortho preview (while adjusting GCPs):
1. Warp at pyramid level 3 or 4 (1/8 or 1/16 resolution) — ~1–5 seconds instead of 30+.
2. Trigger full-resolution warp only when the user explicitly commits.

---

## File Format Recommendations

| Use Case | Format | Rationale |
|---|---|---|
| Source imagery (local) | GeoTIFF COG | GDAL-native, rasterio-readable, overviews included |
| Source imagery (remote) | COG over HTTP | Range requests avoid full download |
| Ortho output | GeoTIFF COG | Standard, GIS-compatible |
| Reference tiles (Leaflet) | XYZ/MBTiles | Already consumed by Leaflet tile layer |
| Collection cache | Zarr | Chunked, compression, multi-band |

---

## Implementation Plan

### Phase 1 — In-Memory Pyramid (current sprint blocker: none)
- [ ] Add `_pyramid: dict[int, np.ndarray]` to `Test_Image_Viewer`
- [ ] Build pyramid after async load completes (background thread or post-process step)
- [ ] Modify `update_display` to select level from `zoom_factor`
- [ ] Scale GCP overlay coordinates by selected level
- [ ] Add pyramid level indicator to info label

### Phase 2 — Tile Cache + Viewport Culling
- [ ] Design `Tile_Source` ABC in `tmns.io` or `pointy.core`
- [ ] Implement `PNG_Tile_Source` (slices in-memory array)
- [ ] Implement `TIFF_Tile_Source` (rasterio window reads)
- [ ] Replace `Graphics_Image_View` pixmap with tile-composited `paintEvent`
- [ ] LRU `Tile_Cache` with configurable max tiles

### Phase 3 — Sparse Warp Acceleration
- [x] Add `geographic_to_source_batch(lons, lats)` vectorised method to `Projector` base (implemented in RPC)
- [x] Implement sparse grid + interpolation warp path for TPS/RPC via `compute_remap_coordinates` (TPS uses LinearNDInterpolator, RPC uses batch inverse)
- [ ] Add downsampled "preview" warp mode triggered during interactive GCP editing
- [ ] Full-res warp on explicit commit

### Phase 4 — COG + Remote Streaming
- [ ] Ingest pipeline: `gdal_translate` to COG on collection load (optional, user-triggered)
- [ ] `COG_Tile_Source` using rasterio `/vsicurl/`
- [ ] Progress indicator during remote tile fetch

---

## Open Questions

1. **Tile size**: 256×256 (Leaflet-compatible) vs 512×512 (fewer tiles for large images) — likely configurable.
2. **Pyramid build timing**: Eagerly on load vs lazily on first zoom-out — eager is simpler, lazy saves startup time.
3. **GeoTIFF-first vs PNG fallback**: Should we mandate COG conversion on ingest, or keep PNG as the primary source indefinitely?
4. **Thread safety**: Tile cache must be thread-safe if background prefetch threads are used.
5. **Ortho output format**: Write COG immediately, or keep in-memory array until explicit save?
