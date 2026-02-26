# Feature Specification: Executor Command Deduplication Fix

**Feature Branch**: `009-executor-command-dedup`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User reported that commands repeat unnecessarily, but also fail to fire when they should (e.g., after observation mode toggle-off or HA restart).

## Problem Statement

The `PowerwallExecutor.apply_state()` method tracks "last requested state" and "last executed state" as a single variable (`_last_state`). This conflation causes two failure modes:

1. **Observation mode exit bug**: When observation mode is active, `_last_state` is updated (line 70) BEFORE the observation mode gate (line 75). When the user later disables observation mode, the dedup check at line 66 sees the state as unchanged and skips execution. The battery never receives the command.

2. **Unnecessary re-calling**: The coordinator calls `apply_state()` every update cycle (~30s or on telemetry change). If the state hasn't changed, we should NOT re-send the service call. This works today but only because of the dedup check.

3. **HA restart gap**: After HA restarts, `_last_state` is `None`. The first call always executes (good). But if the battery was already in the correct state, this sends a redundant command (acceptable, since we can't know the battery's actual state).

The core requirement: **track what was last COMMANDED separately from what was last REQUESTED**.

## User Scenarios & Testing

### User Story 1 - State Deduplication (Priority: P1)

The coordinator calls `apply_state(IDLE, 0.0)` every 30 seconds while the FSM recommends IDLE. The executor should send the IDLE command once and suppress subsequent identical calls.

**Acceptance Scenarios**:

1. **Given** executor has sent IDLE, **When** apply_state(IDLE, 0.0) is called again, **Then** no service call is made and apply_count does NOT increment.
2. **Given** executor has sent IDLE, **When** apply_state(CHARGE_GRID, 6.3) is called, **Then** the charge script IS called and apply_count increments.

---

### User Story 2 - Observation Mode Exit Triggers Execution (Priority: P1)

The user has observation mode ON. The FSM recommends CHARGE_GRID. The executor tracks the request but does not call scripts. The user then disables observation mode. The next coordinator cycle calls `apply_state(CHARGE_GRID, 6.3)` — the executor MUST execute because no command has actually been sent for this state.

**Acceptance Scenarios**:

1. **Given** observation mode is ON and apply_state(CHARGE_GRID, 6.3) is called, **When** observation mode is toggled OFF, **Then** the next call to apply_state(CHARGE_GRID, 6.3) DOES execute.
2. **Given** observation mode is ON, **When** multiple state requests are suppressed, **Then** apply_count still tracks requests but a separate executed_count tracks actual commands.

---

### User Story 3 - HA Restart Recovery (Priority: P2)

After HA restarts, the executor has no memory of previous state. The first `apply_state()` call should always execute.

**Acceptance Scenarios**:

1. **Given** executor is freshly constructed, **When** apply_state(IDLE, 0.0) is called, **Then** the IDLE commands ARE executed (even if the battery is already idle).

---

## Requirements

### Functional Requirements

- **FR-001**: The executor MUST track "last executed state" (`_last_executed_state`) separately from "last requested state" (`_last_state`).
- **FR-002**: Deduplication MUST compare against `_last_executed_state`, not `_last_state`.
- **FR-003**: `_last_executed_state` MUST only be updated AFTER successful command execution.
- **FR-004**: When observation mode suppresses execution, `_last_executed_state` MUST NOT be updated.
- **FR-005**: The `last_state` property MUST continue to return the last requested state (for dashboard display).
- **FR-006**: A new `last_executed_state` property SHOULD be available for diagnostics.

### Non-Functional Requirements

- **NFR-001**: No new dependencies. Pure Python logic change.
- **NFR-002**: All existing tests must continue to pass.

## Edge Cases

- **Observation mode ON, same state repeated**: `_last_state` updates for dashboard, `_last_executed_state` stays stale, dedup won't block when mode toggles off.
- **Limit change only**: If state is same but limit changes (e.g., CHARGE_GRID at 5.0 then 6.3), the executor should re-execute. Current dedup already handles this via limit comparison — keep this behaviour but compare against `_last_executed_limit`.
- **HA restart**: `_last_executed_state` starts as None, first call always executes.

## Success Criteria

- **SC-001**: Observation mode toggle-off triggers immediate execution on next `apply_state()` call.
- **SC-002**: Same-state repeated calls with no observation mode change are deduplicated.
- **SC-003**: All 134+ existing tests pass.
- **SC-004**: New tests cover the observation mode exit scenario.
