# Tasks: 026 — Single State Source

**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/026-single-state-source/spec.md)
**Plan**: [plan.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/026-single-state-source/plan.md)
**Issue**: #26

## Task 1: Remove `dh_0`/`dg_0` from `propose_state_of_charge` return (FR-001)
- [ ] Remove `dh_0` extraction from LP result variables in `propose_state_of_charge`
- [ ] Remove `dg_0` extraction from LP result variables
- [ ] Remove `dg_0` gate override at L298-299 (redundant — gate already in sequence builder L267-277)
- [ ] Change return from `b_1/capacity, objective_value, dh_0, dg_0, sequence` to `b_1/capacity, objective_value, sequence`

## Task 2: Replace independent state classification in `calculate_next_state` (FR-001)
**Depends on**: Task 1
- [ ] Update unpacking at L357 from 5-tuple to 3-tuple: `target_soc_frac, projected_cost, sequence`
- [ ] Remove `dg_kw = raw_dg / (5.0 / 60.0)` (L394)
- [ ] Remove `dh_kw = raw_dh / (5.0 / 60.0)` (L395)
- [ ] Replace L378-423 (4-branch if/elif/else) with single-source logic:
  - Read `state_0 = sequence[0]["state"]` if sequence exists, else `"SELF_CONSUMPTION"` (FR-003)
  - Keep `target_delta_kwh` / `power_kw` calculation for limit_kw only (FR-002)
  - Force `limit_kw = 0.0` when `state_0 == "SELF_CONSUMPTION"`
  - Return single `FSMResult` using `state_0`

## Task 3: Update test callers of `propose_state_of_charge`
**Depends on**: Task 1
- [ ] `test_solver_replay.py:226`: Change `_, _, _, _, sequence` to `_, _, sequence`
- [ ] `test_lazy_import.py:80`: Change `assert len(res) == 5` to `assert len(res) == 3`

## Task 4: Add state agreement test (SC-004)
**Depends on**: Task 2
- [ ] Add `test_fsm_result_state_matches_plan_row_0` to `test_fsm_lin.py`
  - Construct boundary inputs where old Path 2 would disagree with Path 1
  - Assert `result.state == result.future_plan[0]["state"]` for all 3 states
- [ ] Add state agreement assertion to existing replay tests in `test_solver_replay.py`

## Task 5: Run full test suite and verify (SC-001, SC-002)
**Depends on**: Tasks 1-4
- [ ] `pytest tests/ -q --tb=short` — all tests pass
- [ ] Verify no `raw_dg`, `raw_dh`, `dg_0`, `dh_0` references remain in non-backup files
- [ ] Commit, push, tag, release
