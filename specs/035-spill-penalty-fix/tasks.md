# Feature 035 Tasks

## Phase 1: Planning (Current)
- [x] T001 Write `spec.md` for the fix
- [x] T002 Write `plan.md` outlining the objective function change
- [x] T003 Generate `tasks.md`
- [ ] T004 Get user approval for the plan

## Phase 2: Implementation
- [ ] T005 Update `custom_components/house_battery_control/fsm/lin_fsm.py` with `obj[s_off + i] = max(0.0, -price_sell[i])`
- [ ] T006 Add `test_spill_variable_penalises_negative_export` in `tests/test_fsm_lin.py` to ensure solver doesn't fill up battery early when export is negative later.

## Phase 3: Verification
- [ ] T007 Run specific test: `pytest tests/test_fsm_lin.py -k test_spill_variable`
- [ ] T008 Run full regression suite: `pytest tests/`

## Phase 4: Release
- [ ] T009 Update `manifest.json` and `hacs.json` to next version if required
- [ ] T010 Commit and push changes
