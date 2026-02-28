# Tasks: Push-Driven Panel Updates (016)

**Branch**: `016-hass-push-driven-panel`

## Phase 1: Setup

- [ ] T001 Verify branch `016-hass-push-driven-panel` is checked out

## Phase 2: Implementation (US1 — Panel Survives Tab Idle)

- [ ] T002 [US1] Add `_lastFetch` field to constructor, rename `_interval` to `_fallbackInterval`
- [ ] T003 [US1] Replace `setInterval(30s)` with 60s fallback timer in `connectedCallback`/`disconnectedCallback`
- [ ] T004 [US1] Add `updated(changedProps)` method — detect `hass` changes, check `sensor.hbc_state.last_updated`, call `_debouncedFetch()`
- [ ] T005 [US1] Add `_debouncedFetch()` method — 10s debounce guard around `_fetchData()`

## Phase 3: Implementation (US2 — Real-Time Updates)

- [ ] T006 [US2] Verify `_fetchData` 401 retry logic from feature 015 is retained (no changes needed, just confirm)

## Phase 4: Cache Buster

- [ ] T007 Bump JS cache buster from `?v=48` to `?v=50` in `__init__.py`

## Phase 5: Verification

- [ ] T008 Run `pytest tests/ -v` — all tests pass
- [ ] T009 Run `ruff check custom_components/ tests/` — clean

## Phase 6: Branch Pre-Release

- [ ] T010 Follow `/release` workflow: version bump, tag, push, create pre-release
