# Implementation Plan: 001-fix-cost-persistence

**Branch**: `001-fix-cost-persistence` | **Date**: 2026-02-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-fix-cost-persistence/spec.md`

## Summary

The objective is to fix the issue where cumulative cost and acquisition cost lose their historical tracking when Home Assistant or the House Battery Control integration restarts. The system currently hardcodes the fallback acquisition cost to `0.06` in the coordinator and computes cumulative cost purely for the future UI rendering array rather than persistently tracking actuals over time.

We will integrate `homeassistant.helpers.storage.Store` into the `HBCDataUpdateCoordinator` to read and save a running state of `cumulative_cost` and `acquisition_cost`, defaulting correctly to $0.00 and 10c/kWh respectively.

## Technical Context

**Language/Version**: Python 3.12 (HA component)
**Primary Dependencies**: `homeassistant.helpers.storage.Store`
**Storage**: HA standard `.storage/` directory via JSON dict
**Testing**: pytest (mocking `Store`)
**Target Platform**: Home Assistant OS / Core
**Project Type**: Custom Integration backend

## Constitution Check

*Not applicable. No broad architectural changes beyond standard custom component APIs are being introduced.*

## Proposed Changes

### custom_components/house_battery_control/coordinator.py
[MODIFY] `coordinator.py`(file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/coordinator.py)
- Import `Store` from `homeassistant.helpers.storage` safely.
- Add `self.store = Store(hass, 1, "house_battery_control.cost_data")` to `__init__`.
- Add `async def async_load_stored_costs(self)` to load data from the store initially. Initialize `self.cumulative_cost = 0.0` and `self.acquisition_cost = 0.10` (10c/kWh = 0.10) if store is empty.
- Hook `async_load_stored_costs` strictly into module setup (likely called externally by `__init__.py` async setup procedure, or directly in `coordinator.py`). 
- **CRITICAL MATH FIX**: In `_async_update_data`, rather than passing a hardcoded `0.06`, pass `self.acquisition_cost`.
- After `fsm_result` is computed, analyze `future_plan[0]` (the very first 5-minute interval representing the action taken *now*). Based on `future_plan[0]` net grid kW and current prices, calculate reality:
  - Add to `self.cumulative_cost`.
  - Mathematically re-calculate `self.acquisition_cost` based on energy pushed into the battery *only* during this immediate 5-minute interval.
- Call `self.store.async_delay_save(...)` if values changed significantly to persist them to disk.
- Expose these variables to the UI state output dictionary safely so `web.py` can render the true cumulative figures instead of resetting ones.

### custom_components/house_battery_control/__init__.py
[MODIFY] `__init__.py`(file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/__init__.py)
- Ensure the newly created `async_load_stored_costs` is `await`ed on `coordinator` initialization before the first refresh is requested, guaranteeing the correct data is in memory when the FSM boots.

## Verification Plan

### Automated Tests
1. **Test `async_load_stored_costs`**: Add test asserting reading missing files falls back to 0.00 / 0.10. Assert reading valid storage file restores exactly.
2. **Test FSM Tick State Mutator**: Write a unit test that mocks `_async_update_data` resolving an FSM plan, and verifies `coordinator.cumulative_cost` and `coordinator.acquisition_cost` strictly mutate based *only* on the first row's intervals, not the entire 24h array.
3. run `pytest tests/test_coordinator.py` locally.

### Manual Verification
1. Open Home Assistant with House Battery Control running.
2. Manually observe the UI displaying `Cumul. Cost`.
3. Force restart Home Assistant.
4. Verify immediately upon initialization that the UI accurately displays the correct historical `Cumul. Cost` and it hasn't reset to `$0.00`.
