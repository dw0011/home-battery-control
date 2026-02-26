# Feature Specification: Fix Cost Persistence

**Feature Branch**: `001-fix-cost-persistence`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User description: "Acquisition cost does not seem to be persistent across restarts as well as cumulative cost."

## User Scenarios & Testing

### User Story 1 - Restarting Home Assistant Retains Costs (Priority: P1)

As a Home Assistant user tracking battery financials,
I want my cumulative cost and acquisition cost metrics to persist across system restarts,
So that I don't lose my historical financial tracking when Home Assistant reboots or the integration reloads.

**Why this priority**: Cost tracking is a core feature of the battery optimization system. Losing this data on restart breaks the financial tracking promise.

**Independent Test**: Can be tested by verifying values in the UI, restarting the Home Assistant core, and confirming the exact same values are restored upon restart.

**Acceptance Scenarios**:

1. **Given** the system has accumulated $5.00 in total cost and $2.00 in acquisition cost, **When** Home Assistant is restarted, **Then** the metrics initialize with $5.00 and $2.00 respectively rather than resetting to zero.
2. **Given** the system is freshly installed with no previous data, **When** it starts up, **Then** it initializes cumulative cost at $0.00 and acquisition cost at 10 c/kWh.

### Edge Cases

- **Acquisition Cost Calculation Horizon**: Acquisition cost is only mathematically calculated based on actuals for the first row (the first 5 minutes) of the optimization matrix. Beyond this immediate interval, it is a forecast. The system must ensure that the persisted acquisition cost always reflects the calculated actuals from this first interval, preventing forward-looking forecasted costs from corrupting the true historical acquisition average.
- What happens when the system is offline for an extended period? Do costs from outside the integration's uptime need to be retroactively calculated? (Assuming no, only tracking while running).
- How does the system handle corrupt persistence files or invalid data? (Should gracefully fall back to $0.00 or the last known good state).

## Requirements

### Functional Requirements

- **FR-001**: System MUST save the cumulative cost metric to a persistent storage mechanism that survives Home Assistant reboots.
- **FR-002**: System MUST save the acquisition cost metric to a persistent storage mechanism that survives Home Assistant reboots.
- **FR-003**: System MUST load these saved values during integration initialization (setup).
- **FR-004**: System MUST gracefully initialize cumulative cost to 0.00 and acquisition cost to 10 c/kWh if no persistent data exists or if the data is corrupt (a default of 10 c/kWh prevents the solver from treating the energy in the battery as worthless).
- **FR-005**: System MUST update the persistent storage whenever the costs change significantly to minimize data loss on unexpected shutdown.

### Key Entities

- **Cost Metrics**: Cumulative cost and acquisition cost representing the financial metrics tracked by the system.
- **Persistent Data Store**: The underlying storage mechanism used to persist the data between sessions.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of tracked cost metrics (cumulative and acquisition) survive a planned Home Assistant restart.
- **SC-002**: Data loss in the event of an unexpected crash is limited to the last unchanged state prior to the crash.
- **SC-003**: System initialization time is not degraded by loading the persisted data.
