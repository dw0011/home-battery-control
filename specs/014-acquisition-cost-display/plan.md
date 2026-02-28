# Implementation Plan: Acquisition Cost Display

**Branch**: `014-acquisition-cost-display` | **Date**: 2026-02-28 | **Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/014-acquisition-cost-display/spec.md)

## Summary

Add the live battery acquisition cost to the **Dashboard** tab's "24-Hour Forecast Summary" card, alongside Avg Import, Avg Export, Total Gen, Total Load.

## Technical Context

**File**: `custom_components/house_battery_control/frontend/hbc-panel.js`  
**Method**: `_renderDashboard()` (line 140)  
**Location**: "24-Hour Forecast Summary" card (lines 213-233)  
**Data source**: `this._data.acquisition_cost` — already in `/hbc/api/status` response

## Changes

### [MODIFY] hbc-panel.js — `_renderDashboard()` (after line 231)

Add a new stat item to the "24-Hour Forecast Summary" status-grid:

```diff
           <div class="stat">
             <div class="stat-value">${summaryStats.totalLoad}</div>
             <div class="stat-label">Total Load kWh</div>
           </div>
+          <div class="stat">
+            <div class="stat-value">${(d.acquisition_cost || 0).toFixed(2)}</div>
+            <div class="stat-label">Acq Cost c/kWh</div>
+          </div>
         </div>
       </div>
```

That's the entire change. No plan tab, no backend, no new calculations.

## Verification

```bash
pytest tests/ -v          # 150 tests must pass
ruff check custom_components/ tests/   # clean
```

Manual: Open Dashboard tab, confirm "Acq Cost c/kWh" tile appears in the 24-Hour Forecast Summary section.
