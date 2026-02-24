# Feature Specification: Admin-Only API Access & Plan Table Deprecation

**Feature Branch**: `01-admin-api-auth`  
**Created**: 2026-02-24  
**Status**: Draft  
**Input**: User comments on system_requirements.md: (1) `/hbc/api/status` must be admin-level only; hbc-panel needs a different data mechanism. (2) §2.2.1 Plan Table Data Interpolation is deprecated and must be removed.

## User Scenarios & Testing

### User Story 1 - Admin-Only API Access (Priority: P1)

As a Home Assistant administrator, I need the HBC API endpoints to be restricted to authenticated admin users only, so that sensitive battery control data and operational state are not exposed to unauthenticated or non-admin users on my network.

**Why this priority**: Security. Currently all `/hbc/*` endpoints are publicly accessible to anyone on the local network without authentication. This exposes real-time energy pricing, battery state, solar forecasts, and operational control data.

**Independent Test**: An unauthenticated HTTP request to `/hbc/api/status` must return HTTP 401. An authenticated admin request must return the full JSON payload.

**Acceptance Scenarios**:

1. **Given** an unauthenticated user, **When** they request `/hbc/api/status`, **Then** they receive HTTP 401 Unauthorized.
2. **Given** an authenticated admin user, **When** they request `/hbc/api/status`, **Then** they receive the full JSON diagnostic payload.
3. **Given** an authenticated non-admin user, **When** they request `/hbc/api/status`, **Then** they receive HTTP 401 Unauthorized.
4. **Given** the hbc-panel web component is loaded by an admin user, **When** the panel fetches data, **Then** it successfully authenticates using the HA session credentials and displays the dashboard.

---

### User Story 2 - Panel Authentication Flow (Priority: P1)

As an admin user viewing the HBC dashboard panel, I need the panel to seamlessly pass my HA authentication credentials when fetching API data, so that the transition to admin-only endpoints doesn't break the user experience.

**Why this priority**: The panel currently uses unauthenticated `fetch()` calls to `/hbc/api/status`. When the API is locked to admin-only, the panel must supply HA auth tokens or the dashboard becomes non-functional.

**Independent Test**: Loading `/hbc` as an admin user displays the dashboard with live data. Loading `/hbc` as a non-admin user shows an appropriate access denied message.

**Acceptance Scenarios**:

1. **Given** an admin user has the HBC panel open, **When** the panel fetches data from `/hbc/api/status`, **Then** the request includes the HA authentication token and succeeds.
2. **Given** a non-admin user attempts to access the HBC panel, **When** the page loads, **Then** an appropriate "insufficient permissions" notice is displayed instead of the dashboard.

---

### User Story 3 - Deprecate Plan Table Interpolation (Priority: P2)

As a maintainer, I need §2.2.1 "Plan Table Data Interpolation" removed from the system requirements and any associated diagnostic-only code paths deprecated, so the codebase reflects the current production direction.

**Why this priority**: This section describes diagnostic-only behaviour that is not part of the final production application. Removing it reduces maintenance burden and prevents confusion about which requirements are active.

**Independent Test**: After removal, the system requirements document no longer contains §2.2.1. All code exclusively supporting this deprecated interpolation path is fully removed from the codebase.

**Acceptance Scenarios**:

1. **Given** the system requirements document, **When** §2.2.1 is removed, **Then** no remaining sections reference "Plan Table Data Interpolation" as a current requirement.
2. **Given** the codebase, **When** the deprecation is applied, **Then** all code exclusively implementing §2.2.1 interpolation logic is fully removed.
3. **Given** the codebase, **When** the `/hbc/plan` endpoint is removed, **Then** no route handler or HTML view for `/hbc/plan` exists.

---

### Edge Cases

- What happens if HA downgrades a user from admin to non-admin while the panel is open? The next API poll should fail gracefully and display a "session expired / insufficient permissions" message.
- What happens if the HA auth token expires during a long session? The panel should handle 401 responses by prompting reauthentication or displaying an appropriate error.
- The `/hbc/plan` HTML view must be fully removed as it is no longer a production requirement.

## Requirements

### Functional Requirements

- **FR-001**: All `/hbc/*` HTTP endpoints MUST require admin-level HA authentication.
- **FR-002**: The `hbc-panel.js` web component MUST pass the HA authentication token via `Authorization: Bearer` header with every API fetch request, using the standard `this.hass.auth.data.access_token` provided by HA to custom panels.
- **FR-003**: Unauthenticated or non-admin requests to any `/hbc/*` endpoint MUST receive HTTP 401.
- **FR-004**: The HBC custom panel registration MUST specify `require_admin=True` so HA only shows it to admin users.
- **FR-005**: §2.2.1 "Plan Table Data Interpolation" MUST be removed from `system_requirements.md`.
- **FR-006**: The `/hbc/plan` HTML endpoint and its route handler MUST be fully removed from the codebase.
- **FR-007**: All remaining `/hbc/*` endpoint views (dashboard HTML, config YAML, ping, load history) MUST enforce the same admin-only restriction consistently.

### Key Entities

- **HA Auth Token**: The bearer token provided by HA to authenticated users, available in the panel via `this.hass.auth.data.access_token`.
- **Admin User**: An HA user with the `is_admin` flag set to `true`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of `/hbc/*` endpoints return HTTP 401 for unauthenticated requests.
- **SC-002**: Admin users experience zero change in dashboard functionality after auth enforcement.
- **SC-003**: §2.2.1 is fully removed from `system_requirements.md` with no orphaned references.
- **SC-004**: All existing unit tests pass after changes, with new tests covering auth enforcement.

## Assumptions

- HA provides the auth token to custom panels via the standard `this.hass` object.
- The `require_admin` flag on `panel_custom` registration is sufficient to restrict sidebar access.
- API-level auth enforcement is additionally needed because endpoints are reachable via direct URL even if the sidebar entry is hidden.

## Clarifications

### Session 2026-02-25

- Q: How should the panel authenticate its API requests? → A: Option A — Pass HA auth token via `Authorization: Bearer` header on existing fetch calls. Standard HA pattern, minimal changes, security guaranteed by HA's built-in auth middleware.
