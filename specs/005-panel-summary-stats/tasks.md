# Tasks: HBC Panel Summary Stats

## Phase 1: Setup
*(No broad setup tasks required for this UI enhancement)*

## Phase 2: Foundational
*(No foundation required, the `plan` payload is already populated with the necessary 288 intervals)*

## Phase 3: Add Summary Stats to Dashboard and Plan Tabs [US1]
**Goal**: Calculate and display 24-hour summary averages and totals for key metrics derived from the frontend interval loop.

- [x] T001 [US1] Create a new helper method `_calculateSummaryStats()` inside the `HBCPanel` class in `c:\Users\markn\OneDrive - IXL Signalling\0-01 AI Programming\AI Coding\House Battery Control\custom_components\house_battery_control\frontend\hbc-panel.js` to iterate over `this._data.plan` and return the math aggregates for Average Import Price, Average Export Price, Total PV kWh, and Total Load kWh.
- [x] T002 [US1] Modify `_renderDashboard()` in `hbc-panel.js` to invoke the helper and append a secondary row of status cards beneath the primary display showing the summary stats.
- [x] T003 [US1] Modify `_renderPlan()` in `hbc-panel.js` to invoke the helper and inject a `<tfoot>` element containing these 4 key aggregates at the bottom of the tabular data representation.

## Phase 4: Polish & Verification
- [x] T004 Run `pytest tests/test_web.py` to ensure the file still serves without string formatting errors.
- [x] T005 Deploy to Home Assistant and manually verify the Dashboard and Plan tabs accurately reflect the totals.

## Dependencies
- T001 must be completed first as it provides the data engine for the UI components.
- T002 and T003 depend on T001 but can naturally follow sequentially as they target the same file.
- T004 and T005 are verification steps dependent on T001-T003 completion.
