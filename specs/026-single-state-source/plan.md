# Implementation Plan: Single State Source (026)

**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/026-single-state-source/spec.md)
**Branch**: `026-single-state-source`
**Issue**: #26

## Technical Context

The bug is in `lin_fsm.py` function `calculate_next_state` (L316-424). Two independent paths classify the state:

### Path 1 — Sequence Builder (L259-269) ← SOURCE OF TRUTH
```python
if step_dg > 0.005:        → DISCHARGE_GRID
elif step_c > 0.005 and step_g > 0.005: → CHARGE_GRID
else:                       → SELF_CONSUMPTION
```
Then the acquisition cost gate (L267-277) may override DISCHARGE_GRID → SELF_CONSUMPTION.

### Path 2 — Independent Classification (L378-423) ← TO ELIMINATE
```python
target_delta_kwh = (target_soc_frac - current_soc) * capacity
power_kw = target_delta_kwh * 12.0
if power_kw > 0.1:    → CHARGE_GRID
elif power_kw < -0.1: → check dg_kw vs dh_kw → DISCHARGE_GRID or SELF_CONSUMPTION
else:                  → SELF_CONSUMPTION
```

Path 2 uses different variables (net SoC delta vs raw LP components) and different thresholds (0.1 kW vs 0.005 kWh), causing disagreement at boundary conditions.

## Proposed Changes

### lin_fsm.py — `calculate_next_state` (L378-423)

**Before** (4 branches, independent classification):
```python
if power_kw > 0.1:
    return FSMResult(state="CHARGE_GRID", ...)
elif power_kw < -0.1:
    if dg_kw > dh_kw:
        return FSMResult(state="DISCHARGE_GRID", ...)
    else:
        return FSMResult(state="SELF_CONSUMPTION", ...)
return FSMResult(state="SELF_CONSUMPTION", ...)
```

**After** (read from sequence, single source):
```python
# FR-001: State from sequence[0], not independent classification
if sequence:
    state_0 = sequence[0]["state"]
else:
    state_0 = "SELF_CONSUMPTION"  # FR-003: safe default

# limit_kw calculation unchanged (FR-002)
if power_kw > 0.1:
    req = power_kw / battery.charging_efficiency
    limit_kw = round(min(limit_kw_charge, req), 2)
elif power_kw < -0.1:
    req = abs(power_kw) * battery.discharging_efficiency
    limit_kw = round(min(limit_kw_discharge, req), 2)
else:
    limit_kw = 0.0

# If state is SC but we computed a limit, force limit to 0
if state_0 == "SELF_CONSUMPTION":
    limit_kw = 0.0

return FSMResult(
    state=state_0,
    limit_kw=limit_kw,
    reason=f"LP Optimized {state_0.replace('_', ' ').title()}",
    target_soc=target_soc_frac * 100.0,
    projected_cost=projected_cost,
    future_plan=sequence,
)
```

### Key Design Decision: limit_kw When State Disagrees

When Path 1 says SELF_CONSUMPTION but Path 2 computed a non-zero limit_kw, we force limit_kw=0.0 to match the state. The state is authoritative — if the sequence says SC, we don't send a power command.

### Tests — `test_fsm_lin.py`

New test: `test_fsm_result_state_matches_plan_row_0`
- Construct inputs where the two paths would disagree (boundary SoC delta near 0.1 threshold)
- Verify `fsm_result.state == fsm_result.future_plan[0]["state"]`
- Cover all 3 states: CHARGE_GRID, DISCHARGE_GRID, SELF_CONSUMPTION

Existing solver replay test: `test_solver_replay.py`
- Add assertion: `assert result.state == result.future_plan[0]["state"]` to every existing replay test

## Redundant Code Removal

### lin_fsm.py — `propose_state_of_charge` return signature (L301)
**Before**: Returns 5 values: `b_1/capacity, objective_value, dh_0, dg_0, sequence`
**After**: Returns 3 values: `b_1/capacity, objective_value, sequence`

`dh_0` and `dg_0` were only consumed by the old Path 2 classification to decide `dg_kw > dh_kw`. With state coming from `sequence[0]`, these are dead variables.

### lin_fsm.py — `calculate_next_state` unpacking (L357)
**Before**: `target_soc_frac, projected_cost, raw_dh, raw_dg, sequence = ...`
**After**: `target_soc_frac, projected_cost, sequence = ...`

### lin_fsm.py — Independent classification block (L378-423)
**Removed entirely** — the 4-branch if/elif/elif/else that independently classified state from SoC delta. Replaced by reading `sequence[0]["state"]`.

Variables removed:
- `dg_kw = raw_dg / (5.0 / 60.0)` (L394)
- `dh_kw = raw_dh / (5.0 / 60.0)` (L395)
- `dg_kw > dh_kw` branch (L397)

### lin_fsm.py — `propose_state_of_charge` internal variables
- `dh_0` extraction (from LP result) — REMOVE
- `dg_0` extraction (from LP result) — REMOVE
- `dg_0` gate override at L298-299 — REMOVE (gate already applied in sequence builder at L267-277)

### Tests — redundant test cleanup
Scan for any test that specifically asserts `raw_dg`, `raw_dh`, `dg_0`, `dh_0` values from the solver return. These become dead tests.

## Files Changed

| File | Change |
|------|--------|
| `fsm/lin_fsm.py` | Remove `dh_0`/`dg_0` from return signature and extraction; remove L378-423 independent classification; read state from `sequence[0]` |
| `tests/test_fsm_lin.py` | Add `test_fsm_result_state_matches_plan_row_0`; remove any tests asserting `raw_dg`/`raw_dh` |
| `tests/test_solver_replay.py` | Add state agreement assertion to existing replay tests |

## Verification Plan

1. `pytest tests/ -q --tb=short` — all 205+ tests pass
2. New test explicitly covers boundary conditions where paths would have disagreed
3. Replay tests assert state agreement on frozen production data
