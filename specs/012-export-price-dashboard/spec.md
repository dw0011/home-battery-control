# Feature Specification: Export Price Dashboard Feature

**Feature Branch**: `012-export-price-dashboard`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User description: "One small request, I don't see the export/sell price on the dashboard - can we get that next to current price"

## User Scenarios & Testing

### User Story 1 - Viewing Export Price on Dashboard (Priority: P1)

As a Home Assistant user observing the HBC dashboard tab (not the plan tab),
I want to see the current export (sell) price alongside the current import (buy) price,
So that I can immediately understand the financial incentive for discharging my battery to the grid without having to check secondary sensor cards.

**Why this priority**: Directly solves the user request and improves the standalone observability of the custom panel.

**Independent Test**: Can be tested by opening the HBC panel in Home Assistant and verifying that a new "Export" or "Sell" price element is visible, formatted correctly (like "45.2 c"), and matches the `current_export_price` sensor or rate forecast.

**Acceptance Scenarios**:

1. **Given** the system is successfully polling Amber rates, **When** the dashboard renders, **Then** both the "Buy" (Import) and "Sell" (Export) prices are clearly displayed in the status grid.
2. **Given** the underlying export spot price spikes to 150c/kWh, **When** the dashboard updates, **Then** the export price reflects the exact 150c/kWh value.

### Edge Cases

- What happens if the `export_price` data is null or unavailable from the API payload? (Dashboard should handle it gracefully, e.g., displaying "--" or hiding the element rather than throwing a JavaScript error).
- How does the layout handle very large numbers or negative numbers? (e.g., if export drops to -5.0c/kWh, the UI must not break formatting).

## Requirements

### Functional Requirements

- **FR-001**: The `/hbc/api/status` backend API MUST include the current export price in its JSON payload alongside the existing `current_price` (import).
- **FR-002**: The `frontend/hbc-panel.js` LitElement MUST parse and render this new export price metric.
- **FR-003**: The UI layout MUST position the export price logically (e.g., next to the import price, potentially labeling them "Buy" and "Sell" for clarity).
- **FR-004**: The system MUST format the export price consistently with the import price (e.g., standardizing on `X.X c` format).

### Key Entities

- **Status Payload**: The JSON dictionary returned by `coordinator.py` and `web.py` to the frontend panel.
- **HBC Panel Widget**: The visual HTML/CSS LitElement rendering the dashboard.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The export price is visible to the user on the primary dashboard interface.
- **SC-002**: The rendered value perfectly matches the underlying `current_export_price` known to the Coordinator.
- **SC-003**: The addition of the new UI element does not visually break or crowd the existing status-grid layout on mobile resolutions.
