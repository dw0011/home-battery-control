# BUG-030 Follow-Up 2: Telemetry Cost Tracker

## Goal Description
The `cumulative_cost` metric should track the real-world money traded with the grid since the integration was installed. Currently, the system attempts to build this historical tracker by blindly inheriting the LP solver's 5-minute *forward projection*. 

As the user correctly identified, because the solver often runs dynamically multiple times within a 5-minute window (due to telemetry state changes like a fridge turning on), the coordinator constantly adds entire 5-minute forecast blocks to the historical tracker, causing exponential cost inflation.

**Proposed Solution:**
The historical cost tracker must be fully decoupled from the solver's future predictions. The coordinator must calculate the *actual* energy transferred since its last update tick using the physical `grid_power` sensor and the exact elapsed time between ticks.

## Proposed Changes

### 1. `custom_components/house_battery_control/coordinator.py`
Track the exact timestamp of the last update and compute real-world grid energy.
#### [MODIFY] coordinator.py
- In `__init__`, initialize `self._last_update_time: datetime | None = None`.
- In `_update_data`, calculate `delta_time = dt_util.utcnow() - self._last_update_time`.
- Calculate `delta_hours = delta_time.total_seconds() / 3600.0`.
- Calculate actual energy transferred: `actual_kwh = grid_p * delta_hours`.
- Multiply `actual_kwh` by `current_price` (for import) or `current_export_price` (for export) to find the exact cost incurred since the last tick.
- Add this micro-interval cost to `self.cumulative_cost`.
- Update `self._last_update_time = dt_util.utcnow()`.
- Ensure tests still pass by stripping out the `future_plan` dependency for the cost tracker.

## Verification
- Run `pytest tests/test_coordinator.py`.
- Ensure the in-memory state correctly ticks up based on *time elapsed*, independent of how many times the solver is invoked.
