# Tasks: No-Import Periods (010)

**Branch**: `010-no-import-periods`

## Phase 1: Core Implementation
- [ ] T001 Add `CONF_NO_IMPORT_PERIODS` to `const.py`
- [ ] T002 Add `_parse_no_import_periods()` and `_is_in_no_import_period()` helpers to `lin_fsm.py`
- [ ] T003 Add `no_import_steps` parameter to `propose_state_of_charge()` and clamp `g[i]` bounds
- [ ] T004 Wire no-import period logic into `calculate_next_state()`
- [ ] T005 Pass `no_import_periods` config in coordinator.py

## Phase 2: Config & UI
- [ ] T006 Add `CONF_NO_IMPORT_PERIODS` to Options flow in `config_flow.py`
- [ ] T007 Add translations in `strings.json` and `en.json`

## Phase 3: Tests
- [ ] T008 Write parser tests (parse single, multiple, empty, invalid)
- [ ] T009 Write time-check tests (within, outside, midnight wrap)
- [ ] T010 Write LP solver test (no-import period produces zero import)

## Phase 4: Verification
- [ ] T011 Run `pytest tests/test_fsm_lin.py -v`
- [ ] T012 Run `pytest tests/ -v` (full suite)
- [ ] T013 Deploy to HA, verify plan table
- [ ] T014 Post GitHub issue #4 response

## Dependencies
- T003 depends on T001, T002
- T004 depends on T003
- T005 depends on T001
- T006-T007 depend on T001
- T008-T010 depend on T002-T004
- T011-T014 depend on all prior
