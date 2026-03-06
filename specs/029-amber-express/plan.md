# Implementation Plan: Amber Express Data Source Integration

**Feature Branch**: `029-amber-express`  
**Status**: Draft

## Goal Description
Integrate a new integration configuration toggle (`CONF_USE_AMBER_EXPRESS`) that switches `RatesManager` into an extraction mode capable of parsing Amber Express sensor dictionaries. 

Amber Express embeds its entire 24-hour horizon inside the `forecasts` attribute array on the current price entity itself. Furthermore, it includes `advanced_price_predicted` and `renewables` data. The system must linearly blend the price from `predicted` to `high` if renewables fall between 35% and 25%.

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
- Update `update()` to branch based on `self._use_amber_express`:
  ```python
  if self._use_amber_express:
      import_rates = self._parse_amber_express_entity(self._import_entity_id, "import")
      export_rates = self._parse_amber_express_entity(self._export_entity_id, "export")
  else:
      import_rates = self._parse_entity(self._import_entity_id, "import")
      export_rates = self._parse_entity(self._export_entity_id, "export")
  ```
- **[NEW METHOD]** Create `_parse_amber_express_entity(self, entity_id, label)`:
  - This method exclusively reads `state.attributes.get("forecasts", [])`.
  - It loops through the `forecasts` list and exacts prices using the exact `advanced_price_predicted` logic.
  
  **Price Extraction and Blending (FR-003, FR-004)**: During the loop over `raw_data`, calculate the price dynamically.
  - Extract `renewables = float(interval.get("renewables", 100.0))`
  - Extract `advanced = interval.get("advanced_price_predicted", {})`
  - `predicted_price = float(advanced.get("predicted", interval.get("per_kwh", 0.0)))`
  - `high_price = float(advanced.get("high", predicted_price))`
  
  **Blending Math:**
  ```python
  if renewables >= 35.0:
      price = predicted_price
  elif renewables <= 25.0:
      price = high_price
  else:
      # Linear interpolation between 35% and 25% (a 10% band)
      # e.g., at 30%, it is exactly 50% predicted + 50% high.
      # e.g., at 31%, it is 60% predicted + 40% high.
      ratio_predicted = (renewables - 25.0) / 10.0
      ratio_high = 1.0 - ratio_predicted
      price = (ratio_predicted * predicted_price) + (ratio_high * high_price)
  ```

- Re-implement the Phase 8 loop (from the standard `_parse_entity`) identically inside `_parse_amber_express_entity` to ensure the dynamically calculated `price` is chunked into native 5-minute ticks.

## Verification Plan

### Automated Tests
1. Edit `tests/test_rates.py` (create if doesn't exist, though rate logic is currently partially tested via `test_coordinator.py`).
2. Add a targeted test injecting an Amber Express dictionary structure into `hass.states` and assert `RatesManager` unpacks it into exactly 6x 5-minute ticks per 30-minute block.
3. Assert that when `use_amber_express=False`, the standard parser array logic is preserved.

### Manual Verification
1. Open HA Integrations > House Battery Control > Configure.
2. Toggle "Use Amber Express".
3. Check UI Plan Table to verify the forecast timeline extends into the future (proving it unpacked the array).
