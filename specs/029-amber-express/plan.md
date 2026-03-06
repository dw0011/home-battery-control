# Implementation Plan: Amber Express Data Source Integration

**Feature Branch**: `029-amber-express`  
**Status**: Draft

## Goal Description
Integrate a new integration configuration toggle (`CONF_USE_AMBER_EXPRESS`) that switches `RatesManager` into an extraction mode capable of parsing Amber Express sensor dictionaries. Unlike the native Amber integration which creates dedicated "Forecast" entities, Amber Express embeds its entire 24-hour horizon inside the `forecasts` attribute array on the current price entity itself.

## User Review Required
The new configuration switch `CONF_USE_AMBER_EXPRESS` will be added to the Options Flow (so existing users can toggle it without deleting the integration) and the Config Flow (so new setups can select it). Is placing this underneath the Price Entity selectors in the UI appropriate?

## Proposed Changes

### Configuration Updates

#### [MODIFY] `custom_components/house_battery_control/const.py`
- Add `CONF_USE_AMBER_EXPRESS = "use_amber_express"`
- Add `DEFAULT_USE_AMBER_EXPRESS = False`

#### [MODIFY] `custom_components/house_battery_control/config_flow.py`
- Update `async_step_energy` schema to include:
  ```python
  vol.Optional(CONF_USE_AMBER_EXPRESS, default=DEFAULT_USE_AMBER_EXPRESS): BooleanSelector(),
  ```
- Ensure this defaults to the user's existing setting if configuring via Options Flow. (Wait, S2 architecture states `config_flow.py` handles both initial and updates via `.async_show_form` re-entries. I'll add the boolean flag to the main `energy` schema.)

### Core Logic Updates

#### [MODIFY] `custom_components/house_battery_control/coordinator.py`
- Update `__init__` to pass the new `use_amber_express` flag into `RatesManager`.
  ```python
  self.rates = RatesManager(
      hass,
      config.get(CONF_IMPORT_PRICE_ENTITY, ""),
      config.get(CONF_EXPORT_PRICE_ENTITY, ""),
      use_amber_express=config.get(CONF_USE_AMBER_EXPRESS, False),
  )
  ```

#### [MODIFY] `custom_components/house_battery_control/rates.py`
- Update `__init__` to accept `use_amber_express: bool = False`.
- In `_parse_entity`, intercept the `raw_data` assignment.
- If `use_amber_express` is True, `raw_data` should explicitly read:
  ```python
  if self._use_amber_express:
      raw_data = state.attributes.get("forecasts", [])
  ```
- Currently, `_parse_entity` reads `interval.get("per_kwh")`. This exactly matches the Amber Express spec provided by the user (`per_kwh: -0.0637` and `per_kwh: 0.1124`).
- Since Amber Express provides 30-minute chunks, the existing Phase 8 loop in `rates.py` (lines 102-119) will automatically chunk these 30-minute intervals into 5-minute ticks for the LP solver. This is a massive native win.

## Verification Plan

### Automated Tests
1. Edit `tests/test_rates.py` (create if doesn't exist, though rate logic is currently partially tested via `test_coordinator.py`).
2. Add a targeted test injecting an Amber Express dictionary structure into `hass.states` and assert `RatesManager` unpacks it into exactly 6x 5-minute ticks per 30-minute block.
3. Assert that when `use_amber_express=False`, the standard parser array logic is preserved.

### Manual Verification
1. Open HA Integrations > House Battery Control > Configure.
2. Toggle "Use Amber Express".
3. Check UI Plan Table to verify the forecast timeline extends into the future (proving it unpacked the array).
