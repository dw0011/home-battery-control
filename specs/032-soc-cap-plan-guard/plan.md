# Implementation Plan: Feature 032 — SoC-Cap Plan Guard

**Branch**: `032-soc-cap-plan-guard` | **Date**: 2026-03-12 | **Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/032-soc-cap-plan-guard/spec.md)

## Summary

Fix two related defects in the LP FSM solver pipeline:

**Part A — Plan Builder Guard**: The plan builder loop (lines 236–296 of `lin_fsm.py`) displays phantom `CHARGE_GRID` states and impossible positive Net Grid values when SoC is at 100%. Fix by clamping `step_c` to available battery headroom before computing Net Grid and state classification.

**Part B — LP Spill Variable**: The LP solver's objective function is blind to the cost of forced solar exports when the battery is full. Introduce a spill variable `s[i]` costed at `price_sell[i]` so the solver considers downstream export penalties when deciding whether to fill the battery early.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: SciPy (`linprog` HiGHS), NumPy
**Testing**: pytest
**Target Platform**: Home Assistant (amd64/aarch64)
**Performance Goals**: LP solve < 2s for 288 steps
**Constraints**: Single file change (`lin_fsm.py`), no API/UI changes

## Project Structure

```text
custom_components/house_battery_control/fsm/
└── lin_fsm.py          # MODIFY — Both Part A and Part B changes

tests/
└── test_fsm_lin.py     # MODIFY — Add 4 new test classes
```

---

## Part A: Plan Builder Headroom Guard

### Change Surface

[lin_fsm.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py) — plan builder loop (lines 236–276)

### Design

Insert a headroom gate **after** extracting LP variables (line 241) and **before** acquisition cost tracking (line 243). This mirrors the existing acquisition cost gate pattern (line 266–276).

```python
# --- SoC-cap plan guard — FR-001/FR-002 (Feature 032) ---
headroom = capacity - step_b
if headroom <= 0:
    # FR-001: Battery full — clamp charge and grid import to zero
    charge_reduction = step_c
    step_c = 0.0
    step_g = max(0.0, step_g - charge_reduction)
elif step_c > headroom:
    # FR-002: Battery nearly full — clamp to available headroom
    charge_reduction = step_c - headroom
    step_c = headroom
    step_g = max(0.0, step_g - charge_reduction)
```

**Insertion point**: After line 241 (`step_dg = abs(...)`) and before line 243 (`# --- Acquisition cost tracking`).

### Why before acquisition cost tracking?

The acquisition cost math on line 244 uses `step_c` and `step_g`. If we clamp after acquisition cost, the cost tracker would see phantom charge that didn't physically happen. Clamping first ensures acquisition cost only tracks physically achievable energy.

### Net Grid and State Recalculation

No additional code needed — the existing Net Grid calculation (line 255) and state classification (line 258–264) already use the local `step_c` and `step_g` variables. Clamping them before these lines naturally produces correct outputs.

### SoC Correction

When charge is clamped, the energy the LP expected to store is "lost." We must **not** add this to `soc_correction` because the LP already capped `b[i]` at capacity. The plan builder's `step_b` is already correct. Unlike the acquisition cost gate (which retains energy in the battery), the headroom guard simply removes phantom charge — no correction accumulator needed.

---

## Part B: LP Spill Variable

### Change Surface

[lin_fsm.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py) — LP formulation (lines 92–219)

### Design

Add a 5th decision variable `s[i]` (spill) to the LP, representing forced solar export when PV > Load and the battery is full.

#### Variable Layout Change

```
Current:  g[0..N-1], c[0..N-1], dh[0..N-1], dg[0..N-1], b[0..N]
                                                         = 5N + 1 vars

Proposed: g[0..N-1], c[0..N-1], dh[0..N-1], dg[0..N-1], s[0..N-1], b[0..N]
                                                         = 6N + 1 vars
```

#### New variable offset

```python
s_off = 4 * number_step       # spill offset (was b_off)
b_off = 5 * number_step       # battery state offset (shifted)
num_vars = 5 * number_step + (number_step + 1)
```

