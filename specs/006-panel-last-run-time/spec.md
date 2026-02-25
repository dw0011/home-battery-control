# Specification: Panel Last Run Time

## 1. Description
The Custom Panel (HBC Dashboard) dynamically displays energy flows, hardware states, and the 24-hour battery plan. The user wants the 'Last Run Time' (the timestamp indicating when the pipeline was last executed and the UI data was refreshed) visible directly on the UI for situational awareness.

This should be added to both the **Dashboard tab** and the **Plan tab** so the user doesn't have to switch views or open the 'Sensor Status' dropdown just to see how fresh the data is.

## 2. Requirements

1. **Visibility on Dashboard View**:
   - The timestamp indicating when the data was last updated must be visible on the main Dashboard view.
2. **Visibility on Plan View**:
   - The same timestamp must be visible on the Plan view (24-hour forecast table view).
3. **Data Source**:
   - The UI should utilize the existing last update timestamp (e.g., `last_update` from the API payload).
4. **Placement**:
   - The timestamp should be positioned logically, such as in the header, footer, or near the existing summary info, without taking up excessive vertical space or cluttering primary metrics.
5. **Format**:
   - The timestamp should be human-readable, ideally in local time. (e.g., standard datetime string format already provided by the backend).

## 3. Assumptions & Clarifications
- **Fact:** The backend API (`/hbc/api/status`) and the data update coordinator natively expose a `last_update` string. This is provided in ISO UTC format (e.g. `2026-02-25T06:52:30.804291+00:00`).
- **Assumption:** No backend Python changes are strictly necessary. The frontend JS can parse this UTC timestamp, convert it to local time, and format it gracefully for display.

## 4. User Scenarios
1. **Verifying Data Freshness (Dashboard)**: The user opens the HBC panel on their phone and looks at the Dashboard. They immediately see "Last Updated: 2026-02-25 17:30" and know the SoC and grid readings are current.
2. **Reviewing the Plan (Plan)**: The user opens the Plan tab to see the FSM actions for tonight. They see the "Last Updated" timestamp at the top of the table card, confirming the 288-interval forecast was just recently generated.

## 5. Success Criteria
- [ ] Navigating to the Custom Panel Dashboard tab clearly shows the "Last Update" time.
- [ ] Navigating to the Custom Panel Plan tab clearly shows the "Last Update" time.
- [ ] No regression or breakage to existing cards or the sensor status dropdown.
