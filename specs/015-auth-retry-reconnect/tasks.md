# Tasks: Auth Retry on Reconnect (015)

**Branch**: `015-auth-retry-reconnect`

## Phase 1: Setup

- [ ] T001 Verify branch `015-auth-retry-reconnect` is checked out

## Phase 2: Implementation (US1 — Panel Recovers After Idle)

- [ ] T002 [US1] Modify `_fetchData()` in `custom_components/house_battery_control/frontend/hbc-panel.js` — add 3s delay + retry on 401
- [ ] T003 [US1] Bump JS cache buster from `?v=48` to `?v=49` in `custom_components/house_battery_control/__init__.py`

## Phase 3: Verification

- [ ] T004 Run `pytest tests/ -v` — all tests pass
- [ ] T005 Run `ruff check custom_components/ tests/` — clean

## Phase 4: Branch Pre-Release

- [ ] T006 Follow `/release` workflow: tag as `v1.2.2-beta.1`, push, create pre-release
