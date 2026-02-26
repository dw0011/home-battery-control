# Implementation Plan: Current Price Entity Configuration

**Feature Branch**: `011-current-price-entities`  
**Specification**: [spec.md](./spec.md)

## Goal Description

Resolve a data-lag issue where the "current price" used by the dashboard and the initial LP solver step (t=0) diverges from the actual instantaneous grid price. This happens because the system heavily relies on pulling price states from the forecast array of `CONF_IMPORT_PRICE_ENTITY`, rather than checking the entity's actual present state.

Since some dynamic pricing models (like Amber Electric) update their instantaneous price more granularly than their 30-minute block forecasts, the system needs to explicitly query the `state` of instantaneous price sensors. We will introduce new config constants, `CONF_CURRENT_IMPORT_PRICE_ENTITY` and `CONF_CURRENT_EXPORT_PRICE_ENTITY`, explicitly binding `t=0` calculations and the `current_price` metric to these real-time values.

## Proposed Changes

---

### Configuration & Utilities

#### [MODIFY] [const.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/const.py)
- **Changes**: Add two new constants:
  - `CONF_CURRENT_IMPORT_PRICE_ENTITY = "current_import_price_entity"`
  - `CONF_CURRENT_EXPORT_PRICE_ENTITY = "current_export_price_entity"`

---

### Setup & Migrations

#### [MODIFY] [config_flow.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/config_flow.py)
- **Changes**: 
  - Update `async_step_energy` in `ConfigFlow` to include `CONF_CURRENT_IMPORT_PRICE_ENTITY` and `CONF_CURRENT_EXPORT_PRICE_ENTITY` using `EntitySelector`. Change labels for `CONF_IMPORT_PRICE_ENTITY` to reflect they are for *forecasts*.
  - Update `HBCOptionsFlowHandler` -> `async_step_energy` identically.

#### [MODIFY] [strings.json](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/strings.json) / [en.json](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/translations/en.json)
- **Changes**: Add English translations and UI form validation strings for `current_import_price_entity` and `current_export_price_entity`. Rename existing price entities to "Import Price Forecast Entity".

---

### Core Data & Services

#### [MODIFY] [coordinator.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/coordinator.py)
- **Changes**:
  - Add `CONF_CURRENT_IMPORT_PRICE_ENTITY` and `CONF_CURRENT_EXPORT_PRICE_ENTITY` to `_build_sensor_diagnostics`.
  - In `_async_update_data`, explicitly fetch the instantaneous price:
    ```python
    current_import_entity = self.config.get(CONF_CURRENT_IMPORT_PRICE_ENTITY)
    if current_import_entity:
        current_price = self._get_sensor_value(current_import_entity)
    else:
        current_price = self.rates.get_import_price_at(dt_util.now())
    ```
  - Pass the exact same logic for the export price if `current_export_price_entity` is provided, supplying it to the `FSMContext` (or adjusting the start of the `forecast_price` array within `lin_fsm.py` if needed). Note that `lin_fsm.py` currently uses `context.current_price` if `t=0` is missing from the forecast, but if the forecast is provided, it uses `float(entry.get("import_price", 0.0))`. 
  - To respect `SC-001`, we must mutate `context.forecast_price[0]` or explicitly override `price_buy[0]` and `price_sell[0]` in `lin_fsm.py` with the accurate `current_price` and `current_export_price`.

#### [MODIFY] [lin_fsm.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py)
- **Changes**: Ensure `calculate_next_state` overrides `price_buy[0]` and `price_sell[0]` with `context.current_price` and `context.current_export_price` (which need to be explicitly passed via `FSMContext`). This guarantees the LP optimizer sees the *instantaneous* price for the very first operational step immediately prior to execution.

## Verification Plan

### Automated Tests
- Run `pytest tests/` specifically monitoring `test_config_flow.py` for new schema compliance.
- Update `test_coordinator.py` mock configurations to include the new entities and verify they override `rates.get_import_price_at(now)`.

### Manual Verification
- View `/hbc/api/status` to ensure `current_price` perfectly syncs with the raw state of `sensor.amber_general_price`.
- Verify the Plan Tab reflects the live price on the very first row `t=0`.
