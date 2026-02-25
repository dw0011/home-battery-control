# Tasks: Remove Artificial 4kW Load Prediction Limit

## Phase 1: Setup
*(No broad setup tasks required for this bugfix)*

## Phase 2: Foundational
*(No foundation required)*

## Phase 3: High-Draw User Story [US1]
**Goal**: Ensure historical load above 4kW scales naturally into the optimizer without arbitrary bounds.

- [x] T001 [US1] Remove the `max_load_kw: float = 4.0` parameter constraint from `LoadPredictor.async_predict(...)` signature in `c:\Users\markn\OneDrive - IXL Signalling\0-01 AI Programming\AI Coding\House Battery Control\custom_components\house_battery_control\load.py`
- [x] T002 [US1] Remove the `min(..., max_load_kw)` bounding clamping logic in `load.py` while explicitly preserving the `max(0.0, derived_kw)` zero-floor.
- [x] T003 [P] [US1] Modify `test_load.py` located at `c:\Users\markn\OneDrive - IXL Signalling\0-01 AI Programming\AI Coding\House Battery Control\tests\test_load.py` to add `test_unclamped_high_load` verifying a 7.5kW+ native load.

## Phase 4: Polish & Verification
- [x] T004 Run `pytest tests/test_load.py -v` to confirm unit level prediction bridging.
- [x] T005 Run the full suite `pytest tests/ -v` to verify the unconstrained mathematical LP flow doesn't cause downstream matrix dimension regressions.

## Dependencies
- T001 and T002 must be completed consecutively as they involve adjacent code modifications in the same `load.py` method.
- T003 is parallelizable `[P]` because it isolates behavior inside a unit test before verification.
- T004 and T005 require completing T001-T003.
