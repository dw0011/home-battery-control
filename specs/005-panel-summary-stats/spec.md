# Specification: HBC Panel Summary Stats

## Description
The user wants to enhance the `hbc-panel` (the custom frontend dashboard for the integration) by displaying a summary statistics footer at the bottom of the tabular data. This footer will provide at-a-glance 24-hour aggregate forecasts for key decision-making metrics. 

Specifically, the footer must display:
1. Average Import Price (over the 24-hour horizon)
2. Average Export Price (over the 24-hour horizon)
3. Total Forecasted PV Generation (kWh)
4. Total Forecasted House Load (kWh)

## User Scenarios

**Scenario 1: Daily Briefing (Plan Tab)**
- **User Activity:** The user opens the House Battery Control panel, navigates to the Plan tab, to understand the day's outlook.
- **Expected Outcome:** Below the 24-hour interval table, a clear summary bar shows the average cost of grid power, expected solar yield, and predicted house consumption.

**Scenario 2: Quick Status Check (Dashboard Tab)**
- **User Activity:** The user opens the House Battery Control panel on the default Dashboard view.
- **Expected Outcome:** In addition to the large current status displays, a secondary row (or dedicated card section) displays the same 24-hour summary statistics (Average Import, Average Export, Total PV, Total Load).

## Functional Requirements

- **FR-01a: Plan Tab Summary Footer:** The UI component shall include a persistent or appended footer section located below the main interval data table on the Plan tab.
- **FR-01b: Dashboard Tab Summary Row:** The UI component shall include a secondary row or card section on the main Dashboard tab displaying the same summary metrics.
- **FR-02: Average Import Calculation:** The UI (or backend) shall calculate and display the mathematical average of all forecasted `import_price` values over the next 24 hours.
- **FR-03: Average Export Calculation:** The UI (or backend) shall calculate and display the mathematical average of all forecasted `export_price` values over the next 24 hours.
- **FR-04: Total PV Forecast:** The UI (or backend) shall sum the `solar_kw` capacity generated per interval and convert it to total kWh expected over the 24-hour period.
- **FR-05: Total Load Forecast:** The UI (or backend) shall sum the `load_kw` draw per interval and convert it to total kWh consumed over the 24-hour period.

## Success Criteria

1. **Visibility:** The summary metrics are clearly visible at both the bottom of the Plan tab and within a distinct row/section on the Dashboard tab of the Home Assistant custom panel.
2. **Accuracy:** The displayed metrics mathematically match the aggregate of the 288 5-minute intervals provided in the API payload.
3. **Responsiveness:** The layout adapts appropriately to mobile and desktop displays within the Home Assistant companion app and web interface.

## Assumptions & Boundaries

- The data required to calculate these aggregates (prices, solar_kw, load_kw) is already present in the existing `future_plan` JSON array payload sent to the frontend.
- It is assumed to be more efficient to perform these straightforward arithmetic aggregations dynamically in the JavaScript frontend (`hbc-panel.js`) rather than modifying the Python backend API contracts, keeping the API payload lean.
