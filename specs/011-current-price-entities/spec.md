# Feature Specification: Current Price Entity Configuration

**Feature Branch**: `011-current-price-entities`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User notes that the generated plan forecast is sometimes very different from the current price, because there is no config state for a "price now" entity for feed-in or import.

## Problem Statement

The system currently relies on the forecast arrays provided by the `CONF_IMPORT_PRICE_ENTITY` and `CONF_EXPORT_PRICE_ENTITY` to determine the "current" price for the LP solver (step 0) and the dashboard. However, in fast-moving dynamic pricing markets (like Amber Electric), the instantaneous current price state can diverge from the interpolated forecast array for the current time block. 

Users need the ability to explicitly configure separate sensor entities that provide the true instantaneous "Current Import Price" and "Current Export Price" to ensure the FSM's first step and the dashboard UI represent reality accurately.

## User Scenarios & Testing

### User Story 1 - Configure Current Price Entities (Priority: P1)

A user navigates to the HBC configuration flow (either Initial Setup or Options Flow -> Energy & Metrics). They are presented with two new required entity selectors: "Current Import Price Entity" and "Current Export Price Entity", alongside the existing forecast price entities.

**Acceptance Scenarios**:

1. **Given** a user opens the "Energy & Metrics" config step, **When** the form renders, **Then** they see fields for both forecast price entities and instantaneous current price entities.
2. **Given** the user selects `sensor.amber_general_price` for both forecast and current import price, **When** the coordinator updates, **Then** it reads the instantaneous price directly from the entity state, rather than parsing the forecast array for step 0 calculations.

---

### User Story 2 - Real-Time Dashboard Accuracy (Priority: P1)

The user views the HBC dashboard during a price spike. The "current price" displayed on the dashboard precisely matches the state of their configured current price entity, bypassing any lag in the forecast arrays.

**Acceptance Scenarios**:

1. **Given** the current import price entity reports 150 c/kWh and the forecast array reports 30 c/kWh for the current interval, **When** the UI updates, **Then** the dashboard clearly shows 150 c/kWh as the current price and the solver utilizes 150 c/kWh for the immediate calculation step.

---

## Requirements

### Functional Requirements

- **FR-001**: Introduce two new configuration constants: `CONF_CURRENT_IMPORT_PRICE_ENTITY` and `CONF_CURRENT_EXPORT_PRICE_ENTITY`.
- **FR-002**: The config flows (Setup and Options) must prompt for these entities in the "Energy & Metrics" step.
- **FR-003**: `coordinator.py` must populate the LP solver's `current_price` directly from the configured `CONF_CURRENT_IMPORT_PRICE_ENTITY` state.
- **FR-004**: The solver step `t=0` logic must natively bind to this instantaneous current import/export price rather than the first element of the smoothed forecast array.
- **FR-005**: If the instantaneous prices are unavailable, the system must gracefully fallback to the forecast array's current valid time block as per existing behavior.

### Non-Functional Requirements

- **NFR-001**: Must remain backward compatible. Existing setups without these new keys should seamlessly use their forecast entity as a fallback for the current price or require reconfiguration gracefully.
- **NFR-002**: All existing tests must pass or be appropriately updated.

## Success Criteria

- **SC-001**: The FSM calculates `t=0` pricing based entirely on the explicitly defined instantaneous price entities.
- **SC-002**: The dashboard accurately presents the instantaneous price independent of array lag.
- **SC-003**: Unit tests successfully validate the fallback mechanism and direct state extraction.
