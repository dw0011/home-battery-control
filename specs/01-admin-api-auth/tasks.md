# Tasks: Admin-Only API Access & Plan Table Deprecation

**Feature Branch**: `01-admin-api-auth`  
**Plan**: [plan.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/01-admin-api-auth/plan.md)  
**Generated**: 2026-02-25

## Phase 1: Setup

- [x] T001 Create archive branch `archive/pre-admin-auth` from `main` and push to origin — permanent snapshot of working codebase before changes

## Phase 2: Foundational (Remove `/hbc/plan`)

- [x] T002 Delete `HBCPlanView` class from `custom_components/house_battery_control/web.py`
- [x] T003 Remove `HBCPlanView` import from `custom_components/house_battery_control/__init__.py`
- [x] T004 Remove `hass.http.register_view(HBCPlanView())` registration from `custom_components/house_battery_control/__init__.py`
- [x] T005 Remove `test_web_has_plan_view` test from `tests/test_web.py`
- [x] T006 Remove `test_plan_is_public` test from `tests/test_web.py`
- [x] T007 Remove `test_plan_html_includes_local_time_column` test from `tests/test_web.py`
- [x] T008 Run `pytest tests/ -v` — confirmed no import errors or failures from removed class

## Phase 3: User Story 1 — Admin-Only API Access [US1]

- [x] T009 [US1] Set `requires_auth = True` on `HBCDashboardView` in `web.py`
- [x] T010 [P] [US1] Set `requires_auth = True` on `HBCApiStatusView` in `web.py`
- [x] T011 [P] [US1] Set `requires_auth = True` on `HBCApiPingView` in `web.py`
- [x] T012 [P] [US1] Set `requires_auth = True` on `HBCConfigYamlView` in `web.py`
- [x] T013 [P] [US1] Set `requires_auth = True` on `HBCLoadHistoryView` in `web.py`
- [x] T014 [US1] Add `require_admin=True` to `async_register_built_in_panel()` in `__init__.py`
- [x] T015 [US1] Update `test_dashboard_is_public` → `test_dashboard_requires_auth` in `test_web.py`
- [x] T016 [P] [US1] Update `test_api_status_is_public` → `test_api_status_requires_auth` in `test_web.py`
- [x] T017 [P] [US1] Update `test_api_ping_public` → `test_api_ping_requires_auth` in `test_web.py`
- [x] T018 [US1] Update `test_load_history_api_public` → `test_load_history_api_requires_auth` in `test_web.py`
- [x] T019 [US1] Run `pytest tests/ -v` — 131 passed ✓

## Phase 4: User Story 2 — Panel Authentication Flow [US2]

- [x] T020 [US2] Update `_fetchData()` in `hbc-panel.js` with `Authorization: Bearer` header
- [x] T021 [US2] Add 401 error handling — "Insufficient permissions" message
- [x] T022 [US2] No JS test changes needed — `test_js_plan_data_structures` tests `build_status_data` passthrough, not fetch

## Phase 5: User Story 3 — Spec & Doc Cleanup [US3]

- [x] T023 [US3] Remove §2.2.1 "Plan Table Data Interpolation" from `system_requirements.md`
- [x] T024 [US3] Update §2.2 to reflect admin-only access in `system_requirements.md`
- [x] T025 [US3] Remove `/hbc/plan` reference from §2.3 and §4.2 in `system_requirements.md`

## Phase 6: Polish & Verification

- [x] T026 Run `pytest tests/ -v` — 131 passed, 0 failed ✓
- [x] T027 Commit `1aa67af` and push to `01-admin-api-auth` branch ✓
- [ ] T028 Deploy to HA via HACS redownload + restart
- [ ] T029 Verify: admin user sees dashboard, unauthenticated request returns 401, `/hbc/plan` returns 404
