# Feature Specification: Fix Auth Token Expiry

**Feature Branch**: `013-fix-auth-token-expiry`  
**Created**: 2026-02-28  
**Status**: Draft  
**Input**: User description: "Fix dashboard auth token expiry causing 401 login failed errors after 30 minutes (GitHub Issue #7)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dashboard Stays Alive (Priority: P1)

As a Home Assistant admin, I want the HBC dashboard panel to remain functional indefinitely without requiring a page refresh, so I can leave the panel open on a wall-mounted tablet and trust the data is always current.

**Why this priority**: This is the core user-facing bug. Users report "login failed" errors after leaving the dashboard open, requiring manual page refreshes. A monitoring dashboard that silently stops updating is worse than useless — it creates a false sense of visibility.

**Independent Test**: Open the HBC panel in HA sidebar, leave it open for 60+ minutes, confirm status data continues to refresh every 30 seconds without errors.

**Acceptance Scenarios**:

1. **Given** the HBC panel is open in the HA sidebar, **When** 60 minutes elapse without user interaction, **Then** the dashboard still displays current battery/solar/grid data without "Login Failed" or 401 errors.
2. **Given** the HA access token has expired, **When** the panel's 30-second polling timer fires, **Then** the system automatically obtains a fresh token and completes the API request successfully.
3. **Given** the user is not an admin, **When** they view the panel, **Then** a clear "admin access required" message is shown (not a cryptic "login failed").

---

### Edge Cases

- What happens when the HA WebSocket connection drops temporarily (network blip)? The panel should recover on next poll attempt.
- What happens when the user's session is revoked (e.g., admin removes long-lived token)? A clear re-login prompt should appear.
- What happens when `this.hass` is null during initial panel load? A loading state should be shown, not an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard panel MUST continue to successfully poll `/hbc/api/status` indefinitely without manual page refresh.
- **FR-002**: The panel MUST use Home Assistant's approved authentication mechanism that handles token refresh automatically.
- **FR-003**: The panel MUST gracefully handle 401 responses by displaying a clear permission error, not a generic "login failed".
- **FR-004**: The panel MUST guard against null/undefined `this.hass` during early lifecycle or reconnection events.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dashboard panel remains fully functional after 60+ minutes of idle open time without page refresh.
- **SC-002**: Zero "login failed" errors appear in HA notification logs during normal panel operation.
- **SC-003**: All 150 existing tests continue to pass (no regression).
- **SC-004**: Token refresh is handled transparently — users never see authentication-related interruptions during normal operation.

## Assumptions

- The `this.hass` object provided by HA's panel framework is refreshed automatically by the frontend with current auth state.
- HA's `hass.fetchWithAuth()` or equivalent method handles token refresh transparently for non-`/api/` prefixed endpoints.
- The fix is frontend-only (`hbc-panel.js`) — no backend changes to `web.py` are required.
