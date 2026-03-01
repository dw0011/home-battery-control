# Feature Specification: Push-Driven Panel Updates

**Feature Branch**: `016-hass-push-driven-panel`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: "Replace setInterval polling with HA hass reactivity for push-driven panel updates (GitHub Issue #12)"

## Problem Statement

The HBC dashboard panel uses `setInterval` (30s) to poll an HTTP API endpoint for data. This approach:

1. **Breaks on background tabs**: Chrome freezes timers → token expires → 401 on return
2. **Has 30-second update lag**: Data only refreshes when the timer fires, not when the coordinator actually updates
3. **Wastes resources**: Polls even when nothing has changed
4. **Conflicts with HA architecture**: HA is push-based (WebSocket) but our panel ignores this entirely

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Panel Survives Tab Idle (Priority: P1)

As an HBC user with the dashboard on a wall tablet, I want the panel to automatically recover and show current data when I switch back to it after hours of idle, without any manual refresh.

**Why this priority**: This is the primary user-facing bug (issues #7, #11, #12). The architectural fix eliminates the root cause.

**Independent Test**: Open the HBC panel, leave idle for 2+ hours, return — data displays automatically within seconds.

**Acceptance Scenarios**:

1. **Given** the panel has been idle for 2+ hours, **When** the user returns to the tab, **Then** HA reconnects the WebSocket and pushes fresh `hass` state → panel re-renders with current data.
2. **Given** the coordinator runs and updates data, **When** the panel is focused, **Then** the panel updates within the HA event cycle (typically <2 seconds), not after a 30-second timer.
3. **Given** `this.hass` becomes null during reconnection, **When** the panel checks for updates, **Then** it silently waits and re-renders on the next valid `hass` push.

### User Story 2 - Real-Time Updates (Priority: P2)

As an HBC user actively watching the dashboard, I want to see data update in near real-time when the coordinator computes a new plan, so I can observe the system reacting to price changes and solar forecasts.

**Independent Test**: Trigger a coordinator update (via HA developer tools or config reload), confirm the dashboard updates within 2 seconds without page refresh.

**Acceptance Scenarios**:

1. **Given** the coordinator completes an update cycle, **When** entity states change, **Then** HA pushes the new `hass` object → panel fetches fresh data from `/hbc/api/status`.
2. **Given** no coordinator update has occurred, **When** `hass` pushes with unchanged HBC entities, **Then** the panel does NOT make a redundant fetch (debounce).

---

### Edge Cases

- What if `this.hass` is null on initial load? Fetch data on first non-null `hass` assignment.
- What if coordinator data changes but HBC entity states don't? Use a debounced fallback timer (e.g., 60s) to catch edge cases.
- What if the user is on the Plan tab when data updates? Panel should re-render the active tab correctly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The panel MUST use LitElement's `updated(changedProps)` lifecycle method to detect `hass` property changes, replacing `setInterval` polling.
- **FR-002**: The panel MUST fetch data from `/hbc/api/status` when `this.hass` changes and an HBC sensor entity has been updated.
- **FR-003**: The panel MUST debounce fetch calls to avoid redundant requests (max 1 fetch per 10 seconds).
- **FR-004**: The panel MUST include a fallback timer (60s) to catch updates not reflected in entity state changes.
- **FR-005**: The `setInterval(30s)` polling MUST be removed entirely.
- **FR-006**: The 401 retry logic from feature 015 MUST be retained as a safety net for edge cases.
- **FR-007**: The panel MUST handle `this.hass` being null gracefully during WebSocket reconnection.

### Key Entities

- **`hass`**: LitElement property set by HA framework on every state change. Contains all entity states, auth, connection info.
- **`sensor.hbc_state`**: HBC FSM state entity — changes when coordinator runs.
- **`/hbc/api/status`**: HTTP endpoint returning full coordinator data (plan, forecast, costs).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Panel recovers automatically after 2+ hours idle — zero manual refreshes needed.
- **SC-002**: Panel updates within 2 seconds of coordinator completing an update cycle.
- **SC-003**: No redundant fetches — at most 1 fetch per 10 seconds during normal operation.
- **SC-004**: `setInterval` completely removed from codebase.
- **SC-005**: All existing tests pass (no regression).
- **SC-006**: 401 retry logic still functional as fallback.
