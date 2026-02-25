# Tasks: Config Flow Options Regression (007)

**Branch**: `007-config-flow-regression`  
**Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/007-config-flow-regression/spec.md)  
**Plan**: [plan.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/007-config-flow-regression/plan.md)

## Phase 1: Foundation
- [ ] T001 Add `CONF_OBSERVATION_MODE = "observation_mode"` to `const.py`
- [ ] T002 Add observation mode early-return gate to `execute.py` `apply_state()`

## Phase 2: Options Flow (User Story 1 + 2)
- [ ] T003 Rewrite `HBCOptionsFlowHandler.async_step_control` in `config_flow.py` with observation_mode toggle, 4 script selectors, panel_admin_only, and entity-clearing logic
- [ ] T004 Update `strings.json` options control section with all labels
- [ ] T005 Update `translations/en.json` options control section with matching labels

## Phase 3: Verification
- [ ] T006 Run `pytest tests/test_config_flow.py -v`
- [ ] T007 Run `pytest tests/ -v` (full suite, 134 tests)
- [ ] T008 Deploy to HA, verify Options → Control form, toggle observation mode, clear script entity

## Dependencies
- T002 depends on T001 (imports the new constant)
- T003 depends on T001 (imports the new constant)
- T004 and T005 are independent
- T006-T008 depend on all prior tasks
