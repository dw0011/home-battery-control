# Feature Specification: Debug Replay Snapshot

**Feature Branch**: `027-debug-replay`  
**Created**: 2026-03-06  
**Status**: Draft  
**Input**: Solver issues need offline reproduction from user feedback. Add solver inputs to API and auto-capture on state transitions.

## User Scenarios & Testing

### User Story 1 - Capture Solver Snapshot via API (Priority: P1)

As a user who sees a suspicious solver decision on the dashboard, I want to run a single console command in Home Assistant to capture the exact solver inputs that produced it, so I can send the JSON to a developer for offline replay.

**Why this priority**: This is the primary debug workflow. The user already knows how to run the console fetch command. Adding solver inputs to the existing API response requires zero new UX.

**Independent Test**: Call `/hbc/api/status`, verify `solver_snapshot` field contains all 4 input arrays plus battery config and acquisition cost.

**Acceptance Scenarios**:

1. **Given** the solver has run at least once, **When** I fetch `/hbc/api/status`, **Then** the response includes a `solver_snapshot` object containing `price_buy[288]`, `price_sell[288]`, `load_kwh[288]`, `pv_kwh[288]`, battery config, acquisition_cost, and the current result state
2. **Given** the solver has NOT run yet, **When** I fetch `/hbc/api/status`, **Then** `solver_snapshot` is null
3. **Given** a captured snapshot JSON, **When** loaded by `test_solver_replay.py`, **Then** it produces the same FSM result state and plan

---

### User Story 2 - Auto-Capture State Transitions (Priority: P2)

As a developer debugging intermittent issues, I want the system to automatically save a snapshot whenever the FSM result state changes between ticks, so I never lose transient issues.

**Why this priority**: Some solver issues are transient — they appear for one tick then vanish. Auto-capture ensures we catch them even if the user doesn't react in time.

**Independent Test**: Trigger a state change in tests, verify the ring buffer contains the snapshot.

**Acceptance Scenarios**:

1. **Given** the FSM result state changes from SELF_CONSUMPTION to CHARGE_GRID, **When** the coordinator completes the update cycle, **Then** a snapshot is added to the ring buffer
2. **Given** the ring buffer has 10 entries, **When** a new state change occurs, **Then** the oldest entry is evicted and the new one added
3. **Given** the FSM result state does NOT change between ticks, **When** the coordinator completes the update cycle, **Then** no new snapshot is added
4. **Given** I fetch `/hbc/api/status`, **Then** the response includes `state_transitions` array containing the last 10 auto-captured snapshots

---

### Edge Cases

- What happens on integration restart? → Ring buffer starts empty, rebuilds from live operation
- What happens if the solver errors? → No snapshot captured for ERROR state (no useful inputs)
- How large is the payload? → ~30KB for 1 snapshot (4 × 288 floats), ~300KB for 10 in buffer. Acceptable for API response
- What about no_import_steps? → Included in snapshot, serialised as a list of integers

## Requirements

### Functional Requirements

- **FR-001**: The `/hbc/api/status` response MUST include a `solver_snapshot` object containing the most recent solver inputs (SolverInputs arrays + battery config + acquisition_cost + result state/limit_kw/target_soc)
- **FR-002**: The coordinator MUST maintain an in-memory ring buffer of the last 10 state-transition snapshots
- **FR-003**: A state-transition snapshot MUST be captured when `fsm_result.state != previous_state` (comparing to the state from the prior tick)
- **FR-004**: The `/hbc/api/status` response MUST include a `state_transitions` array containing all ring buffer entries, newest first
- **FR-005**: Each snapshot MUST include a UTC ISO-8601 timestamp of when it was captured
- **FR-006**: The snapshot format MUST be directly loadable by `test_solver_replay.py` for offline reproduction
- **FR-007**: The ring buffer is in-memory only — no persistent storage required

### Key Entities

- **SolverSnapshot**: timestamp, solver_inputs (4 arrays + no_import_steps), battery_config (soc, capacity, charge_rate_max, inverter_limit, rte, reserve_soc), acquisition_cost, result (state, limit_kw, target_soc)
- **Ring Buffer**: Fixed-size deque of SolverSnapshot, size 10, evicts oldest on overflow

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every `/hbc/api/status` response includes `solver_snapshot` (not null after first tick)
- **SC-002**: A captured snapshot can be loaded into `test_solver_replay.py` and reproduces the same result state
- **SC-003**: The ring buffer correctly captures state transitions and limits to 10 entries
- **SC-004**: API payload size increases by no more than 30KB for the snapshot, 300KB for the transition buffer
