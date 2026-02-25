# Implementation Plan: Remove Artificial 4kW Load Prediction Limit

## Goal Description
The House Battery Control integration currently enforces a hardcoded 4.0kW ceiling on its load forecast in `load.py`. This prevents accurate planning for heavy-load households (like those with EVs or resistive heating). We are unconditionally removing this arbitrary limitation from the predictive engine, allowing natural historical loads to flow through to the optimizer.

## Proposed Changes

### Core Prediction Logic

#### [MODIFY] load.py
- **Method**: `LoadPredictor.async_predict(...)`
- **Changes**:
  - Remove the default parameter `max_load_kw: float = 4.0` from the method signature.
  - Remove the upper-bound clamping logic: `kw_final = round(max(0.0, min(derived_kw, max_load_kw)), 2)`
  - Replace with: `kw_final = round(max(0.0, derived_kw), 2)` to retain the safe 0.0kW floor.

### Test Suite Adaptations

#### [MODIFY] tests/test_load.py
- **Changes**:
  - Add a dedicated test `test_unclamped_high_load` that injects a mocked history of `7.5kW` usage.
  - Assert that `LoadPredictor.async_predict()` correctly returns predicting intervals of ~`7.5` rather than being clamped down to `4.0`.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_load.py` to ensure the new `test_unclamped_high_load` test passes and native prediction math is maintained accurately.
- Run the full test suite `pytest tests/` to ensure the FSM solver handles higher load capacities seamlessly (as the LP matrices are inherently scale-invariant, this should pass perfectly).

### Manual Verification
- Review the Home Assistant "Plan" panel output for periods simulating EV charging or high baseline usage to visually confirm unrestricted forecasting.
