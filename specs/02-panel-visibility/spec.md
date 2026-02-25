# Feature Specification: Configurable Panel Visibility

**Feature Branch**: `02-panel-visibility`  
**Created**: 2026-02-25  
**Status**: Draft  
**Input**: User description: "The panel only — users may choose to make user-visible, not admin."

## User Scenarios & Testing

### User Story 1 - Admin Configures Panel to Be Visible to All Users (Priority: P1)

An HA admin opens the HBC integration's Options flow and sets "Panel Visibility" to "All Users". After saving and reloading the integration, all authenticated HA users (not just admins) can see the HBC entry in the sidebar and access the panel.

**Why this priority**: Core feature — the entire point of this change is to let admins choose who sees the panel.

**Independent Test**: Change the option to "All Users", reload integration, open a non-admin HA session — sidebar entry is visible and panel loads.

**Acceptance Scenarios**:

1. **Given** panel visibility is set to "Admin Only" (default), **When** admin changes it to "All Users" in Options, **Then** non-admin users see the HBC sidebar entry after reload.
2. **Given** panel visibility is set to "All Users", **When** a non-admin user clicks the HBC sidebar entry, **Then** the panel loads and displays data.

---

### User Story 2 - Admin Restricts Panel Back to Admin-Only (Priority: P1)

An HA admin who previously set visibility to "All Users" changes it back to "Admin Only". After reload, non-admin users no longer see the HBC sidebar entry.

**Why this priority**: Equal importance — must be reversible to prevent accidental exposure.

**Independent Test**: Toggle option back to "Admin Only", reload, verify non-admin session no longer shows sidebar entry.

**Acceptance Scenarios**:

1. **Given** panel visibility is "All Users", **When** admin changes it to "Admin Only" in Options, **Then** non-admin users no longer see the HBC sidebar entry after reload.

---

### User Story 3 - Default Behaviour After Fresh Install (Priority: P2)

A user installs the HBC integration for the first time. The panel defaults to "Admin Only" visibility without requiring explicit configuration.

**Why this priority**: Safety — default secure posture; existing installations must not change behaviour.

**Independent Test**: Fresh install of integration — only admin users see the sidebar entry.

**Acceptance Scenarios**:

1. **Given** a fresh installation of HBC, **When** no visibility option has been configured, **Then** only admin users see the HBC sidebar entry (same as current behaviour).

---

### Edge Cases

- What happens when the option is changed but HA is not reloaded/restarted? The visibility change takes effect on the next integration reload.
- What happens to existing installations upgrading? The default remains "Admin Only" — no change in behaviour.
- API endpoints remain admin-only regardless of panel visibility setting. Only the sidebar entry visibility is controlled.

## Requirements

### Functional Requirements

- **FR-001**: The HBC Options flow MUST include a "Panel Visibility" selector with two choices: "Admin Only" (default) and "All Users".
- **FR-002**: When set to "Admin Only", the panel registration MUST use `require_admin=True`.
- **FR-003**: When set to "All Users", the panel registration MUST use `require_admin=False`.
- **FR-004**: The default value for panel visibility MUST be "Admin Only" so existing installations are unaffected.
- **FR-005**: The API endpoints (`/hbc/api/*`) MUST remain `requires_auth=True` regardless of panel visibility setting.
- **FR-006**: Changing the option MUST take effect after integration reload (via Options save or HA restart).

### Key Entities

- **Panel Visibility Option**: A config option stored in the integration's Options data, with values "admin_only" or "all_users".

## Success Criteria

### Measurable Outcomes

- **SC-001**: Admin can toggle panel visibility via Options flow without editing code or YAML.
- **SC-002**: Default behaviour matches current admin-only setting — no regression.
- **SC-003**: API endpoints remain secured regardless of panel visibility setting.
- **SC-004**: All existing unit tests pass after changes, with new tests covering the visibility toggle.

## Assumptions

- HA's `async_register_built_in_panel` accepts `require_admin` as a boolean parameter.
- The Options flow already exists and accepts new fields.
- Integration reload re-executes `async_setup_entry`, which re-registers the panel with the updated setting.
