# GUI Testing Strategy — Pointy McPointface

## Goals

Catch regressions without requiring a human to click through the app.  The
strategy is layered: fast headless unit tests cover the bulk of logic; a
smaller set of integration tests exercise the wired-up GUI under a virtual
framebuffer; smoke tests catch import/startup breakage in CI.

---

## Layer 1 — Pure Logic (no Qt at all)

These run instantly, no display required.

### What to cover

| Area | What to test |
|---|---|
| `Auto_Match_Settings` | `to_log_string()`, default values, nested dataclass equality |
| `Feature_Extractor` | `normalize_to_uint8` with uint8 / uint16 / float32 inputs; `downscale`; `to_gray` |
| `Auto_Matcher.run` | Feed synthetic numpy arrays — assert `Match_Result` fields are populated |
| `Imagery_Loader` | `needs_seed_location` with a real tiny GeoTIFF fixture vs a non-geo PNG |
| `GCP_Processor` | add / remove / serialise GCPs |
| `Collection_Manager` | seed location, first image, round-trip TOML |
| Coordinate types | `Geographic.create`, round-trips through `recreate_map_with_center` signature |

### Location

`test/unit/` — no `qapp` fixture needed.

### Running

```bash
pytest test/unit/ -m "not gui"
```

---

## Layer 2 — Headless Qt Widget Tests

Uses `QT_QPA_PLATFORM=offscreen` (already set in `conftest.py`).  Widgets are
instantiated and signals are exercised without a real display.

### What to cover

#### Panel / settings round-trip
The most valuable regression test in the whole suite.  Verifies that every
spinbox / combobox value survives a `get_settings()` → `Auto_Match_Settings`
round-trip.

```python
# test/unit/gui/test_auto_match_panel.py
def test_get_settings_round_trip(qapp):
    panel = Auto_Match_Panel()
    s = panel.get_settings()
    assert s.algo == Match_Algo.AKAZE
    assert s.test_extraction.pyramid_level == panel.pyramid_combo.currentData()
    assert s.matching.ratio_test == panel.ratio_spin.value()
    assert s.outlier.inlier_threshold == panel.threshold_spin.value()
```

#### Signal emission
Verify `run_requested` fires when the Run button is clicked and carries a
valid `Auto_Match_Settings`.

```python
def test_run_requested_emits_settings(qapp, qtbot):
    panel = Auto_Match_Panel()
    received = []
    panel.run_requested.connect(received.append)
    qtbot.mouseClick(panel.run_btn, Qt.LeftButton)
    assert len(received) == 1
    assert isinstance(received[0], Auto_Match_Settings)
```

#### Results panel update
`update_results()` should not raise and should populate the table.

```python
def test_update_results_populates_table(qapp):
    panel = Auto_Match_Panel()
    panel.update_results(
        candidates=42, inliers=12, coverage=None, rmse=None,
        candidate_rows=[(100.0, 200.0, -119.1, 35.4)]
    )
    assert panel._results_panel._table.rowCount() == 1
```

#### `_on_algo_changed` visibility
Switching the algo combo should toggle group-box visibility.

```python
def test_algo_combo_toggles_groups(qapp):
    panel = Auto_Match_Panel()
    panel.algo_combo.setCurrentIndex(
        panel.algo_combo.findData(Match_Algo.ORB)
    )
    assert not panel._akaze_group.isVisible()
    assert panel._orb_group.isVisible()
```

### Location

`test/unit/gui/test_auto_match_panel.py` (start here), then
`test_gcp_loading.py` (already exists).

### Running

```bash
pytest test/unit/gui/ -m gui
```

---

## Layer 3 — Controller Integration Tests

Wire a controller to mock viewers/sidebar and drive it via signals.  No real
image file required — use small synthetic numpy arrays.

### What to cover

#### `Auto_Match_Controller`

- `on_run_requested` disables the run button while the worker runs.
- Worker `finished` signal re-enables the button and calls
  `panel.update_results`.
- Worker `error` signal shows a status message and re-enables the button.
- Passing `None` as the test image (no image loaded) does not crash — shows an
  appropriate status message.

