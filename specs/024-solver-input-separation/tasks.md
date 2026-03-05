# Tasks: Solver Input Separation

**Feature Branch**: `024-solver-input-separation`  
**Plan**: [plan.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/024-solver-input-separation/plan.md)  
**Generated**: 2026-03-05

## Phase 1: Foundation — SolverInputs Dataclass

- [ ] T001 Add `SolverInputs` dataclass to `custom_components/house_battery_control/fsm/base.py`
- [ ] T002 Add `solver_inputs: SolverInputs | None = None` field to `FSMContext` in `custom_components/house_battery_control/fsm/base.py`

## Phase 2: Tests — Solver Contract (US1 — TDD, written before code)

- [ ] T003 [US1] Write `test_solver_fails_fast_without_solver_inputs` in `tests/test_fsm_lin.py` — verify ERROR when `solver_inputs` is None (FR-008)
- [ ] T004 [US1] Write `test_solver_uses_solver_inputs_prices` in `tests/test_fsm_lin.py` — verify row-0 uses `solver_inputs.price_buy[0]`, not `context.current_price` (FR-005, SC-003)
- [ ] T005 [US1] Write `test_solver_no_dict_parsing` in `tests/test_fsm_lin.py` — verify solver works with empty `forecast_price` when `solver_inputs` is populated (FR-005)

## Phase 3: Tests — Builder Method (US2 — TDD, written before code)

- [ ] T006 [P] [US2] Create `tests/test_solver_inputs_builder.py` with `test_build_price_arrays_from_rates` — verify `price_buy` and `price_sell` are `list[float]` of length 288 (FR-001)
- [ ] T007 [P] [US2] Write `test_build_price_row0_uses_live_price` — verify live price overrides forecast[0] (FR-002, SC-003 — THE BUG FIX)
- [ ] T008 [P] [US2] Write `test_build_price_row0_fallback_no_entity` — verify fallback to `rates.get_import_price_at(now)` (FR-002)
- [ ] T008b [P] [US2] Write `test_build_price_row0_sensor_unavailable_fallback` — verify fallback when current price entity is configured but sensor is unavailable (Edge case EC-2)
- [ ] T009 [P] [US2] Write `test_build_load_pv_arrays` — verify kW→kWh conversion (`× 5/60`) and length 288 (FR-003)
- [ ] T010 [P] [US2] Write `test_build_pads_short_arrays` — verify 100-element input padded to 288 (Edge case)
- [ ] T011 [P] [US2] Write `test_build_empty_forecast_returns_zeros` — verify empty input → 288 zeros (Edge case)

## Phase 4: Tests — No-Import Resolution (US3 — TDD, written before code)

- [ ] T012 [P] [US3] Write `test_build_no_import_steps` in `tests/test_solver_inputs_builder.py` — verify step indices for "15:00-21:00" (FR-004)
- [ ] T013 [P] [US3] Write `test_build_no_import_empty` — verify empty config → None (FR-004)
- [ ] T013b [P] [US3] Write `test_build_no_import_midnight_wrap` — verify midnight-spanning periods (e.g. "22:00-06:00") resolve correctly (Edge case EC-4)

## Phase 5: Confirm Tests Fail

- [ ] T014 Run `pytest tests/test_fsm_lin.py tests/test_solver_inputs_builder.py -v` — confirm new tests fail (TDD red phase)

## Phase 6: Implementation — Coordinator Builder (US2)

- [ ] T015 [US2] Implement `_build_solver_inputs()` method on `HBCDataUpdateCoordinator` in `custom_components/house_battery_control/coordinator.py`
- [ ] T016 [US2] Wire `_build_solver_inputs()` into `_async_update_data()` — call after forecast assembly, set `fsm_context.solver_inputs` before `calculate_next_state`

## Phase 7: Implementation — Solver Cleanup (US1)

- [ ] T017 [US1] Remove price array construction (L323-339) from `calculate_next_state` in `custom_components/house_battery_control/fsm/lin_fsm.py`
- [ ] T018 [US1] Remove load/solar extraction and kW→kWh conversion (L341-349) from `calculate_next_state`
- [ ] T019 [US1] Remove no-import period timestamp resolution (L375-396) from `calculate_next_state`
- [ ] T020 [US1] Add fail-fast guard at top of `calculate_next_state` — return ERROR if `solver_inputs` is None
- [ ] T021 [US1] Replace removed code with direct reads from `context.solver_inputs` fields

## Phase 8: Fixture Updates

- [ ] T022 Update `base_context` fixture in `tests/test_fsm_lin.py` to populate `solver_inputs` field from existing forecast data
- [ ] T023 Update any other test files that construct `FSMContext` directly (search all `tests/test_*.py`)

## Phase 9: Full Regression

- [ ] T024 Run `pytest tests/ -v` — all 191 existing + 11 new tests pass (202+ expected)
- [ ] T025 Run `scripts/test_fsm_offline.py` for output equivalence check (SC-002)

## Dependencies

```
T001 → T002 → T003-T013 (tests depend on dataclass existing)
T003-T013 → T014 (red phase confirmation)
T014 → T015-T016 (builder implementation)
T014 → T017-T021 (solver cleanup)
T015-T021 → T022-T023 (fixture updates)
T022-T023 → T024-T025 (regression)
```

## Parallel Opportunities

- T003-T005 can be written in one batch (same file, same class)
- T006-T011 are all [P] — independent tests in the new file
- T012-T013 are [P] — independent no-import tests
- T017-T021 are sequential edits to the same function
