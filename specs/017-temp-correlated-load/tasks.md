# Tasks: 017 — Temperature-Correlated Load Prediction (Post-Quizme)

**Branch**: `017-temp-correlated-load` | **Issue**: #13

> [!IMPORTANT]
> TDD discipline: write tests BEFORE verifying code. No new config needed — uses existing `weather_entity`.

## Tasks (dependency order)

### Phase 1 — Historical Analyzer Tests + Code

- [x] **T001** — Implement `extract_temp_data()` in `historical_analyzer.py`
  - Reads `attributes.temperature` from weather entity history
  - Falls back to numeric `state` for sensor entities

- [x] **T002** — Extend `build_historical_profile()` with `temp_data` param
  - Returns `{"load_kw": X, "avg_temp": Y}` per slot

- [ ] **T003** — Write tests for `extract_temp_data()` in `test_historical_analyzer.py`
  - Weather entity with attributes.temperature
  - Numeric sensor fallback
  - Unavailable/unknown states skipped
  - **TEST FIRST**

- [ ] **T004** — Write tests for `build_historical_profile()` with temp_data
  - With temp_data: returns dual format
  - Without temp_data: avg_temp = None

### Phase 2 — Load Predictor Tests + Code

- [x] **T005** — Implement delta-based adjustment in `load.py`
  - Bidirectional delta (FR-004/005/009)
  - Fallback to absolute threshold (FR-008)

- [ ] **T006** — Write tests for delta-based temp adjustment in `test_load.py`
  - Hot day delta: history 20°C, forecast 35°C → load += 15 × sensitivity
  - Zero delta: history 30°C, forecast 30°C → no adjustment
  - Negative delta (FR-009): history 35°C, forecast 28°C → load reduced
  - Within band: forecast 22°C → no adjustment
  - Cold snap: history 18°C, forecast 8°C → load += 10 × sensitivity
  - Fallback: no temp data → absolute threshold

### Phase 3 — Wiring + Regression

- [x] **T007** — Update `coordinator.py` to pass `weather_entity_id`

- [ ] **T008** — Update existing tests for new profile format
  - Tests mocking `build_historical_profile` need `{"load_kw": X, "avg_temp": Y}`

- [ ] **T009** — Full regression + ruff
  - `pytest tests/ -v` — all pass
  - `ruff check` — clean
