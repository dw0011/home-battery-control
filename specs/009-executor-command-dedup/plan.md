# Implementation Plan: Executor Command Deduplication Fix

**Branch**: `009-executor-command-dedup` | **Date**: 2026-02-26 | **Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/009-executor-command-dedup/spec.md)

## Summary

Split the single `_last_state` / `_last_limit` tracking into two pairs: one for "last requested" (dashboard display) and one for "last executed" (actual dedup gate). This ensures observation mode suppression doesn't permanently block execution when mode is toggled off.

## Technical Context

**File**: `custom_components/house_battery_control/execute.py`  
**Test File**: `tests/test_execute.py`  
**Impact**: Single file change + tests. No other files affected.

## Proposed Changes

### 1. execute.py — Refactor state tracking

**Current state** (3 variables):
```python
self._last_state: str | None = None      # tracks requested state
self._last_limit: float = 0.0             # tracks requested limit
self._apply_count: int = 0                # tracks request count
```

**New state** (5 variables):
```python
self._last_state: str | None = None           # last REQUESTED state (for dashboard)
self._last_limit: float = 0.0                  # last REQUESTED limit (for dashboard)
self._last_executed_state: str | None = None   # last EXECUTED state (for dedup)
self._last_executed_limit: float = 0.0          # last EXECUTED limit (for dedup)
self._apply_count: int = 0                     # total request count
```

**apply_state() logic change**:

```python
async def apply_state(self, state: str, limit_kw: float) -> None:
    # Always update requested state (for dashboard/diagnostics)
    self._last_state = state
    self._last_limit = limit_kw

    # Observation mode: track request but do not execute
    if self._config.get(CONF_OBSERVATION_MODE, False):
        _LOGGER.info(f"Observation mode — suppressing: {state} (limit: {limit_kw:.1f} kW)")
        return

    # Dedup: only execute if different from last EXECUTED state
    if state == self._last_executed_state and limit_kw == self._last_executed_limit:
        _LOGGER.debug(f"State unchanged ({state}), skipping execute")
        return

    self._apply_count += 1
    _LOGGER.info(f"Applying state: {state} (limit: {limit_kw:.1f} kW)")

    await self._async_execute_commands(state, limit_kw)

    # Only update executed state AFTER successful execution
    self._last_executed_state = state
    self._last_executed_limit = limit_kw
```

**Key changes**:
1. `_last_state` always updates immediately (dashboard can show what FSM wants)
2. Observation mode check comes BEFORE dedup (not after)
3. Dedup compares against `_last_executed_state` not `_last_state`
4. `_last_executed_state` only updates AFTER `_async_execute_commands()` succeeds

### 2. test_execute.py — Add observation mode tests

New tests:
- `test_observation_mode_suppresses_execution` — commands not called when observation_mode=True
- `test_observation_mode_exit_triggers_execution` — toggling observation_mode off then calling same state triggers execution
- `test_observation_mode_dedup_after_real_execution` — after real execution, same state is deduped normally

## Verification Plan

### Automated Tests
- `pytest tests/test_execute.py -v` (targeted)
- `pytest tests/ -v` (full suite, 134+ tests)

### Manual Verification
- Deploy to HA, enable observation mode, wait for state change, disable observation mode, verify command fires in HA logs.
