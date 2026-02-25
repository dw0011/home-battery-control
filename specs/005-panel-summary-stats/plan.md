# Implementation Plan: HBC Panel Summary Stats

## Goal Description
Enhance the custom `hbc-panel` UI to provide a quick 24-hour summary of critical metrics (Average Import Price, Average Export Price, Total PV Forecast, Total Load Forecast). These metrics need to be calculated from the existing 288-interval forecast array (`this._data.plan`) and displayed in two places:
1. On the **Dashboard Tab** (as a new standalone summary card).
2. On the **Plan Tab** (as an appended footer `<tfoot>` below the interval data table).

## Proposed Changes

### UI Frontend Component
The changes will be entirely localized to the frontend LitElement component.

#### [MODIFY] hbc-panel.js
- **Helper Method**: Introduce a new method `_calculateSummaryStats()` that processes `this._data.plan`. It will iterate over the 288 elements to:
  - Accumulate `Import Rate` and divide by total intervals (Average Import c/kWh).
  - Accumulate `Export Rate` and divide by total intervals (Average Export c/kWh).
  - Accumulate `PV Forecast` and `Load Forecast` (which are in kW). To convert 5-minute kW samples to kWh, it will sum them and divide by 12 (Total PV kWh, Total Load kWh).
- **Dashboard View (`_renderDashboard`)**:
  - Call the helper method to get the stats.
  - Add a new `<div class="card">` containing a `<div class="status-grid">` with 4 new stat blocks matching the existing visual language.
- **Plan View (`_renderPlan`)**:
  - Call the helper method.
  - Add a `<tfoot>` element to the `<table>` definition rendering a row with a bold design highlighting the 4 key totals, visually anchored to the relevant columns.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_web.py` to ensure the JS file is still served correctly. (Note: standard HA python tests do not execute LitElement JavaScript).

### Manual Verification
- Deploy to the local Home Assistant instance via HACS.
- Ask the USER to verify the dashboard visually or use the `browser_subagent` to capture screenshots of both the **Dashboard Tab** and **Plan Tab** in the browser.
- Mathematically spot-check that the sum of the table rows aligns with the totals provided in the footer.
