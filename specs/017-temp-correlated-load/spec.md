# Feature Specification: Temperature-Correlated Load Prediction

**Feature Branch**: `017-temp-correlated-load`  
**Created**: 2026-03-02  
**Status**: Draft  
**Input**: "Temperature-correlated load prediction using historical temperature delta (GitHub Issue #13)"

## Problem Statement

Load predictions are inaccurate because the temperature adjustment in `load.py` uses absolute forecast thresholds without considering the temperature during the historical period. This causes:

- **Double-counting**: If the past 5 days were 30°C, the history already includes aircon load (~4kW). Adding more load because forecast >25°C double-counts.
- **Under-counting**: If the past 5 days were 20°C (no aircon) and tomorrow is 35°C, the 0.2 kW/degree sensitivity is far too low for a 4kW aircon system.
- **Same applies in winter**: History at 10°C already includes heating. Adjusting for <15°C adds phantom load.

**Root cause**: The historical load profile already embeds the HVAC response to the temperatures that occurred during those 5 days. The adjustment should only account for the **delta** between forecast and historical temperature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Load on Hot Day (Priority: P1)

As an HBC user in South Australia, I want the load prediction to correctly account for aircon usage on a 35°C day when the past 5 days were only 20°C, so the battery plan allocates enough energy for cooling.

**Independent Test**: Compare predicted load on a 35°C forecast day with history at 20°C vs 35°C. The 20°C-history case should show significantly higher predicted load (due to temperature delta). The 35°C-history case should show minimal adjustment (delta near zero).

**Acceptance Scenarios**:

1. **Given** 5-day history at avg 20°C and forecast of 35°C, **When** load is predicted for a 14:00 slot, **Then** load is increased by `(35-20) × high_sensitivity` kW compared to raw history.
2. **Given** 5-day history at avg 32°C and forecast of 33°C, **When** load is predicted, **Then** load adjustment is minimal (~1°C delta × sensitivity).
3. **Given** 5-day history at avg 25°C and forecast of 22°C, **When** both are within the configured threshold band (`low_threshold` to `high_threshold`), **Then** no temperature adjustment is applied.

### User Story 2 - Accurate Load on Cold Day (Priority: P1)

As an HBC user, I want the load prediction to correctly increase for heating load when a cold snap is forecast but history was mild.

**Acceptance Scenarios**:

1. **Given** 5-day history at avg 18°C and forecast of 8°C, **When** load is predicted, **Then** load is increased by `abs(8-18) × low_sensitivity` = `10 × low_sensitivity` kW (FR-005 delta formula).
2. **Given** 5-day history at avg 10°C and forecast of 10°C, **When** load is predicted, **Then** no adjustment (delta = 0, history already contains heating load).

### User Story 3 - Historical Temperature Stored Per Slot (Priority: P2)

As the system, I need to associate temperature with each 5-minute load slot in the historical profile, so the delta calculation has per-slot granularity (mornings may be cool while afternoons are hot).

---

### Edge Cases

- What if weather entity temperature history is unavailable? Fall back to current absolute threshold behaviour (FR-008).
- What if temperature history is unavailable for some slots? Use the overall average of available historical temperature data for those slots.
- What if the weather forecast doesn't cover all 24 hours? Use the last available forecast temperature.
- What if both delta AND absolute adjustments apply? Use ONLY the delta-based approach when historical temp data is available.
- What if forecast is cooler than hot history (e.g., history 35°C, forecast 28°C)? Apply negative adjustment — reduce predicted load (FR-009).
- Source compatibility (historical vs forecast temperature) is the user's responsibility when configuring entities.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST fetch outdoor temperature history for the same 5-day period used for load history.
- **FR-002**: The `build_historical_profile()` function MUST return both average load AND average temperature per 5-minute time slot.
- **FR-003**: The load prediction MUST calculate `temp_delta = forecast_temp - historical_avg_temp` for each slot.
- **FR-004**: When `forecast_temp > high_threshold`, the load MUST be adjusted by `temp_delta × high_sensitivity` (positive delta = increase, negative delta = decrease).
- **FR-005**: When `forecast_temp < low_threshold`, the load MUST be adjusted by `-temp_delta × low_sensitivity` (negative delta = colder = increase load, positive delta = warmer = decrease load).
- **FR-006**: When forecast temp is within the threshold band (`low_threshold` to `high_threshold`), NO temperature adjustment MUST be applied.
- **FR-007**: The system MUST use the existing configured `weather_entity` to fetch historical temperature data via `attributes.temperature` from recorder history.
- **FR-008**: If weather entity temperature history is unavailable, the system MUST fall back to the existing absolute threshold behaviour (backward compatibility).
- **FR-009**: Negative delta adjustments (reducing predicted load) MUST be applied without limit. The final predicted load per slot is naturally clamped at 0.0 kW since negative consumption is not physically possible.
- **FR-010**: Each prediction slot MUST include `temp_delta` (forecast temperature minus historical average temperature for that slot, or `null` if unavailable).
- **FR-011**: Each prediction slot MUST include `load_adjustment_kw` (the kW adjustment applied due to temperature delta, or `0.0` if no adjustment).

### Configuration

- **Existing** (no change): `high_sensitivity`, `low_sensitivity`, `high_threshold`, `low_threshold`, `weather_entity`
- **No new config needed**: The existing `weather_entity` stores temperature in `attributes.temperature`. Its historical values are available via HA's recorder history API.

### Data Model

Current historical profile per slot:
```
{ "14:00": 2.5 }  // just load kW
```

New historical profile per slot:
```
{ "14:00": { "load_kw": 2.5, "avg_temp": 28.3 } }
```

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Load prediction accuracy improves — predicted kWh within 15% of actual on days with >2°C delta from history.
- **SC-002**: No regression on days where forecast temp matches history (delta ≈ 0).
- **SC-003**: Backward compatible — no breakage when weather entity temperature history is unavailable.
- **SC-004**: All existing tests pass + new tests for delta calculation.
- **SC-005**: *(Deferred)* Historical temperature data exposure in coordinator/dashboard is out of scope for v1.
