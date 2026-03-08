# Implementation Plan: Feature 031 (Telemetry Cost Tracker)

## Goal Description
Extract the historical `cumulative_cost` tracking out of the core predictive `HBCDataUpdateCoordinator` and into a dedicated, solver-independent `TelemetryCostTracker` component. 

This tracker will run on an exact 5-minute clock boundary (`async_track_time_change`), independently calculate real-world energy volume deltas from accumulated Home Assistant `kWh` sensors, and multiply them by live Amber Express price sensors. This isolates the financial tracking from FSM execution rates and handles offline intervals natively via the `kWh` delta.

## User Review Required
No major blocking reviews required. The user has provided the sensor schema (e.g. Amber Express string states like `"-0.02"`). The fallback behavior ensures the system defaults gracefully if the user opts out of configuring these sensors.

## Proposed Changes

---

### Configuration Updates
We will add optional fields to the configuration flow to allow the user to nominate the 4 required entities.

#### [MODIFY] `custom_components/house_battery_control/const.py`
- Add configuration keys:
  - `CONF_TRACKER_IMPORT_PRICE = "tracker_import_price"`
  - `CONF_TRACKER_EXPORT_PRICE = "tracker_export_price"`

#### [MODIFY] `custom_components/house_battery_control/config_flow.py`
- Add a dedicated, isolated configuration step strictly for the cost tracker (e.g., `async_step_cost_tracking`).
- Ensure this page is completely optional.
- Add explicit descriptive text to this configuration page warning the user that these **MUST** be Amber Express price sensors to work correctly because they provide settled intervals.
- Add `selector.EntitySelector` for the 2 new price keys, scoped to appropriate domains (`sensor`).
- Auto-reference the historically existing `CONF_METRIC_GRID_IMPORT_TODAY` and `CONF_METRIC_GRID_EXPORT_TODAY` internally; do not require the user to configure them again.

---

### Core Architecture Updates

#### [NEW] `custom_components/house_battery_control/telemetry_tracker.py`
Create a new module containing the `TelemetryCostTracker` class.
- **Initialization**: Takes `hass` and `config_entry`. Initializes a new `Store` instance specifically for persisting cost (`house_battery_control.cumulative_cost_v2`).
- **Startup**: `async_load()` pulls the last saved `cumulative_cost`, `last_import_kwh`, and `last_export_kwh` from `.storage`.
- **Clock Trigger**: Uses `homeassistant.helpers.event.async_track_time_change(hass, self._on_tick, minute=range(0, 60, 5), second=0)` to guarantee execution explicitly on the 5-minute wall-clock boundary.
- **Tick Logic (`_on_tick`)**:
  - Check if the 2 existing kWh sensors and 2 new price sensors are configured in the entry. If absent, abort calculation.
  - Read `hass.states.get(entity_id)` for the 4 sensors. Ensure they exist and are convertible to `float`.
  - **Midnight Reset Interpolation**: 
    - Calculate `import_delta`. If `current_import < last_import` (indicating the `*_today` sensor reset at midnight), then `import_delta = current_import`.
    - Calculate `export_delta`. If `current_export < last_export`, then `export_delta = current_export`.
  - Otherwise, `import_delta = current_import - last_import`, `export_delta = current_export - last_export`.
  - Multiply by `import_price` and `export_price` respectively.
  - Increment `self.cumulative_cost`.
  - Update `last_import` and `last_export` memory.
  - Trigger `store.async_delay_save` to persist.

#### [MODIFY] `custom_components/house_battery_control/coordinator.py`
- Strip all `cumulative_cost` accumulation and storage saving logic from `_update_data`.
- Keep the `cumulative_cost` attribute on the coordinator, but instead of calculating it, the coordinator simply reads it from the injected `TelemetryCostTracker` reference: `self.cumulative_cost = self.telemetry_tracker.cumulative_cost`.
- If the tracker is unavailable/unconfigured, default `self.cumulative_cost` to `0.0` or pass through `future_plan[0]` as a fallback debug view.

#### [MODIFY] `custom_components/house_battery_control/__init__.py`
- Instantiate `TelemetryCostTracker` during `async_setup_entry`.
- Call `await tracker.async_load()`.
- Pass the `tracker` instance into `HBCDataUpdateCoordinator` so the coordinator can map the single-source-of-truth cost to the dashboard payload.
- Ensure the tracker is cleaned up/unsubscribed in `async_unload_entry`.

---

## Verification Plan
### Automated Tests
- Run `pytest tests/test_coordinator.py` and fix any broken historical cost assertions.
- Add `tests/test_telemetry_tracker.py` mocking `hass.states` to ensure it integrates `kWh` properly over simulated 5-minute intervals and survives negative delta resets.

### Manual Verification
- Deploy to the user.
- Ask the user to assign their Amber Express price sensors and physical inverter `kWh` meter entities in the UI.
- Verify the value ticks up precisely at `XX:00` and `XX:05`.
