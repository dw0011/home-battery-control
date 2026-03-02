# Feature Specification: Acquisition Cost Gate Fix

**Feature Branch**: `019-acquisition-cost-gate`  
**Created**: 2026-03-02  
**Status**: Draft  
**Input**: GitHub Issue #15 — "Acquisition cost gate allows unprofitable grid discharge"

## Problem Statement

The LP solver currently applies a single static acquisition cost value as a discharge gate for all 288 forecast steps. This value comes from the coordinator's persistence store and defaults to 0.10 c/kWh. Two problems arise:

1. **Static gate**: The same acquisition cost is applied uniformly across all 288 steps. In reality, the acquisition cost evolves as the battery charges and discharges through the simulation. A step at hour 4 (after cheap solar charging) should have a different gate value than a step at hour 1 (before any charging).

2. **Default masking**: The 0.10 c/kWh default means the gate is effectively permanently open, since all market export prices exceed 0.10 c/kWh.

## Core Mechanism

The acquisition cost gate must operate **row by row within the solver's step loop**. At each step `i`:

1. The acquisition cost at step `i` is known — it was computed from step `i-1` (or from the persisted/default value for step 0).
2. Compare the export price at step `i` against this acquisition cost.
3. If `export_price[i] < acquisition_cost[i]`, discharge to grid is unprofitable at this step — override the solver's discharge decision to SELF_CONSUMPTION.
4. When a discharge is overridden, the battery **retains** that energy. This must be reflected in the battery state for all subsequent steps — the SoC is higher than the solver computed, and the acquisition cost carries forward unchanged (no energy was sold).
5. The updated battery state and acquisition cost then feed into step `i+1`.

This is not a pre-solve gate (bounds), nor a post-solve label change. It is a **row-by-row evaluation during the sequence builder loop** with full battery state propagation when overrides occur.

## User Scenarios & Testing

### User Story 1 - Discharge Gate Uses Per-Step Acquisition Cost (Priority: P1)

As a user, I want the system to never export to the grid at a price below what the stored energy cost to acquire at that point in the forecast, so that I don't lose money on any exported kWh.

**Why this priority**: Financial protection — the current gate is effectively disabled.

**Independent Test**: When a step's export price is below the projected acquisition cost at that step, DISCHARGE_GRID must not appear.

**Acceptance Scenarios**:

1. **Given** the acquisition cost at step 40 is 18.5 c/kWh (after charging at ~9 c/kWh earlier), **When** the export price at step 40 is 14 c/kWh, **Then** the solver MUST NOT show DISCHARGE_GRID at step 40.
2. **Given** the acquisition cost at step 40 is 10 c/kWh (after cheap solar charging), **When** the export price at step 40 is 14 c/kWh, **Then** the solver MAY show DISCHARGE_GRID at step 40.
3. **Given** a discharge is overridden at step 40, **When** step 41 is evaluated, **Then** the battery SoC at step 41 reflects the retained energy (higher than the solver computed), and the acquisition cost at step 41 is unchanged from step 40.

---

### User Story 2 - Persisted Acquisition Cost Loads Correctly (Priority: P1)

As a user, I want the system to use my real historical acquisition cost from persistent storage across restarts, so that the gate is based on actual data.

**Why this priority**: The 0.10 c/kWh default renders the gate permanently open.

**Independent Test**: After restart, the acquisition cost at step 0 matches the persisted value.

**Acceptance Scenarios**:

1. **Given** persistent storage contains an acquisition cost of 18.5 c/kWh, **When** the integration loads, **Then** step 0 of the solver uses 18.5 c/kWh, not 0.10.
2. **Given** no persistent storage exists (fresh install), **When** the integration loads, **Then** step 0 uses 0.10 c/kWh as a safe default.

---

### Edge Cases

- What happens if acquisition cost is 0.0 (battery fully charged from free solar)? The gate allows export at any positive price — correct behaviour.
- What happens if a discharge override changes the battery state significantly? All subsequent steps must see the corrected SoC and acquisition cost.
- What happens if multiple consecutive discharges are overridden? Each override compounds — the battery retains more energy, SoC climbs higher, and acquisition cost remains stable.

## Requirements

### Functional Requirements

- **FR-001**: At each step `i` in the solver's sequence loop, the discharge-to-grid decision MUST be gated against the acquisition cost computed from step `i-1`.
- **FR-002**: When a discharge-to-grid is overridden (export price < acquisition cost), the battery state MUST be updated to reflect the retained energy — the SoC at step `i+1` must be higher than the solver planned.
- **FR-003**: When a discharge is overridden, the acquisition cost MUST carry forward unchanged (no energy was sold, so the weighted average doesn't change).
- **FR-004**: The initial acquisition cost at step 0 MUST come from the persisted coordinator value, falling back to 0.10 c/kWh only for fresh installs with no storage.
- **FR-005**: The plan table's "Acq. Cost" column MUST reflect the per-step acquisition cost after any overrides have been applied.
- **FR-006**: The pre-solve static gate (current L172-181 in lin_fsm.py) MUST be removed — it is replaced by the row-by-row mechanism.

## Success Criteria

### Measurable Outcomes

- **SC-001**: No DISCHARGE_GRID state appears in the plan when the export price is below the acquisition cost at that step.
- **SC-002**: After a discharge override, subsequent rows show higher SoC than the solver originally computed.
- **SC-003**: After restart with persisted data, step 0's acquisition cost matches the stored value.
