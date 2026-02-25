# Specification: Remove Artificial 4kW Load Prediction Limit

## Description
The House Battery Control integration currently enforces a hardcoded maximum cap of 4.0kW on load predictions derived from historical usage. This prevents accurate forecasting for households with heavy-draw appliances (such as EV chargers, electric heating, induction cooktops) where average periodic load routinely exceeds 4kW. This artificial limitation must be removed entirely so the integration relies natively on the historical telemetry to guide the solver.

## User Scenarios

**Scenario 1: High Draw Household Forecasting**
- **User Activity:** A user operates an EV charger at 7kW during peak historical usage windows.
- **Expected Outcome:** The internal load predictor correctly identifies the 7kW average historical draw and surfaces this directly to the FSM/Solver without artificial suppression.

**Scenario 2: Winter Electric Heating**
- **User Activity:** A user heavily relies on reverse-cycle air-conditioning, drawing a continuous 5.5kW during evening peaks.
- **Expected Outcome:** The load forecasting accurately predicts a 5.5kW draw + temperature sensitivity additions, passing the unrestrained, accurate prediction to the solver to budget adequately.

## Functional Requirements

- **FR-01: Remove 4kW Clamp:** The system shall not restrict, cap, or clamp predicted load output to an arbitrary upper ceiling (historically 4.0kW).
- **FR-02: Retain Natural Ceilings:** The load predictor shall continue to output whatever maximum kilowatt load the historical extraction logically dictates (plus legitimate sensitivity augmentations).
- **FR-03: Backward Compatibility (0 Floor):** The system shall continue to prevent negative load forecasting (the floor of 0.0kW must remain enforce).

## Success Criteria

1. **Measurable Prediction Accuracy:** The integration reliably forecasts loads greater than 4.0kW dynamically, directly proportional to past behavior without clamping.
2. **Solver Ingestion:** The LP solver correctly receives and processes the unrestricted load profiles (e.g. 7.5kW) to calculate appropriate opportunity costs or grid import bounds.
3. **Tests Pass:** Related unit tests are adapted and effectively prove that load forecasting can return loads greater than 4.0kW.

## Assumptions & Boundaries

- No configuration GUI modifications are required, as the user explicitly instructed to remove the limit globally rather than implementing user-configurable maximums.
- The `LoadPredictor` class naturally bounds predictions via the existing negative-clip floor (`max(0.0, derived_value)`); this floor is safe and outside the scope of removal.
