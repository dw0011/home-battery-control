# Feature Specification: Acquisition Cost Tracker Fix

**Feature Branch**: `025-acq-cost-tracker-fix`  
**Created**: 2026-03-05  
**Status**: Draft  
**Input**: User description: "Remove redundant coordinator acquisition cost tracker — use solver plan value instead"

## Background

The coordinator (`coordinator.py`) maintains two independent acquisition cost computations:

1. **Coordinator tracker** (L612-634): A weighted average updated every update cycle (~30s) using `future_plan[0]` values and 5-minute energy assumptions. This value is stored in `self.acquisition_cost` and persisted to `.storage/house_battery_control.cost_data`.

2. **Solver tracker** (`lin_fsm.py` L227-285): The LP solver's internal `running_cost` which starts from `terminal_valuation` and is updated step-by-step using precise solver variables. This value appears in each `future_plan` entry as `"acquisition_cost"`.

**Bug**: The coordinator tracker (1) over-counts energy because it runs every ~30 seconds but assumes each run represents a full 5-minute interval. Over time this dilutes `self.acquisition_cost` toward zero. The API returns this buggy value while the plan table displays the correct solver value.

**Impact**: The dashboard stat card "Acq Cost c/kWh" shows `0.00` while plan table rows correctly show ~13.5 c/kWh.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Dashboard Displays Correct Acquisition Cost (Priority: P1)

As a system operator I want the dashboard stat card to display the same acquisition cost as the plan table row 0 so that I can trust the displayed value for export profitability decisions.

**Why this priority**: The current display of 0.00 c/kWh is misleading and could cause incorrect manual overrides.

**Independent Test**: Verify that the top-level `acquisition_cost` in the API response matches `plan[0]["Acq. Cost"]` to within rounding tolerance.

**Acceptance Scenarios**:

1. **Given** the solver produces a plan with row-0 acquisition_cost of 13.5c, **When** the dashboard loads, **Then** the stat card shows `13.50` (not `0.00`).
2. **Given** no future plan exists (solver error), **When** the dashboard loads, **Then** the stat card falls back to the stored `self.acquisition_cost` value.

---

### User Story 2 — Remove Redundant Tracker Code (Priority: P1)

As a maintainer I want the redundant coordinator-level acquisition cost tracker removed so that there is one authoritative source of truth and no divergent values.

**Why this priority**: Two independent trackers computing different values is a maintenance hazard and the source of this bug.

**Independent Test**: Verify that the coordinator no longer contains the weighted average computation at the current L612-634 block, and that all tests pass.

**Acceptance Scenarios**:

1. **Given** the coordinator update cycle runs, **When** `self.acquisition_cost` is set, **Then** it is sourced from `future_plan[0].get("acquisition_cost")` (solver value), not from an independent weighted average.
2. **Given** the coordinator update cycle runs with no plan, **When** `self.acquisition_cost` is set, **Then** it retains its previous value (no reset to 0).

---

### User Story 3 — Storage Persistence Uses Solver Value (Priority: P2)

As a system operator I want the persisted acquisition cost to use the solver's value so that restarts restore the correct value.

**Why this priority**: After restart, the stored value seeds the solver's `terminal_valuation`. A stored value of 0.0004 produces incorrect terminal valuations.

**Independent Test**: Verify the `.storage` file contains the solver's acquisition_cost after a coordinator tick.

**Acceptance Scenarios**:

1. **Given** the solver produces acquisition_cost of 13.5c, **When** the coordinator persists cost data, **Then** the stored `acquisition_cost` is 13.5c (not the old tracker's value).

---

### Edge Cases

- What happens when `future_plan` is empty or `None`? → `self.acquisition_cost` retains previous value.
- What happens when `future_plan[0]` has no `"acquisition_cost"` key? → Falls back to `self.acquisition_cost`.
- What happens on first boot with no storage file? → `self.acquisition_cost` defaults to 0.10 c/kWh (existing behaviour preserved).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The coordinator MUST set `self.acquisition_cost` from `future_plan[0].get("acquisition_cost")` after each successful solver run.
- **FR-002**: The coordinator MUST NOT independently compute acquisition cost via a weighted average tracker.
- **FR-003**: The data return dict's `"acquisition_cost"` field MUST reflect the solver's plan row-0 value when available.
- **FR-004**: If `future_plan` is empty or missing, `self.acquisition_cost` MUST retain its previous value (no reset).
- **FR-005**: Persistent storage MUST save the solver-sourced `self.acquisition_cost`, not a redundantly computed value.
- **FR-006**: The cumulative cost tracker (`self.cumulative_cost`) MUST be preserved unchanged — only the acquisition cost tracker is removed.

### Key Entities

- **`self.acquisition_cost`**: Coordinator-level acquisition cost in c/kWh. Currently: buggy tracker. After fix: sourced from solver plan.
- **`future_plan[0]["acquisition_cost"]`**: Solver's authoritative acquisition cost at time step 0, computed from `terminal_valuation` and step-0 charging.
- **`.storage/house_battery_control.cost_data`**: Persistent storage for cumulative and acquisition costs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dashboard stat card displays acquisition cost ≥ 0.01 c/kWh when the solver produces a valid plan (not 0.00).
- **SC-002**: API response `acquisition_cost` matches `plan[0]["Acq. Cost"]` to within 0.01 c/kWh.
- **SC-003**: Coordinator code contains zero independent weighted-average acquisition cost computation.
- **SC-004**: All existing tests pass with no regressions.
