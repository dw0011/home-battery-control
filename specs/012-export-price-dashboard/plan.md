# Implementation Plan: Export Price Dashboard Feature

**Branch**: `012-export-price-dashboard` | **Date**: 2026-02-26 | **Spec**: [012-export-price-dashboard/spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/012-export-price-dashboard/spec.md)
**Input**: Feature specification from `/specs/012-export-price-dashboard/spec.md`

## Summary

This feature aims to satisfy User Story 1 from the specification by exposing the real-time export (sell) price on the HBC dashboard tab alongside the existing import (buy) price. (Note: the Plan tab already exposes the forecasted Export rates per row, this feature applies only to the `status-grid` on the Dashboard tab).
This requires a minor backend change to expose the variable in the diagnostic JSON payload, and a minor frontend change to parse and display it structurally in the 5-column CSS grid.

## Technical Context

**Language/Version**: Python 3.13, ES6 JavaScript  
**Primary Dependencies**: Home Assistant custom component architecture, UI LitElement 2.4.0, pytest  
**Storage**: N/A  
**Testing**: pytest  
**Target Platform**: Home Assistant (Backend), Modern Browsers (Frontend)  
**Project Type**: Home Assistant Integration (Web Component + Python Backend)  
**Performance Goals**: N/A  
**Constraints**: UI visual constraints on mobile resolutions. Grid should ideally handle scaling or wrap cleanly.
**Scale/Scope**: 1 UI Element, 1 JSON Payload Key.

## Proposed Changes

### `coordinator.py`

#### [MODIFY] [coordinator.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/coordinator.py)
- Inside `_async_update_data`, we already extract `current_export_price` as `current_export_price = self._get_sensor_value(CONF_CURRENT_EXPORT_PRICE_ENTITY)`.
- If that fails or isn't supplied, it falls back to `current_export_price = self.rates.get_current_export_price()`.
- The dict returned at the bottom (line ~531) must be updated to include `"current_export_price": current_export_price`. 
- Ensure it handles potential rounding correctly `round(current_export_price, 2)` or similar if the type isn't guaranteed string.

### `tests/test_web.py`

#### [MODIFY] [test_web.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_web.py)
- Update all occurrences of mocked `coordinator.data` (e.g. lines 93, 397, 452) to include the `"current_export_price": 5.0` to prevent `KeyError` regressions on `web.py` rendering.

### `frontend/hbc-panel.js`

#### [MODIFY] [hbc-panel.js](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/frontend/hbc-panel.js)
- Inside `_renderDashboard()`, extract `current_export_price` from the data payload (e.g., `const export_price = d.current_export_price !== undefined ? d.current_export_price : 0;`).
- Insert a new `<div class="stat">` block immediately following the "Price c/kWh" stat block.
- Adjust the labeling so the UI remains clear:
  - Import Stat Label: "Buy c/kWh"
  - Export Stat Label: "Sell c/kWh"
- Adjust the `.status-grid` layout grid in CSS if necessary. It is currently `grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));`. Adding a 6th element to `status-grid` which currently holds 5 elements will naturally scale due to `auto-fit`, but visual validation will be necessary to ensure no weird orphans exist on common resolutions.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_web.py tests/test_coordinator.py` to ensure payload additions don't break existing parsing logic or schema validations.

### Manual Verification
- Deploy the frontend via standard script updating logic.
- Load the Home Assistant frontend and navigate to the HBC sidebar panel.
- Ensure the new "Sell c/kWh" module appears alongside "Buy c/kWh".
- Verify that resizing the browser window down to mobile widths does not break the DOM layout rendering of the `status-grid`.
