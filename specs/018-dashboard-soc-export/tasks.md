# Tasks: Dashboard SoC & Export Price Layout

**Feature**: 018-dashboard-soc-export  
**Branch**: `018-dashboard-soc-export`  
**Total Tasks**: 8

## Phase 1: Setup

- [ ] T001 Create feature branch and verify clean state on `018-dashboard-soc-export`

## Phase 2: Tests First (TDD)

- [ ] T002 [P] [US1] Write browser test: SoC is present in Power Flow card in `tests/test_web.py`
- [ ] T003 [P] [US1] Write browser test: SoC is NOT present in Status Grid in `tests/test_web.py`
- [ ] T004 [P] [US2] Write browser test: Export c/kWh is present in Status Grid in `tests/test_web.py`

## Phase 3: User Story 1 — SoC in Power Flow Bar (P1)

**Goal**: SoC percentage appears as 5th item in Power Flow card, removed from Status Grid.  
**Independent Test**: SoC value visible in Power Flow section, absent from Status section.

- [ ] T005 [US1] Add SoC as 5th flow-item in Power Flow card in `custom_components/house_battery_control/frontend/hbc-panel.js`
- [ ] T006 [US1] Remove SoC from Status Grid in `custom_components/house_battery_control/frontend/hbc-panel.js`

## Phase 4: User Story 2 — Export Price on Dashboard (P1)

**Goal**: Current export price (c/kWh) shown in Status Grid after import price.  
**Independent Test**: Export c/kWh visible after Import c/kWh in Status Grid.

- [ ] T007 [US2] Read export price from `plan[0]["Export Rate"]` and add Export c/kWh stat to Status Grid, rename "Price c/kWh" to "Import c/kWh" in `custom_components/house_battery_control/frontend/hbc-panel.js`

## Phase 5: Verification

- [ ] T008 Run full test suite (`pytest tests/ -q`) and verify 0 regressions

## Dependencies

```
T001 → T002, T003, T004 (setup before tests)
T002, T003 → T005, T006 (TDD: tests before code)
T004 → T007 (TDD: tests before code)
T005, T006, T007 → T008 (all implementation before final verification)
```

## Parallel Opportunities

- T002, T003, T004 can run in parallel (different test cases, same file)
- T005 + T006 can be done in one edit (same file, same function)
- T007 is independent of T005/T006 (different section of same function)
