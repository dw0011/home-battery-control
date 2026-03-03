# Feature Specification: Load History Cache Fix (v2)

**Feature Branch**: `020-load-history-cache`
**Created**: 2026-03-03
**Status**: Fix for v1.4.1 regression
**Input**: v1.4.1 caused 214 kWh load forecasts — reverted in v1.4.2 hotfix

## Root Cause Analysis

v1.4.1 introduced two changes simultaneously:
1. **Date window change**: `end_date = start_time` → `end_date = dt_util.start_of_local_day()` (midnight today)
2. **Cache wrapping**: if/else gates around DB calls and profile rebuild

The combination broke load forecasting. The exact failure mode produced monotonically increasing load values (5.6 → 34 kW), suggesting either profile corruption or incorrect `is_energy_sensor` propagation through the cache path.

## Design Principle

**Minimal change to working code.** The v1.4.0 `load.py` works correctly. The cache should be the *only* addition — wrapping the existing working flow, not restructuring it.

## Revised Approach

1. **Keep `end_date = start_time`** — the original working date window. No midnight anchor.
2. **Cache the entire result** of `async_predict()` (the final prediction list), not the intermediate profile.
3. **TTL = 24 hours**. Refresh at 00:05 local time (same logic as before).
4. **On cache hit**: return the cached prediction list directly. Skip the entire function body.
5. **On cache miss**: run the original v1.4.0 code path unchanged, then cache the result.

This approach has zero risk of breaking the existing logic because the working code path is never modified — only gated.

## Requirements

### Functional Requirements

- **FR-001**: On cache miss, `async_predict()` MUST execute the identical code path as v1.4.0.
- **FR-002**: On cache hit, `async_predict()` MUST return the cached prediction list without any DB calls.
- **FR-003**: Cache MUST expire after 00:05 local time on the next calendar day.
- **FR-004**: On startup (empty cache), the first call MUST always be a cache miss.
- **FR-005**: The `testing_bypass_history` flag MUST bypass caching entirely (tests see original behaviour).

### Test Requirements

- **TR-001**: Existing tests MUST pass without modification (proves FR-001).
- **TR-002**: New test: two consecutive calls with same time → second call must NOT invoke `get_significant_states`.
- **TR-003**: New test: call at day1 noon, then call at day2 00:10 → second call MUST invoke `get_significant_states`.
- **TR-004**: New test: verify cached prediction has identical content to fresh prediction (same data in, same data out).

## Success Criteria

- **SC-001**: Dashboard shows normal load values (~0.5–3 kW typical) with cache enabled.
- **SC-002**: No `database without the database executor` warnings at reduced frequency (1/day vs 288/day).
- **SC-003**: All tests pass (existing + new).
