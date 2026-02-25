# Tasks: Configurable Panel Visibility

**Feature Branch**: `02-panel-visibility`  
**Plan**: [plan.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/02-panel-visibility/plan.md)  
**Generated**: 2026-02-25

## Phase 1: Config Constant

- [ ] T001 Add `CONF_PANEL_ADMIN_ONLY = "panel_admin_only"` to `const.py` after Scripts section
- [ ] T002 Add `DEFAULT_PANEL_ADMIN_ONLY = True` to `const.py` after `DEFAULT_RESERVE_SOC`

## Phase 2: Options Flow [US1, US2]

- [ ] T003 [US1] Import `CONF_PANEL_ADMIN_ONLY` and `DEFAULT_PANEL_ADMIN_ONLY` in `config_flow.py`
- [ ] T004 [US1] Add `BooleanSelector` field to `HBCOptionsFlowHandler.async_step_control` schema
- [ ] T005 [US2] Add `panel_admin_only` translation key to `en.json` options → control → data

## Phase 3: Panel Registration [US1, US3]

- [ ] T006 [US1] Import `CONF_PANEL_ADMIN_ONLY` and `DEFAULT_PANEL_ADMIN_ONLY` in `__init__.py`
- [ ] T007 [US1] Replace hardcoded `require_admin=True` with config lookup in `async_setup_entry`

## Phase 4: Tests

- [ ] T008 Add `test_panel_admin_only_constant_exists` to `test_init.py`
- [ ] T009 Add `test_options_control_has_panel_visibility` to `test_config_flow.py`
- [ ] T010 Run `pytest tests/ -v` — all pass

## Phase 5: Commit & Deploy

- [ ] T011 Commit and push to `02-panel-visibility`
- [ ] T012 Merge to `main`, HACS redownload, HA restart
- [ ] T013 Verify: Options → Control shows toggle, default is ON (admin-only)
- [ ] T014 Verify: Toggle OFF → reload → non-admin sees sidebar

## Parallel Opportunities
- T001 ∥ T002 (both in `const.py`, single edit)
- T003 ∥ T004 (both in `config_flow.py`, single edit)
- T006 ∥ T007 (both in `__init__.py`, single edit)

## MVP Scope
T001–T007 + T010 = functional feature with tests
