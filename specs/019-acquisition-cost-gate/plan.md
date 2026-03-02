# Implementation Plan: Acquisition Cost Gate Fix

**Feature**: 019-acquisition-cost-gate  
**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/019-acquisition-cost-gate/spec.md)  
**GitHub Issue**: #15  
**Archive**: `archive/pre-019-acq-gate` tag on main (rollback point)

## Technical Context

- **Scope**: Single file — `lin_fsm.py`. Three change sites.
- **Risk**: Medium — changes solver decision-making
- **Rollback**: Tag `archive/pre-019-acq-gate` preserves current main
- **Release**: Branch beta release only (not merged to main until validated)

## Proposed Changes

All changes in a single file:

#### [MODIFY] [lin_fsm.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py)

### Change 1: Remove Pre-Solve Static Gate (FR-006)

**Location**: L172-181 — discharge-to-grid bounds loop

Remove the `if price_sell[i] < raw_acquisition_cost` branch. All discharge-to-grid bounds become open (unconstrained by acquisition cost). The solver runs with full discharge freedom.

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

---

### Change 2: Row-by-Row Gate in Sequence Builder (FR-001, FR-002, FR-003, FR-005, FR-008)

**Location**: L244-289 — post-solve sequence builder loop

After the acquisition cost update (L252-259) and state classification (L267-272), add a gate check. When overriding:
- Zero `step_dg` only (FR-008: `dh` is untouched)
- Add retained energy back to `running_capacity` (FR-002: battery state propagation)
- `running_cost` is unchanged (FR-003: no sale occurred)
- Recalculate `net_grid_kwh` without the export (FR-005: consistent plan display)

```python
# Insert after state classification (L272), before cumulative cost (L274):

# --- Acquisition cost gate — FR-001: row-by-row check ---
if state == "DISCHARGE_GRID" and price_sell[i] < running_cost:
    # FR-002: Battery retains energy — adjust state for subsequent steps
    running_capacity = running_capacity + step_dg
    step_dg = 0.0
    state = "SELF_CONSUMPTION"
    # FR-005: Recalculate net grid without export
    net_grid_kwh = load_forecast[i] - pv_forecast[i] + step_c - step_dh - step_dg
    net_grid_kw = net_grid_kwh * (60.0 / 5.0)
```

Note: `running_cost` carries forward unchanged per FR-003 — no additional code needed.

---

### Change 3: Immediate Action Uses Gated Step 0 Values (FR-007, FR-009)

**Location**: L232-236 + L440-462 — first-step extraction and immediate action classifier

Currently `raw_dg` and `raw_dh` are extracted at L235-236 before the sequence builder runs. The immediate action classifier at L445 uses `dg_kw > dh_kw` to choose DISCHARGE_GRID.

**New approach**: After the sequence builder loop completes, extract the gated step 0 values from `sequence[0]`. If the gate overrode step 0's discharge, `dg_0` should be zero.

```python
# After sequence builder loop (L290), update raw_dg from gated sequence:
if sequence and sequence[0]["state"] != "DISCHARGE_GRID":
    dg_0 = 0.0  # Gate overrode step 0 — suppress grid discharge command
```

This ensures the immediate action classifier at L445 sees `dg_kw = 0` and falls through to SELF_CONSUMPTION (FR-007, FR-009).

---

### Change 4: Code Optimisation (line count reduction)

**Current state**: 472 lines. Target: eliminate redundancy while maintaining readability.

**4a. Merge bounds loops** (L146-193): Four separate `for i in range(number_step)` loops build `obj` and `bounds` for g, c, dh, dg variables. These can merge into a single loop — saves ~12 lines and improves locality.

**4b. Remove `raw_acquisition_cost` parameter** (L116): No longer needed after removing the pre-solve gate (Change 1). The gate now uses `running_cost` in the sequence builder, which starts from `acquisition_cost` (the terminal valuation). Remove from both `propose_state_of_charge()` signature and call site at L412.

**4c. Simplify forecast extraction** (L312-353 in `calculate_next_state`): The price extraction loop (L315-335) has duplicate fallback patterns. The load/solar loop (L339-349) can be tightened. Extract a small helper or use list comprehension to reduce repeated `isinstance/dict/get` patterns — saves ~8-10 lines.

**4d. Remove stale comments**: Comments referencing the old FR-002 static gate (L174) and any outdated section references.

**Estimated reduction**: ~25-30 lines net (removals + merge savings minus new gate code).

---

### Tests

#### [MODIFY] [test_fsm_lin.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_fsm_lin.py)

Three new tests:

1. **test_acq_gate_blocks_unprofitable_discharge**: Set up scenario where solver wants to discharge at an export price below acquisition cost. Verify step returns SELF_CONSUMPTION, not DISCHARGE_GRID.
2. **test_acq_gate_allows_profitable_discharge**: Export price above acquisition cost. Verify DISCHARGE_GRID is allowed.
3. **test_acq_gate_propagates_soc**: After gate override, subsequent steps show higher SoC than without the gate. Verify `running_capacity` propagation.

## Verification Plan

### Automated Tests
- `pytest tests/ -q` — all existing + 3 new tests pass

### Manual Verification
- Deploy as branch beta release
- Examine plan table: no DISCHARGE_GRID rows where Export Rate < Acq. Cost
- Compare plan output before/after to confirm reasonable behaviour
- Rollback to `archive/pre-019-acq-gate` if issues found
