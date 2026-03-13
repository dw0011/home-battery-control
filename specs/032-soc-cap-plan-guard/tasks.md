# Tasks: Feature 032 — SoC-Cap Plan Guard

**Branch**: `032-soc-cap-plan-guard`
**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/032-soc-cap-plan-guard/spec.md)
**Plan**: [plan.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/032-soc-cap-plan-guard/plan.md)

---

## Phase 1: Setup

- [x] T001 Verify all existing tests pass before any changes: `pytest tests/test_fsm_lin.py -v`
- [x] T002 Back up current `lin_fsm.py` variable layout comments for reference during Part B refactor

---

## Phase 2: Part A — Plan Builder Headroom Guard

**Goal**: Fix phantom `CHARGE_GRID` at 100% SoC in the forecast plan and immediate executor action.
**Test Criteria**: No `CHARGE_GRID` row appears in the plan when SoC = 100%. Net Grid is never positive at 100% SoC unless load > PV. Executor action at step 0 is also guarded.

- [x] T003 [US1] Add SoC headroom gate after LP variable extraction (after line 241) in `custom_components/house_battery_control/fsm/lin_fsm.py`
  - Calculate `headroom = capacity - step_b`
  - If `headroom <= 0`: clamp `step_c = 0.0`, reduce `step_g` by same amount
  - If `0 < headroom < step_c * eta_in`: clamp `step_c = headroom / eta_in`, reduce `step_g` accordingly
  - FR-001, FR-002, FR-003 (Clarification Q1: efficiency-aware clamping)
- [x] T004 [US1] Verify Net Grid and state classification use clamped values without additional code changes in `custom_components/house_battery_control/fsm/lin_fsm.py`
  - Existing lines 255 and 258-264 already reference local `step_c`/`step_g` — confirm no bypass paths
  - FR-004, FR-005
- [x] T005 [US1] Verify cumulative cost uses adjusted Net Grid values in `custom_components/house_battery_control/fsm/lin_fsm.py`
  - Existing lines 278-282 already reference local `net_grid_kwh` — confirm post-clamp values flow through
  - FR-006
- [x] T006 [US1] Verify immediate executor action is derived from plan[0] after guard in `custom_components/house_battery_control/fsm/lin_fsm.py`
  - Check `LinearBatteryStateMachine.calculate_next_state` reads state from `sequence[0]` (Clarification Q3)
- [x] T007 [US1] Write test `test_soc_cap_clamps_charge_at_100pct` in `tests/test_fsm_lin.py`
  - SoC=100%, import=-0.05, PV=4.0kW, Load=2.0kW → no CHARGE_GRID, Net Grid ≤ 0
  - Scenario 1, Scenario 2
- [x] T008 [US1] Write test `test_soc_cap_partial_headroom` in `tests/test_fsm_lin.py`
  - SoC=99%, capacity=27kWh (headroom=0.27kWh), verify charge clamped to headroom/eta_in
  - Scenario 3
- [x] T009 [US1] Write test `test_soc_cap_no_regression_normal_charging` in `tests/test_fsm_lin.py`
  - SoC=10%, normal prices → CHARGE_GRID still works unchanged
  - Scenario 4
- [x] T010 [US1] Run full test suite: `pytest tests/ -v`

---

## Phase 3: Part B — LP Spill Variable

**Goal**: Make the LP solver aware of forced solar export costs so it doesn't fill the battery early when downstream export prices are negative.
**Test Criteria**: With negative export prices during solar hours and negative import prices overnight, the LP should leave battery headroom rather than filling completely.
**Dependencies**: Phase 2 must be complete — Part A guard ensures plan builder correctness regardless of LP behavior.

- [x] T011 [US2] Shift variable offsets in `propose_state_of_charge` in `custom_components/house_battery_control/fsm/lin_fsm.py`
  - Add `s_off = 4 * number_step` (spill), shift `b_off = 5 * number_step`
  - Update `num_vars = 5 * number_step + (number_step + 1)`
  - Update all references to `b_off` (lines ~137, 178-186, 206-214, 226, 237)
- [x] T012 [US2] Add spill variable bounds and objective cost in `custom_components/house_battery_control/fsm/lin_fsm.py`
  - `bounds[s_off + i] = (0.0, max(0, pv-load))` — spill capped at physical solar excess
  - `obj[s_off + i] = price_sell[i]` — costed at export price
  - Clarification Q2: physics-only, uniform across all steps
  - FR-007
- [x] T013 [US2] Add spill inequality constraint rows to `A_ub` in `custom_components/house_battery_control/fsm/lin_fsm.py`
  - Constraint: `-s[i] - c[i] <= energy[i]` (when energy < 0, forces spill to capture solar excess not absorbed by charge)
  - Expand `a_ub` from N rows to 2N rows (original grid balance + spill constraints)
  - FR-008
- [x] T014 [US2] Write test `test_spill_variable_penalises_negative_export` in `tests/test_fsm_lin.py`
  - Period 1: negative import (cheap charge incentive), Period 2: negative export + high PV
  - Verify LP doesn't fill battery to 100% if spill cost exceeds import savings
  - Scenario 5
- [x] T015 [US2] Run full test suite: `pytest tests/ -v`

---

## Phase 4: Polish & Release

- [x] T016 Run full regression test suite: `pytest tests/ -v` (218 passed, 2 xfailed)
- [ ] T017 Bump version in `custom_components/house_battery_control/manifest.json` and `hacs.json`
- [ ] T018 Commit, push, and create release

---

## Dependencies

```text
Phase 1 (Setup) → Phase 2 (Part A) → Phase 3 (Part B) → Phase 4 (Polish)
```

Part B depends on Part A because:
1. The plan builder guard must be in place before LP changes, so test stability is maintained
2. Part A is lower risk and delivers immediate value (fixes display bug)

## Parallel Opportunities

Within Phase 2:
- T007, T008, T009 can be written in parallel [P] — they test different scenarios in the same file

Within Phase 3:
- T011, T012 are sequential (offset shift must precede objective function)
- T013 depends on T011 (row count in A_ub depends on offset layout)

## Implementation Strategy

**MVP**: Phase 2 alone fixes the user-visible display bug. Ship as a beta after Phase 2 if needed.
**Full Feature**: Phase 3 adds LP optimisation awareness. Ship after Phase 3 passes all tests.

## Summary

| Phase | Tasks | Notes |
|-------|-------|-------|
| Setup | 2 | Pre-flight verification |
| Part A (Plan Guard) | 8 | Display fix + executor override |
| Part B (LP Spill) | 5 | Solver enhancement |
| Polish | 3 | Version bump + release |
| **Total** | **18** | |
