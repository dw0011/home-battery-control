# Implementation Plan: Dashboard SoC & Export Price Layout

**Feature**: 018-dashboard-soc-export  
**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/018-dashboard-soc-export/spec.md)  
**GitHub Issue**: #14

## Technical Context

- **Scope**: UI layout change only — no backend changes
- **Risk**: Low — no logic changes, no new dependencies
- **Data source**: `plan[0]["Export Rate"]` already reflects the live export price from the rates timeline (same source as import price)

## Proposed Changes

### Component 1: Panel JavaScript

#### [MODIFY] [hbc-panel.js](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/frontend/hbc-panel.js)

**Change 1 (FR-001)**: Add SoC as 5th item in Power Flow card (`_renderDashboard` L213-234):

```diff
         <div class="flow-item house">
           ...
         </div>
+        <div class="flow-item soc-item">
+          <div class="flow-icon">⚡</div>
+          <div class="flow-value">${soc}%</div>
+          <div class="flow-label">SoC</div>
+        </div>
```

**Change 2 (FR-002)**: Remove SoC from Status Grid (L239-242):

```diff
-        <div class="stat">
-          <div class="stat-value">${soc}%</div>
-          <div class="stat-label">SoC</div>
-        </div>
```

**Change 3 (FR-003/004)**: Add export price to Status Grid after import price (L243-246):

```diff
         <div class="stat">
           <div class="stat-value">${price}</div>
           <div class="stat-label">Import c/kWh</div>
         </div>
+        <div class="stat">
+          <div class="stat-value">${export_price}</div>
+          <div class="stat-label">Export c/kWh</div>
+        </div>
```

**Change 4 (FR-003)**: Read export price from plan data at top of `_renderDashboard()`:

```diff
   const price = d.current_price !== undefined ? d.current_price : 0;
+  const plan = d.plan || [];
+  const export_price = plan.length > 0 ? parseFloat(plan[0]["Export Rate"] || 0) : 0;
```

**Change 5**: Rename "Price c/kWh" label to "Import c/kWh" for clarity now that both prices are shown.

---

### Component 2: Tests

#### [MODIFY] [test_web.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_web.py)

Verify export price is displayed — no backend test needed since data comes from existing plan table.

## Verification Plan

### Automated Tests
- `pytest tests/ -q` — all tests pass (no regression)
- New test: `test_api_status_includes_export_price`

### Manual Verification
- Visual check on HA panel: SoC in Power Flow card, export price in Status Grid
- Cache-bust URL for browser testing
