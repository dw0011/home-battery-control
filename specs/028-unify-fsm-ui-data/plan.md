# Implementation Plan: Unify FSM and UI Data Architecture

**Feature Branch**: `028-unify-fsm-ui-data`
**Status**: Draft

## Goal Description
The objective is to fix the underlying architectural flaw causing UI values (prices, net grid) in the Plan Table to desync from the Math Brain (`lin_fsm.py`). Currently, `coordinator.py` independently recalculates grid flows and recombines prices from the raw `RatesManager` arrays, leaving it blind to live sensor overrides and constraints used by the solver. 

The fix is to delete this redundant calculation logic in `coordinator.py::_build_diagnostic_plan_table` and instead map `import_price`, `export_price`, and `net_grid` directly from the dictionaries inside `future_plan` (which is the exact `sequence` array exported by `lin_fsm.py`).

## User Review Required
None. This is a purely internal architectural refactoring that ensures display accuracy.

## Proposed Changes

### Coordinator Refactoring

#### [MODIFY] `coordinator.py`
- Modify `_build_diagnostic_plan_table` method.
- Remove the `price` and `export_price` calculation (lines 292-302 approx) that reads from the `rates` dictionary and the live override injection injected in v1.5.4.
- Update the assignment of `price` and `export_price` inside the `if future_plan and 0 <= idx < len(future_plan):` block to simply pull from the solver's array:
  ```python
  price = future_plan[idx].get("import_price", 0.0)
  export_price = future_plan[idx].get("export_price", 0.0)
  ```
- Remove the independent `interval_cost` calculation based on `net_grid_kw * duration_hours * price`. Replace it with the exact `cumulative_cost` and incremental logic derived from the solver, or use the exact grid flows. Wait, the solver already calculates running cumulative cost, but the UI table expects `Interval Cost`. We can compute interval cost strictly using the solver's fields:
  ```python
  # net_grid_kw already comes from future_plan[idx].get("net_grid")
  if net_grid_kw > 0:
      interval_cost = net_grid_kw * duration_hours * price
  else:
      interval_cost = net_grid_kw * duration_hours * export_price
  ```
  Since `net_grid_kw`, `price`, and `export_price` are exactly what the solver used, the math is guaranteed to align with the solver's internal `running_cum_cost`.
- In the `else:` block (fallback physics), keep the raw rate lookup since there is no solver sequence array to read from.
- Update `async_update_data` to stop passing `current_price` and `current_export_price` down to `_build_diagnostic_plan_table` since the builder doesn't need to manually inject them anymore.

### Internal Solver Outputs Verification

#### [MODIFY] `fsm/lin_fsm.py`
Ensure the solver's `sequence` accurately exports the live prices used at step 0. 
Currently, the solver receives `price_buy` and `price_sell` arrays. We must verify that the first element of these arrays includes the live price override. 
(Note: `_build_solver_inputs` in `coordinator.py` already overrides `price_buy[0]` and `price_sell[0]` with the live prices! So `lin_fsm.py`'s `sequence` output naturally contains them.)

## Verification Plan

### Automated Tests
1. Run `pytest tests/test_coordinator.py` to ensure the table builder still processes plans correctly without throwing key errors.
2. Run `pytest tests/` for the complete suite.

### Manual Verification
1. Export a snapshot JSON from the running system.
2. Observe row 0 `Import Rate` and `Export Rate` in the dashboard UI.
3. Validate they match the live Amber sensors perfectly.
