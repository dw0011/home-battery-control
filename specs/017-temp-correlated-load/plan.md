# Implementation Plan: Temperature-Correlated Load Prediction

**Branch**: `017-temp-correlated-load` | **Date**: 2026-03-02 | **Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/017-temp-correlated-load/spec.md)

## Summary

Replace the absolute-threshold temperature adjustment with a delta-based approach. Fetch outdoor temperature history from the existing `weather_entity` alongside load history, build a per-slot temperature average, then adjust load based on `forecast_temp - historical_avg_temp` instead of `forecast_temp - threshold`.

## Technical Approach

### Current flow
```
load history (5 days) → build_historical_profile() → { "14:00": 2.5 }
forecast temp → if > 25°C: load += (temp - 25) × 0.2
```

### New flow
```
load history (5 days) → │
                        ├→ build_historical_profile() → { "14:00": { "load_kw": 2.5, "avg_temp": 28.3 } }
temp history (5 days) → │

forecast temp for slot → temp_delta = forecast - avg_temp_for_slot
if delta > 0 AND forecast > high_threshold: load += delta × high_sensitivity
if delta < 0 AND forecast < low_threshold: load += abs(delta) × low_sensitivity
```

## Changes

---

### [MODIFY] historical_analyzer.py — Add temperature averaging

#### `build_historical_profile()` — new parameter + dual return

```python
def build_historical_profile(
    valid_data: list, target_tz=None, is_energy_sensor: bool = True,
    temp_data: list | None = None,  # NEW: list of {"time": timestamp, "value": float}
) -> dict:
```

Inside the interval loop, for each 5-min slot:
- Existing: accumulate `slot_sums[time_slot]` for load
- New: also accumulate `temp_sums[time_slot]` by interpolating temp at current_t

Return format changes from:
```python
{ "14:00": 2.5 }
```
to:
```python
{ "14:00": {"load_kw": 2.5, "avg_temp": 28.3} }
```

When `temp_data` is None, return `{"load_kw": X, "avg_temp": None}` per slot (backward compatible).

#### New function: `extract_temp_data()`

```python
def extract_temp_data(historic_states_parsed: list) -> list:
    """Parse weather entity history into time-sorted temp values."""
```

Same pattern as `extract_valid_data()` but extracts the `temperature` attribute or the state value (weather entities have temp as their state).

---

### [MODIFY] load.py — Fetch temp history, use delta adjustment

#### `async_predict()` — new parameter

```python
async def async_predict(
    self,
    start_time: datetime,
    temp_forecast: List[Any] | None = None,
    high_sensitivity: float = 0.0,
    low_sensitivity: float = 0.0,
    high_threshold: float = 25.0,
    low_threshold: float = 15.0,
    duration_hours: int = 24,
    load_entity_id: str | None = None,
    weather_entity_id: str | None = None,  # NEW
) -> List[dict]:
```

**New logic** between history fetch and prediction loop:

1. If `weather_entity_id` is provided, fetch its 5-day history via `get_significant_states` (same pattern as load)
2. Parse via `extract_temp_data()`
3. Pass `temp_data` to `build_historical_profile()`

**Replace temperature adjustment** (lines 147-151):

```python
# OLD: absolute threshold
if temp > high_threshold:
    derived_kw += (temp - high_threshold) * high_sensitivity

# NEW: delta-based
slot_hist_temp = historical_profile[time_slot].get("avg_temp")
if slot_hist_temp is not None:
    temp_delta = temp - slot_hist_temp
    if temp_delta > 0 and temp > high_threshold:
        derived_kw += temp_delta * high_sensitivity
    elif temp_delta < 0 and temp < low_threshold:
        derived_kw += abs(temp_delta) * low_sensitivity
else:
    # Fallback: original absolute threshold (FR-008)
    if temp > high_threshold:
        derived_kw += (temp - high_threshold) * high_sensitivity
    elif temp < low_threshold:
        derived_kw += (low_threshold - temp) * low_sensitivity
```

**Update profile access** — historical_profile values change from float to dict:

```python
# OLD
derived_kw = historical_profile[time_slot] * 12.0

# NEW
slot_data = historical_profile[time_slot]
derived_kw = slot_data["load_kw"] * 12.0 if is_energy_sensor else slot_data["load_kw"]
```

---

### [MODIFY] coordinator.py — Pass weather entity ID

```diff
  load_forecast = await self.load_predictor.async_predict(
      start_time=start_time,
      temp_forecast=self.weather.get_forecast(),
      high_sensitivity=self.config.get(CONF_LOAD_SENSITIVITY_HIGH_TEMP, 0.2),
      low_sensitivity=self.config.get(CONF_LOAD_SENSITIVITY_LOW_TEMP, 0.3),
      high_threshold=self.config.get(CONF_LOAD_HIGH_TEMP_THRESHOLD, 25.0),
      low_threshold=self.config.get(CONF_LOAD_LOW_TEMP_THRESHOLD, 15.0),
      load_entity_id=self.config.get(CONF_LOAD_TODAY_ENTITY, ""),
+     weather_entity_id=self.config.get(CONF_WEATHER_ENTITY, ""),
  )
```

No new config needed — `CONF_WEATHER_ENTITY` already exists.

---

### No changes to config_flow.py, weather.py, web.py, or frontend

---

## Tests

### Existing test updates

- `test_load.py` — update mock historical_profile to return `{"load_kw": X, "avg_temp": Y}` format
- Any test mocking `build_historical_profile` return value needs updating

### New tests

- `test_load.py`:
  - Test delta adjustment: history 20°C, forecast 35°C → load += 15 × sensitivity
  - Test zero delta: history 30°C, forecast 30°C → no adjustment
  - Test within band: history 20°C, forecast 22°C (both within thresholds) → no adjustment
  - Test fallback: no temp_data → original absolute threshold behaviour
  - Test cold snap: history 18°C, forecast 8°C → load += 10 × low_sensitivity

- `test_historical_analyzer.py`:
  - Test `extract_temp_data()` parsing
  - Test `build_historical_profile()` with temp_data returns dual format
  - Test `build_historical_profile()` without temp_data returns `avg_temp: None`

## Verification

```bash
pytest tests/ -v          # all tests pass
ruff check custom_components/ tests/   # clean
```

Manual: Compare predicted load with and without temp history — confirm delta-based adjustment produces more realistic values on extreme temperature days.
