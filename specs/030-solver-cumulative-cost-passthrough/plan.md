# Bug 030: Implementation Plan — Solver Cumulative Cost Passthrough

## Goal Description
To ensure the 24-hour projected `cumulative_cost` chart and table start from the user's scientifically correct, historically accumulated network cost rather than artificially resetting to exactly `$0.00`.

## Proposed Changes

### 1. custom_components/house_battery_control/fsm/base.py
Update the `FSMContext` dataclass definition to explicitly accept `cumulative_cost`.
#### [MODIFY] base.py
- Add `cumulative_cost: float = 0.0` to the `FSMContext` attributes (default to 0.0 for backwards test compatibility).

### 2. custom_components/house_battery_control/coordinator.py
Pass the coordinator's live `cumulative_cost` state down to the solver during the FSM instantiation within `_update_data`.
#### [MODIFY] coordinator.py
- In the `FSMContext` instantiation near line 621, inject `cumulative_cost=self.cumulative_cost`.

### 3. custom_components/house_battery_control/fsm/lin_fsm.py
Override the solver's hardcoded start array.
#### [MODIFY] lin_fsm.py
- Near line 231, change `running_cum_cost = 0.0` to `running_cum_cost = context.cumulative_cost`.

## Verification Plan

### Automated Tests
- Run the full suite `pytest tests/ -v`.
- The tests checking the `future_plan` structure and length must continue to pass, as the mathematical shape of the `cumulative_cost` output curve remains untouched by this constant scalar offset.

### Manual Verification
- Compile and push to the live system.
- Retrieve the JSON output from `/hbc/api/status`.
- Visually verify that the `plan[0].cumulative_cost` array begins with the exact value stored in the parent JSON's `cumulative_cost` field, rather than starting at 0.
- Check the dashboard UI chart for a smooth, unbroken line bridging the current total and the forecasted curve.
