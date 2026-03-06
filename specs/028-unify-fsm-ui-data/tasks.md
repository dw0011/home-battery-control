# Task Tracking: Unify FSM and UI Data Architecture

**Feature Branch**: `028-unify-fsm-ui-data`
**Status**: DONE ✅

## Tasks

### 1. Refactor `coordinator.py` Plan Table Builder - DONE
- [x] Modify `_build_diagnostic_plan_table` to remove the redundant `price = rate.get(...)` fallback logic for rows 0+.
- [x] Read `price` and `export_price` directly from `future_plan[idx]["import_price"]` and `future_plan[idx]["export_price"]`.
- [x] Read `acq_cost` directly from `future_plan[idx]["acquisition_cost"]`.
- [x] Reimplement `interval_cost` to strictly multiply `net_grid_kw * duration_hours * price` (or export price), entirely relying on the solver's `net_grid`.
- [x] For the fallback block (no future plan), retain the existing rate lookups.
- [x] Remove `current_price` and `current_export_price` arguments from `_build_diagnostic_plan_table` and its caller in `async_update_data`, as they are now redundant.

### 2. Verification and Testing - DONE
- [x] Run `pytest tests/test_coordinator.py` to ensure the table builder dict generation still passes. Fix any mocked data structures in the tests that didn't include the new solver dictionary keys.
- [x] Run total test suite recursively `pytest tests/`.
- [x] Commit changes to the `028-unify-fsm-ui-data` branch.

## Notes
Code is fully committed and pushed to the `028-unify-fsm-ui-data` branch on GitHub for review and testing prior to merging to `main`.
