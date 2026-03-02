# Implementation Plan: Acquisition Cost Gate Fix

**Feature**: 019-acquisition-cost-gate  
**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/019-acquisition-cost-gate/spec.md)  
**GitHub Issue**: #15  
**Archive**: `archive/pre-019-acq-gate` tag on main (rollback point)

## Technical Context

- **Scope**: Single file change — `lin_fsm.py`
- **Risk**: Medium — changes solver decision-making in the sequence builder
- **Rollback**: Tag `archive/pre-019-acq-gate` preserves current main
- **Release**: Branch test release only (not merged to main until validated)

## Proposed Changes

### Component 1: Sequence Builder Gate (FR-001, FR-002, FR-003, FR-005, FR-006)

#### [MODIFY] [lin_fsm.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py)

**Change 1 — Remove pre-solve static gate** (L172-181, FR-006):

Remove the static `raw_acquisition_cost` gate from the bounds loop. Let the solver run with all discharge-to-grid bounds open.

```diff
         for i in range(number_step):
-            # Discharge to grid: opportunity cost = max(ε, sell_price)
-            # FR-002: Lock grid discharge to zero when export is below raw acquisition cost
             obj[dg_off + i] = max(0.001, price_sell[i])
-            if price_sell[i] < raw_acquisition_cost:
-                bounds.append((0.0, 0.0))  # Export unprofitable — gate closed
-            else:
-                max_home = max(0.0, energy[i])
-                max_grid = max(0.0, dis_limit - max_home)
-                bounds.append((-max_grid, 0.0))
+            max_home = max(0.0, energy[i])
+            max_grid = max(0.0, dis_limit - max_home)
+            bounds.append((-max_grid, 0.0))
```

**Change 2 — Row-by-row gate in sequence builder** (L244-289, FR-001/002/003):

In the post-solve sequence builder loop, AFTER computing `running_cost` for the row, add a gate check. When a discharge is overridden, propagate the battery state correction:

```python
# After state classification (L267-272) and running_cost update (L252-259):

# Gate: override discharge-to-grid if export price is below acquisition cost
if state == "DISCHARGE_GRID" and price_sell[i] < running_cost:
    # Energy stays in battery — recalculate battery state
    retained_kwh = step_dg  # energy that would have been exported
    step_dg = 0.0
    running_capacity = running_capacity + retained_kwh
    state = "SELF_CONSUMPTION"
    # Recalculate net grid (no longer exporting)
    net_grid_kwh = load_forecast[i] - pv_forecast[i] + step_c - step_dh - step_dg
    net_grid_kw = net_grid_kwh * (60.0 / 5.0)
```

The key: `running_capacity` carries forward to step `i+1`, so subsequent rows see the corrected SoC. `running_cost` already carries forward unchanged (no sale occurred).

---

### Component 2: Tests

#### [MODIFY] [test_fsm_lin.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_fsm_lin.py)

Three new tests:

1. **test_acq_gate_blocks_unprofitable_discharge**: Export price below acquisition cost → no DISCHARGE_GRID in plan sequence at that step.
2. **test_acq_gate_allows_profitable_discharge**: Export price above acquisition cost → DISCHARGE_GRID allowed.
3. **test_acq_gate_propagates_battery_state**: After override, subsequent steps show higher SoC than they would without the gate.

## Verification Plan

### Automated Tests
- `pytest tests/ -q` — all existing + new tests pass

### Manual Verification
- Deploy as branch beta release (v1.4.0-beta.1)
- Examine plan table: no DISCHARGE_GRID rows where Export Rate < Acq. Cost
- Compare plan output before/after to confirm reasonable behaviour
