# Implementation Plan: Admin-Only API Access & Plan Table Deprecation

**Feature Branch**: `01-admin-api-auth`  
**Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/01-admin-api-auth/spec.md)  
**Created**: 2026-02-25

## Technical Context

| Item | Current State |
|---|---|
| `web.py` views | 6 classes, ALL `requires_auth = False` |
| Panel registration | `async_register_built_in_panel` — no `require_admin` param |
| `hbc-panel.js` fetch | Bare `fetch("/hbc/api/status")` — no auth headers |
| `/hbc/plan` endpoint | `HBCPlanView` class registered in `__init__.py` line 65 |
| `system_requirements.md` | §2.2.1 still present |

## Proposed Changes

### Component 1: Backend Auth Enforcement (`web.py`)

#### [MODIFY] [web.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/web.py)

1. Set `requires_auth = True` on all 5 remaining view classes:
   - `HBCDashboardView` (line 112)
   - `HBCApiStatusView` (line 256)
   - `HBCApiPingView` (line 278)
   - `HBCConfigYamlView` (line 289)
   - `HBCLoadHistoryView` (line 311)

2. **Delete** the entire `HBCPlanView` class (lines 171–248) — FR-006.

---

### Component 2: Panel Registration (`__init__.py`)

#### [MODIFY] [\_\_init\_\_.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/__init__.py)

1. Add `require_admin=True` to `async_register_built_in_panel()` call (line 77) — FR-004.
2. Remove `HBCPlanView` import (line 21) and registration (line 65) — FR-006.

---

### Component 3: Frontend Auth Headers (`hbc-panel.js`)

#### [MODIFY] [hbc-panel.js](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/frontend/hbc-panel.js)

1. Update `_fetchData()` (line 48) to include Bearer token:
   ```js
   const resp = await fetch("/hbc/api/status", {
     headers: { "Authorization": `Bearer ${this.hass.auth.data.access_token}` }
   });
   ```
2. Add 401 error handling: display "Insufficient permissions" message — Edge Case.

---

### Component 4: Spec Document Cleanup

#### [MODIFY] [system_requirements.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/system_requirements.md)

1. Remove §2.2.1 "Plan Table Data Interpolation" (lines 29–35) — FR-005.
2. Update §2.2 to reflect admin-only access — FR-001.
3. Update §2.3 to remove `/hbc/plan` endpoint reference — FR-006.
4. Update §4.2 to remove Plan Table reference — FR-006.

---

### Component 5: Test Updates (`test_web.py`)

#### [MODIFY] [test_web.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_web.py)

1. **Remove** `test_web_has_plan_view` (line 49) — tests deleted class.
2. **Remove** `test_plan_is_public` (line 81) — tests deleted endpoint.
3. **Remove** `test_plan_html_includes_local_time_column` (line 535) — tests deleted view.
4. **Update** `test_dashboard_is_public` → rename to `test_dashboard_requires_auth`, assert `requires_auth = True`.
5. **Update** `test_api_status_is_public` → assert `requires_auth = True`.
6. **Update** `test_api_ping_public` → assert `requires_auth = True`.
7. **Add** new test: `test_all_views_require_auth` — loop all view classes and assert `requires_auth = True`.

> [!IMPORTANT]
> Plan table *data generation* in `coordinator.py` (`_build_diagnostic_plan_table`) is NOT removed — it feeds the panel's data payload. Only the standalone HTML endpoint is removed.

## Verification Plan

### Automated Tests

```bash
pytest tests/ -v
```

- All 134+ tests must pass after changes
- New auth tests must assert `requires_auth = True` on all views
- Removed plan view tests must not cause import errors

### Manual Verification

1. Deploy to HA via HACS redownload + restart
2. Open browser to `http://homeassistant.local:8123/hbc-panel` — dashboard loads for admin user
3. Open incognito/unauthenticated browser to `http://homeassistant.local:8123/hbc/api/status` — returns 401
4. Verify `http://homeassistant.local:8123/hbc/plan` returns 404 (endpoint removed)

## Execution Order

1. `web.py` — delete `HBCPlanView`, set `requires_auth = True` on remaining views
2. `__init__.py` — remove plan import/registration, add `require_admin=True` to panel
3. `hbc-panel.js` — add Bearer auth header to fetch
4. `test_web.py` — remove plan tests, update auth assertions
5. `system_requirements.md` — remove §2.2.1 and update references
6. Run tests → verify → commit → deploy