#### Objective function for spill

```python
# Spill (forced export) — costed at export price
# When price_sell < 0, this creates a positive cost (penalty)
# When price_sell > 0, the LP won't spill (it would prefer to charge)
obj[s_off + i] = price_sell[i]
bounds[s_off + i] = (0.0, None)  # spill >= 0
```

#### Spill constraint

The spill must capture unavoidable solar excess. We need an **inequality** constraint:

```
s[i] >= (pv[i] - load[i]) - c[i] + dh[i] + dg[i]
```

In words: spill must be at least the solar excess minus whatever the battery absorbs (charge) plus whatever the battery is discharging. Rearranged for A_ub form (`Ax <= b`):

```
-s[i] + c[i] - dh[i] - dg[i] <= (pv[i] - load[i])
```

This only activates when `pv > load`. When `pv <= load`, the RHS is negative or zero, and with `s >= 0`, the constraint is slack.

#### Grid balance adjustment

The existing grid balance constraint must also account for spill:

```
g[i] - c[i] - dh[i] - dg[i] - s[i] >= energy[i]
```

Wait — actually the grid balance doesn't need spill. Spill is the solar excess that goes to the grid without going through the battery. It's already implicitly handled. The key is just making the LP **see the cost** of forced export via the objective function.

Actually, let me reconsider. The existing grid balance is:

```
g[i] >= energy[i] + c[i] + dh[i] + dg[i]
```

This says: grid import must cover (load - pv) + charge + discharge adjustments. When energy < 0, the grid import can be 0. The spill is `max(0, -energy[i] - c[i])` — the leftover solar after charging. The LP needs to account for the cost of this leftover.

The simplest correct formulation:

```
s[i] >= -energy[i] - c[i]   →   -s[i] - c[i] <= energy[i]
s[i] >= 0
obj[s_off + i] = price_sell[i]
```

When `energy[i] < 0` (solar surplus) and `c[i]` can't absorb all of it (battery nearly full), `s[i]` captures the remainder and costs it at `price_sell[i]`.

When `energy[i] >= 0` (load deficit), the constraint becomes `s[i] >= negative`, trivially satisfied by `s[i] = 0`.

This is a clean formulation that doesn't touch the existing grid balance constraint at all — it just adds N new rows to `A_ub`.

---

## Test Plan

### Part A Tests (Plan Builder Guard)

#### T001: `test_soc_cap_clamps_charge_at_100pct`
- SoC=100%, import_price=-0.05, PV=4.0kW, Load=2.0kW
- Verify: No `CHARGE_GRID` in plan, Net Grid <= 0 for all 100% SoC steps

#### T002: `test_soc_cap_partial_headroom`
- SoC=99%, capacity=27kWh (headroom=0.27kWh), step_c would be 0.525kWh
- Verify: Charge clamped to headroom, Net Grid reduced accordingly

#### T003: `test_soc_cap_no_regression_normal_charging`
- SoC=50%, normal prices
- Verify: CHARGE_GRID still works, plan unchanged from current behavior

### Part B Tests (LP Spill Variable)

#### T004: `test_spill_variable_penalises_negative_export`
- Setup: Two pricing periods — period 1 has negative import (incentive to charge), period 2 has negative export (penalty for forced solar export)
- Verify: LP sees the spill cost and may choose not to fill battery entirely in period 1

### Regression Safety

- All existing tests in `test_fsm_lin.py` must pass unchanged
- Full `pytest tests/` suite must pass

## Implementation Order

1. **Part A first** (plan builder guard) — lower risk, fixes the display bug immediately
2. **Part B second** (spill variable) — higher complexity, touches the LP constraint matrix
3. Run all tests after each part
4. Version bump to next beta

## Verification Plan

### Automated Tests
```bash
pytest tests/test_fsm_lin.py -v
pytest tests/ -v
```

### Manual Verification
Deploy to HA, fetch API status JSON, and verify:
- No `CHARGE_GRID` rows when SoC = 100%
- Net Grid is negative (export) when PV > Load at 100% SoC
- Cumulative cost trajectory is physically realistic
