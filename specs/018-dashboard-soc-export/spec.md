# Feature Specification: Dashboard SoC & Export Price Layout

**Feature Branch**: `018-dashboard-soc-export`  
**Created**: 2026-03-02  
**Status**: Draft  
**Input**: User description: "SoC to be moved up to Power Flow bar. Export c/kWh to be in second row after import c/kWh."  
**GitHub Issue**: #14

## User Scenarios & Testing

### User Story 1 - SoC in Power Flow Bar (Priority: P1)

As a user viewing the dashboard, I want to see the battery SoC percentage displayed alongside the other power flow values (Solar, Grid, Battery, House) so I can see all real-time energy data at a glance without scrolling.

**Why this priority**: SoC is the single most important battery metric and logically belongs with the power flow indicators, not the status grid below.

**Independent Test**: Battery SoC value appears in the Power Flow card alongside Solar, Grid, Battery, and House values.

**Acceptance Scenarios**:

1. **Given** the dashboard loads, **When** the Power Flow card renders, **Then** the SoC percentage is displayed as a fifth item in the flow grid.
2. **Given** the SoC is displayed in the Power Flow card, **When** the user views the Status Grid, **Then** SoC is no longer displayed there (no duplication).

---

### User Story 2 - Export Price Visible on Dashboard (Priority: P1)

As a user monitoring energy pricing, I want to see the current export price (c/kWh) on the dashboard alongside the import price so I can quickly assess whether it's profitable to export.

**Why this priority**: Export price is essential for understanding arbitrage opportunities and is already tracked by the coordinator but not displayed.

**Independent Test**: Export price value appears in the Status Grid immediately after the Import price.

**Acceptance Scenarios**:

1. **Given** the dashboard loads, **When** the Status Grid renders, **Then** the export price (c/kWh) is displayed immediately after the import price.
2. **Given** no export price entity is configured, **When** the Status Grid renders, **Then** the export price shows `0.0` (graceful fallback).

---

### Edge Cases

- What happens when SoC is undefined or null? Display `0%`.
- What happens when export price is undefined? Display `0.0`.
- What happens on narrow screens? The flow grid already wraps — adding a fifth item should not break layout.

## Requirements

### Functional Requirements

- **FR-001**: The Power Flow card MUST display SoC as a fifth item alongside Solar kW, Grid kW, Battery kW, and House kW.
- **FR-002**: SoC MUST be removed from the Status Grid (no duplication).
- **FR-003**: The Status Grid MUST display the current export price (c/kWh) immediately after the import price (c/kWh).
- **FR-004**: The export price MUST be labelled "Export c/kWh" to distinguish it from import price.
- **FR-005**: If export price data is unavailable, the value MUST default to `0.0`.
- **FR-006**: The SoC item in the Power Flow card MUST use a distinct icon to differentiate it from the Battery kW item.

## Success Criteria

### Measurable Outcomes

- **SC-001**: User can see SoC percentage in the Power Flow card on dashboard load.
- **SC-002**: Export price is visible in the Status Grid below the import price.
- **SC-003**: No duplicate SoC values appear on the dashboard.
- **SC-004**: Dashboard renders correctly with all 5 Power Flow items and updated Status Grid on mobile and desktop widths.
