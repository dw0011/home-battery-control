# Feature Specification: Single State Source

**Feature Branch**: `026-single-state-source`  
**Created**: 2026-03-06  
**Status**: Draft  
**Input**: BUG-026 — Executor state and plan table row 0 state are derived from independent classification paths, causing mismatch

## User Scenarios & Testing

### User Story 1 - Executor State Matches Plan Row 0 (Priority: P1)

As a user monitoring the HBC dashboard, I expect the inverter command (charge/discharge/self-consumption) to always match what the plan table shows for the current time step. When the plan shows SELF_CONSUMPTION, the inverter must not be charging or discharging to grid.

**Why this priority**: This is a correctness bug. A mismatch causes real energy costs — the inverter charges at the wrong time or discharges when it shouldn't.

**Independent Test**: Run the solver with known inputs and verify that the FSM result state matches the first row of the future_plan sequence.

**Acceptance Scenarios**:

1. **Given** the LP solver produces a plan where step 0 state is SELF_CONSUMPTION, **When** the FSM result is returned, **Then** the result state must be SELF_CONSUMPTION
2. **Given** the LP solver produces a plan where step 0 state is CHARGE_GRID, **When** the FSM result is returned, **Then** the result state must be CHARGE_GRID
3. **Given** the LP solver produces a plan where step 0 state is DISCHARGE_GRID, **When** the FSM result is returned, **Then** the result state must be DISCHARGE_GRID
4. **Given** the LP solver produces an empty plan, **When** the FSM result is returned, **Then** the result state must be SELF_CONSUMPTION (safe default)

---

### Edge Cases

> **Note**: The limit_kw calculation via `target_delta_kwh * 12` is correct and remains unchanged.
> The executor already deduplicates commands via `last_executed_state` check (execute.py L87-89).

- What happens when the LP's SoC delta is positive (implying charge) but the plan row 0 state is SELF_CONSUMPTION because PV covers it? → Must follow plan row 0 (SELF_CONSUMPTION)
- What happens when plan sequence is empty? → Return SELF_CONSUMPTION with limit_kw=0.0
- What happens when the acquisition cost gate overrides step 0 from DISCHARGE_GRID to SELF_CONSUMPTION? → Must follow the gated state

## Requirements

### Functional Requirements

- **FR-001**: The FSM result state MUST be derived from `sequence[0]["state"]`, not from an independent classification of the SoC delta
- **FR-002**: The FSM result limit_kw calculation (`target_delta_kwh * 12`) is correct and MUST NOT change
- **FR-003**: If `sequence` is empty or None, the FSM MUST return SELF_CONSUMPTION with limit_kw=0.0
- **FR-004**: The acquisition cost gate (existing FR-001 from spec 025) MUST still apply to sequence[0] before it is used as the result state
- **FR-005**: All existing tests MUST continue to pass — this is a bug fix, not a behavioral change for correct inputs

### Key Entities

- **FSMResult**: The output of `calculate_next_state` — contains `state`, `limit_kw`, `reason`, `target_soc`, `projected_cost`, `future_plan`
- **sequence**: The 288-step plan built inside `propose_state_of_charge` — each step has `state`, `target_soc`, `net_grid`, `load`, `pv`, prices
- **Executor**: `PowerwallExecutor` — receives `fsm_result.state` and `fsm_result.limit_kw` to command the inverter

## Success Criteria

### Measurable Outcomes

- **SC-001**: For every test scenario, the FSM result state exactly matches `future_plan[0]["state"]` — zero mismatches
- **SC-002**: All existing 205 tests pass without modification (no regression)
- **SC-003**: The independent SoC-delta state classification (L382-414) is replaced by reading `sequence[0]["state"]` — only one state source exists
- **SC-004**: A targeted test explicitly verifies state agreement between FSM result and plan row 0 across multiple boundary conditions
