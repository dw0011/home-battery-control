# Feature Specification: Load History Daily Cache

**Feature Branch**: `020-load-history-cache`  
**Created**: 2026-03-03  
**Status**: Draft  
**Input**: GitHub Issue #16 — "Load history fetched every 5 min - should cache with daily refresh"

## Problem Statement

`LoadPredictor.async_predict()` fetches 5 days of recorder history (~8,640 DB rows) on **every 5-minute coordinator cycle**. This causes:

1. **~3,900 HA log warnings/day**: `Detected code that accesses the database without the database executor` — because the calls use `hass.async_add_executor_job()` instead of `recorder.get_instance(hass).async_add_executor_job()`.
2. **~2.5 million redundant row reads/day**: The 5-day statistical profile changes negligibly within any given day — 99.7% of reads return identical data.

## Core Mechanism

Cache the **computed historical profile** (the 288 time-slot averages produced by `build_historical_profile()`) on the `LoadPredictor` instance. Refresh it **once daily at 00:05** local time.

1. On first call after startup (no cache), fetch 5 completed calendar days from recorder (midnight yesterday back to midnight 6 days ago — **no partial today data**) and build profile → cache it.
2. On subsequent calls, check if local time has passed 00:05 since the last refresh → if yes, re-fetch previous 5 complete days and rebuild.
3. If cache is valid, skip the recorder call entirely and use the cached profile + cached temperature history.
4. Temperature **forecast** (live weather entity) remains fresh every cycle — only the **historical** side is cached.

## User Scenarios & Testing

### User Story 1 - Recorder Only Called Once Per Day (Priority: P1)

As a user, I want the integration to query the recorder database at most once per day, so that my HA instance isn't burdened by thousands of redundant history fetches.

**Acceptance Scenarios**:

1. **Given** the integration starts fresh, **When** the first coordinator cycle runs, **Then** the recorder is queried and the profile is cached.
2. **Given** a cached profile exists (built at 00:05), **When** a cycle runs at 14:30, **Then** the recorder is NOT queried — the cached profile is used.
3. **Given** a cached profile exists (built yesterday at 00:05), **When** a cycle runs at 00:06 today, **Then** the recorder IS queried and the cache is refreshed.

### User Story 2 - Recorder Executor Warning Eliminated (Priority: P1)

As a user, I want no `database without the database executor` warnings in my HA logs from this integration.

**Acceptance Scenarios**:

1. **Given** the daily fetch is triggered, **When** the recorder is called, **Then** it uses `recorder.get_instance(hass).async_add_executor_job()`.

### Edge Cases

- What if the integration restarts mid-day? Cache is empty → first cycle fetches previous 5 complete calendar days (no partial today), next refresh at 00:05.
- What if the recorder is unavailable at 00:05? Log a warning, keep the stale cache, retry next cycle.
- What if no load_entity_id is configured? No recorder call at all — no change from current behaviour.

## Requirements

### Functional Requirements

> [!NOTE]
> FR-001 through FR-005 should also be reflected in `system_requirements.md` under the Load Prediction section.

- **FR-001**: `LoadPredictor` MUST cache the computed historical profile (output of `build_historical_profile()`) and the historical temperature data in memory.
- **FR-001a**: The recorder query window MUST always be 5 completed calendar days: `end_date = start_of_today (00:00 local)`, `start_date = end_date - 5 days`. Today's partial data MUST NOT be included.
- **FR-002**: The cache MUST be refreshed when local time passes 00:05 and the cache was last built on a previous calendar day.
- **FR-003**: On first call with an empty cache (startup), the recorder MUST be queried immediately.
- **FR-004**: When the cache is valid, `async_predict()` MUST NOT call `history.get_significant_states`.
- **FR-005**: The recorder call MUST use `recorder.get_instance(hass).async_add_executor_job()` instead of `hass.async_add_executor_job()`.
- **FR-006**: Temperature forecast (live weather entity attributes) MUST remain fresh on every cycle — only the historical temperature averages are cached.
- **FR-007**: If the recorder call fails during the daily refresh, the stale cache MUST be retained and a warning logged.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After startup + first fetch, no `get_significant_states` calls occur until after 00:05 the next day.
- **SC-002**: No `database without the database executor` warnings from this integration in HA logs.
- **SC-003**: Load forecast quality is unchanged (same 5-day average profile, same temperature adjustments).
