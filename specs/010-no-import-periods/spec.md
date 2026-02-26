# Feature Specification: No-Import Periods (Demand Charge Windows)

**Feature Branch**: `010-no-import-periods`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: GitHub Issue #4 — User requests configuration for demand charge windows (NSW 3pm-9pm) where HBC should never import from the grid.

## Problem Statement

Some electricity tariffs include demand charges calculated from the highest grid import during specific peak windows (e.g., 3pm-9pm in NSW). If the LP optimizer schedules grid charging during these windows, it can incur massive demand charge penalties that outweigh the import savings. Users need a way to define time periods where grid import is absolutely forbidden.

## User Scenarios & Testing

### User Story 1 - Configure No-Import Periods (Priority: P1)

A user navigates to Settings → Integrations → HBC → Configure → Control Services and enters one or more time windows (e.g., "15:00-21:00") where grid import must be blocked. The optimizer respects these windows and never schedules grid charging during them.

**Acceptance Scenarios**:

1. **Given** user enters "15:00-21:00" as a no-import period, **When** the LP solver runs, **Then** no grid import is scheduled between 3pm and 9pm local time.
2. **Given** user enters multiple periods "06:00-09:00,15:00-21:00", **When** the LP solver runs, **Then** grid import is blocked during both windows.
3. **Given** no periods are configured (empty), **When** the LP solver runs, **Then** behavior is unchanged from current.

---

### User Story 2 - Plan Table Shows Blocked Periods (Priority: P2)

The user views the Plan tab on the HBC dashboard. Steps that fall within a no-import period show zero grid import, and the solver works around these constraints using battery discharge and solar.

**Acceptance Scenarios**:

1. **Given** a no-import period from 15:00-21:00, **When** the plan table is displayed, **Then** all rows in that window show zero or negative Net Grid (no import).

---

### Edge Cases

- **Midnight-spanning windows**: e.g., "22:00-06:00" — the window wraps around midnight.
- **Empty or invalid format**: gracefully ignored with a log warning.
- **Infeasible LP**: if blocking import makes the problem infeasible (battery too small to cover load), the solver must still return a valid result — it should discharge to zero SoC and accept grid import as a last resort. This is handled by the solver's inequality constraint `g[i] >= energy[i]` which forces the minimum import needed.

## Requirements

### Functional Requirements

- **FR-001**: A new config option `CONF_NO_IMPORT_PERIODS` must accept a comma-separated list of `HH:MM-HH:MM` time ranges in local time.
- **FR-002**: The LP solver must set `g[i]` upper bound to `0.0` for all 5-minute steps that fall within a configured no-import period.
- **FR-003**: The feature must be configurable via the Options flow (Control step).
- **FR-004**: Empty/missing config means no import restrictions (backward compatible).
- **FR-005**: Midnight-spanning periods (e.g., "22:00-06:00") must be handled correctly.

### Non-Functional Requirements

- **NFR-001**: No new dependencies.
- **NFR-002**: All existing tests must continue to pass.

## Success Criteria

- **SC-001**: LP solver produces zero grid import during configured no-import periods.
- **SC-002**: Plan table reflects blocked periods.
- **SC-003**: All automated tests pass (existing + new).
- **SC-004**: Backward compatible — no import restrictions when config is empty.
