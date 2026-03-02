# Feature Specification: Acquisition Cost Gate Fix

**Feature Branch**: `019-acquisition-cost-gate`  
**Created**: 2026-03-02  
**Status**: Draft  
**Input**: GitHub Issue #15 — "Acquisition cost gate allows unprofitable grid discharge"

## User Scenarios & Testing

### User Story 1 - Discharge Gate Respects Acquisition Cost (Priority: P1)

As a user, I want the system to never export to the grid at a price below what the stored energy cost to acquire, so that I don't lose money on every kWh exported.

**Why this priority**: This is a financial protection mechanism. Without it, the system actively loses money by selling cheap.

**Independent Test**: When the export price at any future step is below the projected acquisition cost at that step, the solver must not schedule DISCHARGE_GRID.

**Acceptance Scenarios**:

1. **Given** the projected acquisition cost at step `i` is 18.5 c/kWh, **When** the export price at step `i` is 14 c/kWh, **Then** the solver MUST NOT schedule DISCHARGE_GRID at step `i`.
2. **Given** the projected acquisition cost at step `i` is 10 c/kWh, **When** the export price at step `i` is 40 c/kWh, **Then** the solver MAY schedule DISCHARGE_GRID at step `i`.
3. **Given** acquisition cost drops through the simulation due to cheap charging, **When** the export price exceeds the new projected acquisition cost at a later step, **Then** DISCHARGE_GRID becomes available at that later step.

---

### User Story 2 - Persisted Acquisition Cost Loads Correctly (Priority: P1)

As a user, I want the system to use my real historical acquisition cost from persistent storage across restarts, so that the gate is based on actual data, not a meaningless default.

**Why this priority**: The 0.10 c/kWh default renders the gate permanently open since all export prices exceed it.

**Independent Test**: After restart, the acquisition cost used by the solver matches the persisted value, not the default.

**Acceptance Scenarios**:

1. **Given** persistent storage contains an acquisition cost of 18.5 c/kWh, **When** the integration loads, **Then** the solver receives 18.5 c/kWh as its acquisition cost, not 0.10.
2. **Given** no persistent storage exists (fresh install), **When** the integration loads, **Then** the solver receives 0.10 c/kWh as a safe default.
3. **Given** the integration has been running and charging, **When** the coordinator updates acquisition cost, **Then** the updated value is persisted to storage.

---

### Edge Cases

- What happens if acquisition cost is 0.0 (battery fully charged from solar with no grid cost)? The gate should allow export at any positive price.
- What happens if acquisition cost exceeds ALL future export prices? The solver should never discharge to grid — SELF_CONSUMPTION only.
- What happens if acquisition cost changes mid-simulation due to simulated charging? The gate must reflect the updated per-step value.

## Requirements

### Functional Requirements

- **FR-001**: The LP solver MUST compare the export price at each step against the **projected acquisition cost at that step**, not a single static value.
- **FR-002**: The projected acquisition cost at each step MUST account for simulated charging that occurs in earlier steps of the same solver run.
- **FR-003**: The `raw_acquisition_cost` passed to the solver MUST be the persisted coordinator value when available, falling back to 0.10 c/kWh only for fresh installs with no storage.
- **FR-004**: The persisted acquisition cost MUST survive integration restarts via the HA `.storage` mechanism.
- **FR-005**: The plan table's "Acq. Cost" column and the discharge gate MUST use the same per-step projected value (consistency between display and behaviour).

## Success Criteria

### Measurable Outcomes

- **SC-001**: No DISCHARGE_GRID state appears in the plan when the export price is below the projected acquisition cost at that step.
- **SC-002**: After restart with persisted data, the solver's acquisition cost matches the stored value (verified via diagnostic log).
- **SC-003**: The plan table's Acq. Cost column matches the value used by the discharge gate at each step.
