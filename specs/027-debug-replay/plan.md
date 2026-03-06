# Implementation Plan: Debug Replay Snapshot (027)

**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/027-debug-replay/spec.md)

## Changes

### coordinator.py

1. **`__init__`** (L87): Add `self._solver_snapshot = None` and `self._state_transitions = deque(maxlen=10)` and `self._previous_state = None`

2. **`_async_update_data`** (after L618): Build snapshot dict from `fsm_context.solver_inputs` + config + result. Store as `self._solver_snapshot`. If `fsm_result.state != self._previous_state`, append to `self._state_transitions`. Update `self._previous_state`.

3. **Return dict** (L663-711): Add `"solver_snapshot"` and `"state_transitions"` to the response.

### No other files modified for core feature. Tests added.

## Snapshot Format
```python
{
    "timestamp": "2026-03-06T01:25:00+00:00",
    "solver_inputs": {
        "price_buy": [...],       # 288 floats
        "price_sell": [...],      # 288 floats
        "load_kwh": [...],        # 288 floats
        "pv_kwh": [...],          # 288 floats
        "no_import_steps": [...]  # list of ints
    },
    "battery": {
        "soc": 74.3,
        "capacity": 27.0,
        "charge_rate_max": 6.3,
        "inverter_limit": 10.0,
        "round_trip_efficiency": 0.90,
        "reserve_soc": 0.0
    },
    "acquisition_cost": 0.078,
    "result": {
        "state": "CHARGE_GRID",
        "limit_kw": 6.3,
        "target_soc": 75.1
    }
}
```
