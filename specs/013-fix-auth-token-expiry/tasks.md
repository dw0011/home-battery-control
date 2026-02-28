# Tasks: Fix Auth Token Expiry (013)

**Feature**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/013-fix-auth-token-expiry/spec.md)  
**Plan**: [plan.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/013-fix-auth-token-expiry/plan.md)  
**Branch**: `013-fix-auth-token-expiry`

## Phase 1: Setup

- [ ] T001 Verify branch `013-fix-auth-token-expiry` is checked out and clean

## Phase 2: Implementation (User Story 1 — Dashboard Stays Alive, P1)

- [ ] T002 [US1] Replace `_fetchData()` in `custom_components/house_battery_control/frontend/hbc-panel.js` to use `this.hass.fetchWithAuth()` per plan.md
- [ ] T003 [US1] Add null guard for `this.hass` at top of `_fetchData()` in `custom_components/house_battery_control/frontend/hbc-panel.js`
- [ ] T004 [US1] Preserve 401 error handling for non-admin users in `_fetchData()` in `custom_components/house_battery_control/frontend/hbc-panel.js`

## Phase 3: Verification

- [ ] T005 Run `pytest tests/ -v` — all 150 tests must pass
- [ ] T006 Run `ruff check custom_components/ tests/` — must be clean
- [ ] T007 Deploy to HA via `/update-ha` workflow (from branch)
- [ ] T008 Use browser agent to open the HBC panel at `http://homeassistant.local:8123/hbc-panel` and confirm data loads
- [ ] T009 Use browser agent to revisit the HBC panel after 35+ minutes and confirm no 401 or "Login Failed" error appears

## Phase 4: Branch Pre-Release

- [ ] T010 Follow `/release` workflow with `--prerelease` flag: tag as `v1.2.1-beta.1`, push branch to origin
- [ ] T011 After soak test confirmed (manual user approval), merge to `main` and cut stable `v1.2.1` release

## Dependencies

```
T001 → T002, T003, T004 (parallel)
T002, T003, T004 → T005
T005 → T006
T006 → T007 (deploy to HA)
T007 → T008 (browser check)
T008 → T009 (soak test after 35+ min)
T009 → T010 (pre-release tag)
T010 → T011 (user approval → merge to main)
```

## Summary

- **Total tasks**: 11
- **Branch strategy**: Pre-release on branch, merge to main only after soak test passes
- **Verification**: Agentic browser-based — open panel, wait 35+ min, confirm no auth errors