#### `Image_Controller`

- `on_image_loaded` with a pending seed calls
  `ref.recreate_map_with_center(Geographic)`.
- `on_image_loaded` without a pending seed updates the status bar only.

#### `Sync_Controller`

- `on_gcp_navigate` calls `ref.recreate_map_with_center(gcp.geographic, zoom=17)`.

### Recommended pattern — mock viewers

```python
from unittest.mock import MagicMock, patch
import numpy as np

@pytest.fixture
def mock_ref():
    ref = MagicMock()
    ref.grab_ref_chip.side_effect = lambda cb: cb(
        np.zeros((256, 256, 3), dtype=np.uint8),
        lambda px, py: (-119.0 + px / 256, 35.0 + py / 256),
    )
    return ref

@pytest.fixture
def mock_test():
    test = MagicMock()
    test.get_image_array.return_value = np.zeros((512, 512, 3), dtype=np.uint8)
    return test
```

### Location

`test/integration/test_auto_match_controller.py`

### Running

```bash
pytest test/integration/ -m integration
```

---

## Layer 4 — Smoke / Import Tests

Catch the class of error we just fixed (`ModuleNotFoundError` on startup).

```python
# test/unit/test_imports.py
def test_core_imports():
    from pointy.core import Collection_Manager, GCP_Processor, Imagery_Loader

def test_controllers_importable():
    from pointy.controllers.auto_match_controller import Auto_Match_Controller
    from pointy.controllers.image_controller import Image_Controller
    from pointy.controllers.sync_controller import Sync_Controller

def test_viewers_importable():
    from pointy.viewers.leaflet_reference_viewer import Leaflet_Reference_Viewer
    from pointy.viewers.test_image_viewer import Test_Image_Viewer
```

These have zero dependencies (no `qapp`, no fixtures) and run in < 1 s.

> **Note:** Once unit test coverage is solid, these become redundant — any
> import error will surface in the unit suite anyway.  The smoke layer is most
> valuable while the suite is still sparse and modules aren't exercised by any
> other test.

### Location

`test/smoke/test_imports.py`

---

## Infrastructure

### Dependencies

Add to `pyproject.toml` / `requirements.txt` if not already present:

```
pytest
pytest-qt
pytest-mock
```

`pytest-qt` provides the `qtbot` fixture and handles `QApplication` lifecycle.
`pytest-mock` provides the `mocker` fixture (cleaner than `unittest.mock`
patches in many cases).

### `pytest.ini` / `pyproject.toml` markers

```toml
[tool.pytest.ini_options]
markers = [
    "gui: requires offscreen Qt",
    "integration: wired-up component tests",
    "slow: may take > 5 s",
    "network: requires internet",
]
```

### CI invocation (suggested)

```bash
# Smoke only — runs on every push, < 5 s
pytest test/smoke/ --tb=short -q

# Fast gate — unit + smoke
pytest test/unit/ test/smoke/ -m "not slow" --tb=short -q

# Full suite — nightly or pre-merge
pytest test/ --tb=short -q
```

---

## Priority Order

Build tests in this order to get maximum regression coverage fastest:

1. **`test/smoke/test_imports.py`** — catches dead-import regressions immediately (30 min)
2. **`test/unit/gui/test_auto_match_panel.py`** — settings round-trip + signal (1 hr)
3. **`test/unit/` logic tests** — `Feature_Extractor`, `Auto_Match_Settings` (2 hrs)
4. **`test/integration/test_auto_match_controller.py`** — mock-based pipeline (2 hrs)
5. **`test/integration/test_image_controller.py`** — seed / center flow (1 hr)

---

## What NOT to test here

- Leaflet JavaScript rendering — not testable in Python; use a browser automation
  tool (Playwright) only if map correctness becomes a recurring issue.
- Pixel-perfect screenshot comparisons — fragile across platforms; prefer
  behavioural assertions (row counts, signal payloads, method call args).
- Network tile loading — mock at the `QWebEngineView` boundary or skip with
  `@pytest.mark.network`.
