# Tasks: Acquisition Cost Gate Fix (Feature 019)

**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/019-acquisition-cost-gate/spec.md)  
**Plan**: [plan.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/019-acquisition-cost-gate/plan.md)

## Phase 1: Tests First (TDD)

### T001: Write test_acq_gate_blocks_unprofitable_discharge
- [ ] In `test_fsm_lin.py`, create test where solver wants DISCHARGE_GRID but export price < acquisition cost
- [ ] Assert result state is SELF_CONSUMPTION, not DISCHARGE_GRID
- [ ] Covers: FR-001, FR-007, FR-009
- **Expect**: FAIL (gate not implemented yet)

### T002: Write test_acq_gate_allows_profitable_discharge
- [ ] In `test_fsm_lin.py`, create test where export price > acquisition cost
- [ ] Assert DISCHARGE_GRID is allowed
- [ ] Covers: FR-001
- **Expect**: PASS (current behaviour allows discharge)

### T003: Write test_acq_gate_propagates_soc
- [ ] In `test_fsm_lin.py`, create test where gate overrides a discharge
- [ ] Assert subsequent plan rows show higher SoC than without gate
- [ ] Covers: FR-002, FR-003, FR-005
- **Expect**: FAIL (gate not implemented yet)

## Phase 2: Gate Implementation

### T004: Remove pre-solve static gate (Change 1, FR-006)
- [ ] Delete L172-181 `if price_sell[i] < raw_acquisition_cost` branch
- [ ] Replace with unconditional bounds for dg variables
- [ ] Run `pytest tests/ -q` — all existing tests pass (no new tests yet)

### T005: Add row-by-row gate in sequence builder (Change 2, FR-001/002/003/005/008)
- [ ] After state classification (L267-272), add gate check: `if state == "DISCHARGE_GRID" and price_sell[i] < running_cost`
- [ ] Override: zero `step_dg` only (FR-008), retain energy in `running_capacity` (FR-002)
- [ ] Recalculate `net_grid_kwh` and `net_grid_kw` after override
- [ ] `running_cost` carries forward unchanged (FR-003)
- [ ] Run `pytest tests/ -q` — T001, T003 should now pass

### T006: Gate the immediate action classifier (Change 3, FR-007/009)
- [ ] After sequence builder loop, check if step 0 was gated: `if sequence and sequence[0]["state"] != "DISCHARGE_GRID": dg_0 = 0.0`
- [ ] This ensures L445 `dg_kw > dh_kw` falls through to SELF_CONSUMPTION
- [ ] Run `pytest tests/ -q` — all tests including T001 pass

## Phase 3: Optimisation

### T007: Merge bounds loops (Change 4a)
- [ ] Combine 4 separate `for i in range(number_step)` loops (L146-181) into one
- [ ] Run `pytest tests/ -q` — no regressions

### T008: Remove raw_acquisition_cost parameter (Change 4b)
- [ ] Remove from `propose_state_of_charge()` signature
- [ ] Remove from call site at L412
- [ ] Run `pytest tests/ -q` — no regressions

### T009: Simplify forecast extraction (Change 4c)
- [ ] Tighten price extraction loop (L315-335) — reduce duplicate fallback patterns
- [ ] Tighten load/solar loop (L339-349)
- [ ] Run `pytest tests/ -q` — no regressions

### T010: Remove stale comments (Change 4d)
- [ ] Remove old FR-002 static gate references
- [ ] Update section references to reflect new structure
- [ ] Run `pytest tests/ -q` — no regressions

## Phase 4: Verification

### T011: Full regression test
- [ ] `pytest tests/ -q` — all tests pass (existing + 3 new)
- [ ] Verify line count reduction (target: 472 → ~445)
- [ ] Commit and push to branch
- [ ] Create beta release for manual validation
