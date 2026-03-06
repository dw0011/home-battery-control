# Feature Specification: Amber Express Data Source Integration

**Feature Branch**: `029-amber-express`  
**Created**: 2026-03-07  
**Status**: Draft  
**Input**: User description: "Integrate support for Amber Express pricing sensors... The system needs a configuration switch to select 'Amber Express' mode... For pricing, use 'advanced_price_predicted.predicted' unless renewables < 35%, then blend predicted to high. All predicted at 35%, all high at 25% or below."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configuring Amber Express Mode (Priority: P1)

As a user installing or configuring House Battery Control for an Amber Express setup, I want to explicitly select "Amber Express" as my data source during the configuration flow, so that the system knows how to correctly parse my pricing entities.

**Why this priority**: Without this toggle, users with Amber Express cannot use the integration because the data format is fundamentally different from standard Amber.

**Independent Test**: The Home Assistant configuration and options flows must display a checkbox or dropdown allowing the selection of "Use Amber Express format".

**Acceptance Scenarios**:

1. **Given** a new or existing integration setup, **When** I open the configuration UI, **Then** I see clearly marked option to enable "Amber Express format".
2. **Given** the option is checked, **When** the configuration is saved, **Then** the boolean flag is stored in the integration config entry.

---

### User Story 2 - Parsing Embedded Forecast Arrays (Priority: P1)

As a user with Amber Express pricing, I want the system to correctly predict future LP solver steps by mathematically extracting the forecast timeline embedded deep within my current price sensor's state attributes.

**Why this priority**: The linear programming solver is entirely dependent on an accurate future price timeline to make optimal decisions.

**Independent Test**: The FSM's `rates` timeline array must be exactly populated with the 30-minute interval blocks extracted from the `forecasts` attribute, mapping `per_kwh` to `price`.

**Acceptance Scenarios**:

1. **Given** an Amber Express import entity with a `forecasts` attribute array, **When** the `RatesManager` executes its data fetch, **Then** it correctly maps each item's `start_time`, `end_time`, and `per_kwh` into the internal HBC rate timeline structure.
2. **Given** the system is in standard mode (not Amber Express), **When** the `RatesManager` executes, **Then** it continues to use the existing logic without crashing or attempting to parse non-existent attributes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The config/options flows MUST include a boolean configuration flag (`CONF_USE_AMBER_EXPRESS`) to toggle parsing behavior.
- **FR-002**: When `CONF_USE_AMBER_EXPRESS` is True, `RatesManager` MUST attempt to read the `forecasts` array from the `attributes` of the primary Import and Export entities provided in the configuration.
- **FR-003**: `RatesManager` MUST extract the base price from `advanced_price_predicted.predicted` (falling back to `per_kwh` if the advanced dictionary is missing for the current half-hour block).
- **FR-004**: `RatesManager` MUST apply a linear blend to the price based on the `renewables` percentage in the interval:
  - If `renewables >= 35%`: Use 100% `predicted` price.
  - If `renewables <= 25%`: Use 100% `high` price from the `advanced_price_predicted` dictionary.
  - If `25% < renewables < 35%`: Linearly interpolate between the `predicted` and `high` prices.
- **FR-005**: `RatesManager` MUST correctly parse the `start_time` and `end_time` ISO strings from the Amber Express dictionary into native datetime objects.
- **FR-006**: If the system is NOT in Amber Express mode, `RatesManager` MUST fall back to the existing parser behavior (e.g., standard HA arrays or fallback values).
- **FR-007**: The system MUST handle cases where the `forecasts` attribute is intermittently missing or empty gracefully, reverting to a single fallback entry matching the current state.

### Key Entities 

- **Amber Express Sensor Attribute Structure**: 
  - `state`: current price float
  - `attributes.forecasts`: List of dictionaries containing `start_time`, `end_time`, `per_kwh`, `renewables`, and an `advanced_price_predicted` dictionary (containing `low`, `predicted`, `high`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users with Amber Express sensors can successfully operate the HBC integration with accurate LP solver planning spanning at least 24 hours into the future.
- **SC-002**: Existing users run unaffected without regressions in rate parsing.
- **SC-003**: 100% test coverage on the new `RatesManager.get_rates` split logic.
