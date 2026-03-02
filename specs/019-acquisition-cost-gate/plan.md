# Implementation Plan: Acquisition Cost Gate Fix

**Feature**: 019-acquisition-cost-gate  
**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/019-acquisition-cost-gate/spec.md)  
**GitHub Issue**: #15

## Technical Context

- **Scope**: LP solver logic change + persistence verification
- **Risk**: Medium — changes solver decision-making; must not regress existing optimisation
- **Architecture constraint**: LP bounds are set before solving. Per-step acquisition cost is only known after solving. Requires a two-pass approach.

## Proposed Changes

### Component 1: Post-Solve Row-by-Row Gate (FR-001, FR-002, FR-005)

#### [MODIFY] [lin_fsm.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py)

**Current behaviour** (L172-181): A single static `raw_acquisition_cost` is compared against `price_sell[i]` for all 288 steps BEFORE solving. If export price < acquisition cost, the discharge-to-grid bound is locked to `(0.0, 0.0)`.

**New behaviour — post-solve row-by-row gate**:

1. **Remove the pre-solve static gate** at L172-181 entirely. Let the solver run with all discharge bounds open.

2. **In the post-solve sequence builder** (L244-289), the `running_cost` is already computed row by row. After computing `running_cost` for row `i`, add a gate check:

```python
# Gate: override discharge-to-grid if export price is below projected acquisition cost
if step_dg > 0.005 and price_sell[i] < running_cost:
    step_dg = 0.0
    state = "SELF_CONSUMPTION"  # override, don't export at a loss
```

3. The sequence builder already determines `state` at L267-272. The gate check overrides `DISCHARGE_GRID` → `SELF_CONSUMPTION` when unprofitable.

**Why this works**: Row 1 uses the persisted/default acquisition cost. After row 1 is processed (including any charging), `running_cost` is updated. Row 2 uses row 1's updated value. Repeat ×288. Each row's gate uses the actual projected acquisition cost at that point in the simulation.

**No pre-computation. No two-pass. Single solve. Single loop.**

---

### Component 2: Persistence Verification (FR-003, FR-004)

#### [MODIFY] [coordinator.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/coordinator.py)

**Current behaviour** (L85, L131): `self.acquisition_cost` defaults to 0.10 and loads from `.storage`. The loading path at L131 (`data.get("acquisition_cost", 0.10)`) is correct in structure.

**Verification needed**: Add a DEBUG log at L131 to confirm the value loaded vs the default. This is a verification step, not a code change — confirm the persistence path works in practice. If the value is being reset by integration reloads, document and fix.

---

### Component 3: Tests

#### [MODIFY] [test_fsm_lin.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_fsm_lin.py)

- **Test: export below projected acquisition cost is blocked** — Scenario where charging occurs early (cheap), building up acquisition cost, then export price is below that projected cost at a later step. Verify DISCHARGE_GRID does NOT appear at that step.
- **Test: export above projected acquisition cost is allowed** — Same setup but export price exceeds projected cost. Verify DISCHARGE_GRID IS allowed.
- **Test: gate adapts to mid-simulation cost changes** — Acquisition cost drops during simulation due to very cheap charging. Verify later steps become ungated.

## Verification Plan

### Automated Tests
- `pytest tests/ -q` — all existing + new tests pass
- Specific: `test_fsm_lin.py` for the three new gate scenarios

### Manual Verification
- Deploy beta release, examine plan table: no DISCHARGE_GRID rows where Export Rate < Acq. Cost
