# Feature 031: Telemetry Cost Tracker Tasks

## Phase 1: Setup & Foundations
*Goal: Ensure the Home Assistant configuration flow safely captures the optional price sensors on a dedicated page while explicitly warning the user they must be Amber Express sensors.*
- [x] T001 [P1] Add `CONF_TRACKER_IMPORT_PRICE` and `CONF_TRACKER_EXPORT_PRICE` configuration keys to `custom_components/house_battery_control/const.py`
- [ ] T002 [P1] Implement `async_step_cost_tracking` dedicated optional form page in `custom_components/house_battery_control/config_flow.py`. Add explicit disclaimer text to `strings.json` warning users that values must be Amber Express settled sensors.

## Phase 2: Tracker Core (TDD)
*Goal: Build the isolated telemetry tracking module with the 5-minute tick loop and midnight reset interpolation logic for the kWh meter.*
- [x] T003 [P2] Write failing tests in `tests/test_telemetry_tracker.py` demonstrating successful execution of a 5-minute tick and successful mitigation of a simulated midnight kWh reset.
- [x] T004 [P2] Create `TelemetryCostTracker` class structure in `custom_components/house_battery_control/telemetry_tracker.py` with `Store` initialization and `async_load()` persistence loading.
- [x] T005 [P2] Implement `async_track_time_change` trigger on minute boundaries `0, 5, 10...` inside `telemetry_tracker.py`.
- [x] T006 [P2] Implement `_on_tick()` logic in `telemetry_tracker.py`. Read the two newly configured price sensors alongside the existing `CONF_METRIC_GRID_IMPORT_TODAY` and `_EXPORT_TODAY` sensors from the main entry config. Add interpolation handler for when `current_kwh < last_kwh` (midnight reset). Multiply delta by price and persist.

## Phase 3: Integration & Decoupling
*Goal: Sever the old predictive `cumulative_cost` link in the coordinator and seamlessly hook in the new telemetry class.*
- [x] T007 [P3] Remove legacy FSM solver-based `cumulative_cost` accumulation and storage logic from `_update_data` in `custom_components/house_battery_control/coordinator.py`. Update coordinator logic to read from `self.telemetry_tracker.cumulative_cost`.
- [x] T008 [P3] Instantiate `TelemetryCostTracker` inside `async_setup_entry` in `custom_components/house_battery_control/__init__.py`. Load it, pass it to the `HBCDataUpdateCoordinator`, and ensure cleanup via `async_unload_entry`.
- [x] T009 [P3] Run `pytest tests/` to confirm complete isolation from the FSM linear programming solver without breaking any downstream assertion dependencies on the `future_plan`.
