# Feature Specification: Panel Navigation Fix (iOS)

**Feature Branch**: `008-panel-navigation-fix`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: GitHub Issue #3: "When using the Home Assistant Mobile APP (iOS) and you select HBC on the menu; HBC completely hijacks the app, no way to get out of it, even force closing the app brings you back to HBC dashboard/plan with no way of getting out of it."

## User Scenarios & Testing

### User Story 1 - Navigate Away from HBC Panel on iOS (Priority: P1)

A user opens the HBC panel from the HA sidebar on the iOS mobile app. They view the dashboard, then want to navigate somewhere else. They tap a menu/back button at the top of the HBC panel, which reveals the sidebar or navigates back to the HA overview, just like any other HA panel.

**Why this priority**: The panel currently traps users with no escape route on iOS, requiring force-close and restart.

**Independent Test**: Open HBC on the iOS HA app, verify a menu/back button is visible, tap it, confirm the sidebar appears or user returns to HA.

**Acceptance Scenarios**:

1. **Given** user opens HBC panel on iOS HA app, **When** the panel renders, **Then** a menu/back button is visible at the top of the screen.
2. **Given** user is viewing HBC panel on iOS, **When** they tap the menu/back button, **Then** the HA sidebar appears or they navigate back to the previous page.
3. **Given** user is viewing HBC panel on desktop, **When** the sidebar is already visible, **Then** the menu button acts as a sidebar toggle (consistent with other HA panels).

---

### User Story 2 - Panel Does Not Override HA App State (Priority: P2)

After force-closing and reopening the iOS HA app, the user should not be trapped back on the HBC panel. The HA app should restore to a navigable state.

**Why this priority**: Force-closing currently doesn't escape the trap because HA restores last-viewed panel.

**Independent Test**: This is inherently handled by User Story 1 — if the back button works, force-close/reopen will land on a navigable HBC page.

**Acceptance Scenarios**:

1. **Given** user force-closed the HA app while on HBC, **When** they reopen the app, **Then** HBC renders with the menu/back button visible and functional.

---

### Edge Cases

- What if the sidebar is already visible (desktop)? The menu button toggles the sidebar, consistent with HA's built-in behavior.
- What if the user has `narrow` mode (mobile)? The `narrow` property from HA indicates mobile layout — the button should trigger `history.back()` or fire an HA event to show the sidebar.

## Requirements

### Functional Requirements

- **FR-001**: The HBC panel MUST display a Home Assistant-style toolbar at the top of the panel.
- **FR-002**: The toolbar MUST include a menu/back icon button on the left side that integrates with HA's sidebar navigation.
- **FR-003**: On mobile/narrow layouts, the menu button MUST either navigate back or reveal the HA sidebar.
- **FR-004**: On desktop layouts, the menu button MUST toggle the sidebar visibility.
- **FR-005**: The panel title ("House Battery Control") MUST appear in the toolbar.
- **FR-006**: The existing Dashboard/Plan tab buttons MUST remain functional and positioned below or within the toolbar.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users on the iOS HA app can navigate away from HBC within a single tap.
- **SC-002**: Force-closing the iOS app and reopening does not trap the user on HBC.
- **SC-003**: Desktop sidebar toggle behavior is preserved.
- **SC-004**: All existing automated tests pass.

## Assumptions

- HA custom panels receive `hass`, `narrow`, and `panel` properties automatically from the HA frontend.
- The `narrow` boolean indicates mobile/compact layout.
- HA fires a `hass-toggle-menu` event when custom panels want to toggle the sidebar.
- The panel is a LitElement custom element registered via `panel_custom`.
