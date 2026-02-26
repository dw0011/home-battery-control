# Tasks: Executor Command Deduplication Fix (009)

**Branch**: `009-executor-command-dedup`

## Phase 1: Implementation
- [ ] T001 Add `_last_executed_state` and `_last_executed_limit` fields to `PowerwallExecutor.__init__`
- [ ] T002 Add `last_executed_state` property
- [ ] T003 Rewrite `apply_state()` with new dedup logic (always update requested, dedup against executed, update executed only after success)
- [ ] T004 Write test: `test_observation_mode_suppresses_execution`
- [ ] T005 Write test: `test_observation_mode_exit_triggers_execution`
- [ ] T006 Write test: `test_observation_mode_dedup_after_real_execution`

## Phase 2: Verification
- [ ] T007 Run `pytest tests/test_execute.py -v`
- [ ] T008 Run `pytest tests/ -v` (full suite)
- [ ] T009 Deploy to HA, verify in logs

## Dependencies
- T003 depends on T001, T002
- T004-T006 depend on T003
- T007-T009 depend on all prior tasks
