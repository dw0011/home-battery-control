# Feature Specification: Unify FSM and UI Data Architecture

**Feature Branch**: `028-unify-fsm-ui-data`
**Created**: 2026-03-07
**Status**: Phase 1: Approved
**Input**: User description: "Refactor _build_diagnostic_plan_table to read import_price and net_grid directly out of the solver's sequence dictionary so the Math Brain and UI Formatting Engine share the exact same array values. Ensure it overwrites row 0 values with actual current prices for import and export."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Plan Table Display (Priority: P1)

As a user monitoring the house battery control dashboard, I want the forecast Plan Table to exactly reflect the mathematical decisions made by the solver, so that I can easily understand why the system is choosing to charge, discharge, or wait at any given 5-minute interval.

**Why this priority**: It is critical that users trust the system. Misalignment between the UI display and the underlying solver math causes confusion and breaks trust, as the system will appear to be acting irrationally.

**Independent Test**: The UI Plan Table's prices and grid data must strictly match the data inside the `hbc_debug_` snapshot `plan` array at every step.

**Acceptance Scenarios**:

1. **Given** the solver decides to charge from the grid at a live price override of $0.02, **When** the UI Plan Table is rendered, **Then** Row 0 must display the actual live import price ($0.02) and not the general forecast price ($0.09).
2. **Given** the solver decides to wait and not export because the live sell price is negative (e.g., -$-0.01) despite a positive future forecast, **When** the UI Plan Table is rendered, **Then** Row 0 must show the live export price (-$-0.01).
3. **Given** any future projection step (row 1+), **When** viewing the Plan Table, **Then** the import price, export price, and net grid flow must exactly match the internal optimization variables for that step.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST populate the UI Plan Table using the exact `import_price`, `export_price`, and `net_grid` values from the solver's output sequence array for rows 1 and beyond.
- **FR-002**: The system MUST override the `import_price` and `export_price` in Row 0 of the UI Plan Table with the current, live sensor values.
- **FR-003**: The formatting engine MUST NOT independently recalculate interval costs, grid flow, or active pricing from the raw timeline arrays if the solver has already provided these values in its output sequence.
- **FR-004**: System MUST ensure that row 0 strictly represents the "now" state that the solver acted upon during its current execution tick.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% data parity between the LP solver's internal `sequence` output variables and the rendered UI Plan Table for pricing and net grid flow.
- **SC-002**: Zero user reports of "irrational system behavior" caused by UI display desynchronization.
