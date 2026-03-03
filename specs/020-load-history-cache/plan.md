# Implementation Plan: Load History Daily Cache (020)

**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/020-load-history-cache/spec.md)  
**Issue**: #16  
**Version**: v1.4.1 (patch — internal optimisation, no behaviour change)

## Proposed Changes

All changes in **one file**: `load.py`. No coordinator changes needed.

---

### LoadPredictor Cache State

#### [MODIFY] [load.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/load.py)

**Change 1 — Add cache fields to `__init__` (L13-16)**

```diff
 def __init__(self, hass: HomeAssistant):
     self._hass = hass
     self.last_history_raw: list[list[dict]] = []
     self.last_history: list[dict] = []
+    # Daily cache (Feature 020)
+    self._cached_profile: dict | None = None
+    self._cached_temp_data: Any = None
+    self._cache_date: date | None = None  # date the cache was built FOR
+    self._is_energy_sensor: bool = False   # cached sensor type
```

**Change 2 — Extract cache-check method and refactor `async_predict` (L55-145)**

Current flow:
```
async_predict() called every 5 min:
  → fetch 5-day load history from recorder (L56-93)
  → parse & extract valid data (L96-105)
  → fetch 5-day temp history from recorder (L107-139)
  → build profile from parsed data (L141-145)
  → generate predictions from profile (L147-233)
```

New flow:
```
async_predict() called every 5 min:
  → check: is cache valid? (same calendar day AND cache exists)
    YES → skip DB, use self._cached_profile + self._cached_temp_data
    NO  → fetch 5 complete days (end_date = start_of_today 00:00)
         → use recorder.get_instance(hass).async_add_executor_job() (FR-005)
         → build profile → cache it, set self._cache_date = today
  → generate predictions from profile (unchanged)
```

Key implementation detail for the 00:05 refresh (FR-002):

```python
from datetime import date, time, timedelta
import homeassistant.util.dt as dt_util

def _cache_is_valid(self) -> bool:
    """Cache is valid if it was built for today's date.
    
    After 00:05 local time, 'today's date' advances — meaning yesterday's
    cache is now stale. Before 00:05, we still consider yesterday's date
    as current to avoid a premature refresh at midnight.
    """
    if self._cached_profile is None or self._cache_date is None:
        return False
    now = dt_util.now()
    effective_date = (now - timedelta(minutes=5)).date()  # before 00:05 → yesterday
    return self._cache_date == effective_date
```

This elegantly handles the 00:05 rule: subtracting 5 minutes from `now()` means at 00:04 the effective date is yesterday (cache valid), at 00:06 the effective date is today (cache stale → refresh).

**Change 3 — Fix recorder executor (FR-005)**

Both DB calls change from:
```python
# BEFORE
await self._hass.async_add_executor_job(
    history.get_significant_states, ...
)
```
to:
```python
# AFTER
from homeassistant.components.recorder import get_instance
await get_instance(self._hass).async_add_executor_job(
    history.get_significant_states, ...
)
```

**Change 4 — Fix date window to 5 complete days (FR-001a)**

```python
# BEFORE
end_date = start_time
start_date = end_date - timedelta(days=5)

# AFTER
end_date = dt_util.start_of_local_day()  # midnight today — no partial today data
start_date = end_date - timedelta(days=5)
```

---

## Summary of Changes

| # | What | Where | FR |
|---|------|-------|----|
| 1 | Add cache fields | `__init__` L13-16 | FR-001 |
| 2 | Cache check + skip logic | `async_predict` L55-145 | FR-001, FR-002, FR-003, FR-004, FR-007 |
| 3 | Recorder executor fix | L63, L116 | FR-005 |
| 4 | Date window fix | L59-60, L113-114 | FR-001a |

## Verification Plan

### Automated Tests
- Existing tests continue to pass (they use `testing_bypass_history` — unaffected)
- New test: verify `_cache_is_valid()` returns `False` on first call, `True` on second call within same day
- New test: verify `_cache_is_valid()` returns `False` after 00:05 boundary (freeze time)
- New test: verify `get_significant_states` is called only once across 2 consecutive `async_predict` calls

### Manual Verification
- Deploy to HA, check logs for absence of `database without the database executor` warning
- Confirm load forecast unchanged in dashboard
