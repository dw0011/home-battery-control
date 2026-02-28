# Feature Specification: Auth Retry on Reconnect

**Feature Branch**: `015-auth-retry-reconnect`  
**Created**: 2026-02-28  
**Status**: Draft  
**Input**: "Fix panel auth failure after tab idle by retrying on 401 with reconnect delay (GitHub Issues #7/#11)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Panel Recovers After Tab Idle (Priority: P1)

As an HBC user with the dashboard open on a wall tablet, I want the panel to automatically recover when I switch back to it after it's been idle for hours, so I never see "Login Failed" or a blank screen.

**Why this priority**: This is the core user-facing bug. The panel becomes unusable after extended idle, requiring manual page refresh.

**Independent Test**: Open the HBC panel, switch to another tab for 2+ hours, return — confirm data resumes automatically within 5 seconds without manual refresh.

**Acceptance Scenarios**:

1. **Given** the panel has been idle for 2+ hours, **When** the user returns to the tab, **Then** data resumes within 5 seconds without manual refresh.
2. **Given** a 401 occurs on fetch, **When** the retry fires after a brief delay, **Then** the second attempt succeeds using the refreshed auth state.
3. **Given** a genuine permission error (non-admin user), **When** both attempts return 401, **Then** the "admin access required" message is shown.

---

### Edge Cases

- What if the WebSocket never reconnects (network down)? Show a connection error, not a permissions error.
- What if `this.hass` becomes null during reconnection? Guard and retry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: On a 401 response, the panel MUST wait briefly (3 seconds) and retry the fetch once before showing an error.
- **FR-002**: If the retry also returns 401, the panel MUST display the "admin access required" message.
- **FR-003**: If `fetchWithAuth` throws an exception (network error), the panel MUST display the error message, not a permissions message.
- **FR-004**: The retry mechanism MUST be transparent to the user — no visible loading indicators during the retry delay.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Panel recovers automatically after 2+ hours of tab idle without page refresh.
- **SC-002**: No false "Login Failed" or "admin access required" during normal tab-switching.
- **SC-003**: All existing tests pass (no regression).
- **SC-004**: Genuine permission errors are still correctly reported after retry.
