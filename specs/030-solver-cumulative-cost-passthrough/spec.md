# Bug 030: Solver Cumulative Cost Passthrough

## Goal Description
In the House Battery Control system, the solver's projected 24-hour plan generates a table displaying expected metrics at each 5-minute interval. Currently, the `cumulative_cost` column of this projection artificially resets to $0.00 at the very first step (`t=0`), rather than continuing from the user's actual lifetime cumulative cost maintained by the coordinator.

This issue creates a confusing user experience on the dashboard where the forecast cost always appears disjointed from the historically tracked `sensor.hbc_cumulative_cost`.

## Objective
To thread the coordinator's real `cumulative_cost` value down through to the solver, so the 24-hour projection organically builds upon the current historically accurate total.

## User Scenarios
**Scenario 1: Viewing the Dashboard Forecast**
- **Given** the user's running total `cumulative_cost` is currently $14.50.
- **When** the front-end dashboard displays the latest solver forecast table.
- **Then** the first step's `cumulative_cost` should read approximately $14.50 (plus or minus the first interval's charge), instead of $0.00.

## Functional Requirements
1. **Context Expansion**: The `FSMContext` dataclass must be updated to accept `cumulative_cost: float` as a parameter.
2. **Coordinator Injection**: The `HBCDataUpdateCoordinator` must inject `self.cumulative_cost` into the `FSMContext` when instantiating it.
3. **Solver Passthrough**: The `LinearBatteryStateMachine` must initialize its internal `running_cum_cost` loop variable to the provided `context.cumulative_cost`, rather than hardcoding `0.0`.

## Success Criteria
- The integration passes all unit tests and builds successfully.
- Examining the HTTP `/hbc/api/status` debug endpoint confirms that `plan[0]["cumulative_cost"]` matches (excluding single-step math) the top-level `"cumulative_cost"` property.

## Assumptions & Dependencies
- Home Assistant core integrations remain stable.
- The `cumulative_cost` metric structure and Home Assistant `.storage` retrieval mechanics are correctly preserved.
