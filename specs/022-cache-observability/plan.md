# Implementation Plan: Load Cache Observability (Feature 022)

## Goal

Expose load history cache metadata (last refresh timestamp, effective date) in the API and plan view so users can verify cache freshness during debugging.

## Proposed Changes

### LoadPredictor (`load.py`)

#### [MODIFY] [load.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/load.py)

**FR-001**: Add `_cache_refreshed_at` timestamp field to `__init__` (L15-21). Set it alongside `_cache_date` at L250-252 when cache is written.

Add two read-only properties:
```python
@property
def cache_date(self) -> date | None:
    return self._cache_date

@property
def cache_refreshed_at(self) -> datetime | None:
    return self._cache_refreshed_at
```

---

### Coordinator (`coordinator.py`)

#### [MODIFY] [coordinator.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/coordinator.py)

**FR-002**: Add two fields to the return dict at L578-579:
```python
"load_cache_date": str(self.load_predictor.cache_date) if self.load_predictor.cache_date else None,
"load_cache_refreshed_at": self.load_predictor.cache_refreshed_at.isoformat() if self.load_predictor.cache_refreshed_at else None,
```

---

### Plan View JS (`hbc-panel.js`)

#### [MODIFY] [hbc-panel.js](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/frontend/hbc-panel.js)

**FR-003/FR-004**: Add a cache status subtitle after the `<h2>` at L516, before the resolution buttons at L517.

Display format:
- When cached: `Load history cached: [date] (refreshed [HH:MM])`
- When not cached: `Load history: fetching…`

Style: small font, muted opacity, matching the existing "Updated:" style.

---

### Tests (`test_load.py`)

#### [MODIFY] [test_load.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_load.py)

**SC-004**: Add one test verifying `cache_date` and `cache_refreshed_at` are `None` before first call and populated after.

## Verification Plan

### Automated Tests
```bash
pytest tests/ -q --tb=short
```
All 177 existing + 1 new test must pass.

### Manual Verification
Deploy beta on `022-cache-observability` branch. Check plan tab shows cache status line with correct date and time.
