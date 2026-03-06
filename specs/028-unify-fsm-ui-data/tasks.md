# Task Tracking: Unify FSM and UI Data Architecture

**Feature Branch**: `028-unify-fsm-ui-data`
**Status**: In Progress

## Tasks

### 1. Refactor `coordinator.py` Plan Table Builder
- [ ] Modify `_build_diagnostic_plan_table` to remove the redundant `price = rate.get(...)` fallback logic for rows 0+.
- [ ] Read `price` and `export_price` directly from `future_plan[idx]["import_price"]` and `future_plan[idx]["export_price"]`.
- [ ] Read `acq_cost` directly from `future_plan[idx]["acquisition_cost"]`.
- [ ] Reimplement `interval_cost` to strictly multiply `net_grid_kw * duration_hours * price` (or export price), entirely relying on the solver's `net_grid`.
- [ ] For the fallback block (no future plan), retain the existing rate lookups.
- [ ] Remove `current_price` and `current_export_price` arguments from `_build_diagnostic_plan_table` and its caller in `async_update_data`, as they are now redundant.
- [ ] Keep all string formatting (e.g., `"${interval_cost:.4f}"`) identical so the frontend JS doesn't break.

### 2. Verification and Testing
- [ ] Run `pytest tests/test_coordinator.py` to ensure the table builder dict generation still passes. Fix any mocked data structures in the tests that didn't include the new solver dictionary keys.
- [ ] Run total test suite recursively `pytest tests/`.
- [ ] Commit changes to the `028-unify-fsm-ui-data` branch.

## Notes
The user explicitly noted: "this is a branch, it will be tested before use on main". We will push the branch to GitHub but will not merge or release it automatically.
