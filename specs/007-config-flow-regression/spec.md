# Feature Specification: Config Flow Options Regression

**Feature Branch**: `007-config-flow-regression`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User description: "Fix config flow regression: restore skip button in options flow control step and allow clearing existing entity selections. Add observation mode switch."

## User Scenarios & Testing

### User Story 1 - Toggle Observation Mode (Priority: P1)

A user wants to stop HBC from issuing Powerwall commands without losing their script configuration. They open Options → Control and toggle "Observation Mode" on. The solver still runs and produces plans visible on the dashboard, but the executor skips all script calls. When the user toggles observation mode off, execution resumes using the existing configured scripts — no re-entry needed.

**Why this priority**: Users currently have no way to pause execution without disabling the entire integration, making troubleshooting and price-debugging impossible.

**Independent Test**: Toggle observation mode on, trigger a solver run, verify no scripts are called. Toggle off, trigger again, verify scripts execute.

**Acceptance Scenarios**:

1. **Given** HBC is configured with 4 control scripts, **When** user enables observation mode via Options → Control, **Then** the executor does not call any scripts, but the solver continues producing plans.
2. **Given** observation mode is enabled, **When** user disables it, **Then** the executor resumes calling scripts using the previously configured entities.
3. **Given** observation mode is enabled, **When** user opens Options → Control, **Then** the toggle defaults to checked and all script selectors still show their configured values.

---

### User Story 2 - Clear Individual Script Entities (Priority: P2)

A user wants to remove a single script (e.g. discharge) while keeping the others. They open Options → Control, clear the entity selector for that script, and submit. The cleared script is removed from the config entry; the remaining scripts continue to operate.

**Why this priority**: Allows granular control over which scripts are active.

**Independent Test**: Set a script, re-open Options, clear it, submit, verify it is removed from config data.

**Acceptance Scenarios**:

1. **Given** a script entity is configured, **When** user clears the entity selector and submits, **Then** that script key is removed from the config entry data.

---

### User Story 3 - Friendly Labels Displayed (Priority: P3)

All form fields in the Options → Control step display human-readable labels instead of raw config key names (e.g. "Script: Charge from Grid" not "script_charge").

**Why this priority**: Cosmetic but necessary for usable UI.

**Independent Test**: Open Options → Control and visually confirm all labels are human-readable.

**Acceptance Scenarios**:

1. **Given** user opens Options → Control, **Then** every field shows a friendly label from the translation files.

---

### Edge Cases

- What happens when observation mode is on and all scripts are also cleared? Observation mode takes precedence — no commands are issued. If user later toggles observation off, still no commands because scripts are absent too.
- What happens when observation mode is off but no scripts are configured? Same as today — executor has no scripts to call, effectively observation mode by default.

## Requirements

### Functional Requirements

- **FR-001**: Options flow Control step MUST include an "Observation Mode" boolean toggle, persisted in the config entry data.
- **FR-002**: When observation mode is enabled, the executor MUST NOT call any scripts, regardless of what scripts are configured.
- **FR-003**: Observation mode MUST NOT modify or clear any configured script entity references.
- **FR-004**: Users MUST be able to clear individual optional entity selectors back to empty.
- **FR-005**: When an entity selector is cleared, the system MUST remove that key from config entry data (not store an empty string).
- **FR-006**: The `translations/en.json` and `strings.json` options control section MUST include labels for all fields shown in the form: observation mode toggle, 4 script selectors, panel admin only.
- **FR-007**: The 4 script controls are: Charge from Grid, Stop Charging, Discharge to Grid, Stop Discharging. No other control entities appear in this step.

### Key Entities

- **Config Entry Data**: The persisted dictionary of configuration keys. Script keys are `script_charge`, `script_charge_stop`, `script_discharge`, `script_discharge_stop`.
- **observation_mode**: A persisted boolean in the config entry (default: `False`). When `True`, the executor suppresses all script execution.

## Success Criteria

### Measurable Outcomes

- **SC-001**: User can toggle observation mode on/off via Options → Control and it persists across restarts.
- **SC-002**: With observation mode on, zero scripts are called even when all 4 are configured.
- **SC-003**: Toggling observation mode off resumes script execution without re-entering script entities.
- **SC-004**: Cleared entity selections result in the key being absent from config data.
- **SC-005**: All form fields display human-readable labels.
- **SC-006**: All existing automated tests pass without modification.

## Assumptions

- The executor (`execute.py`) already handles missing script keys gracefully via `.get()` returning `None`.
- The Panel Admin Only toggle is an existing field that should remain in the control step.
- The initial config flow (`ConfigFlow.async_step_control`) is not modified by this feature.
