# Feature Specification: Load Cache Observability

**Feature Branch**: `022-cache-observability`
**Created**: 2026-03-04
**Status**: Draft

## Problem Statement

After implementing load history caching (v1.4.3), there is no way for the user to observe:
- When the load cache was last refreshed
- What effective date the cached data covers
- Whether the data is fresh or stale

This makes debugging load prediction issues difficult — the user cannot tell if the cache has refreshed on schedule or if it's stuck on old data.

## User Scenarios & Testing

### User Story 1 — Cache Freshness Visible in Plan View (Priority: P1)

As a user viewing the plan table, I want to see when the load history was last fetched from the database so I know if the forecast is based on current data.

**Acceptance Scenarios**:

1. **Given** the plan tab is open, **When** load data has been cached, **Then** a subtitle/status line below the plan table header shows the cache date and last refresh timestamp.
2. **Given** the system has just restarted, **When** no cache exists yet, **Then** the status line shows "Fetching…" or "Not cached".

### User Story 2 — Cache Metadata in API (Priority: P1)

As a developer or debugger, I want the cache metadata included in the coordinator data so it can be inspected programmatically.

**Acceptance Scenarios**:

1. **Given** a coordinator update completes, **When** the cache is populated, **Then** the data dict includes `load_cache_date` and `load_cache_refreshed_at`.
2. **Given** no cache exists, **Then** both fields are `null`.

## Requirements

### Functional Requirements

- **FR-001**: `LoadPredictor` MUST expose cache metadata via a public method or properties: `cache_date` (effective date) and `cache_refreshed_at` (timestamp of last DB fetch).
- **FR-002**: Coordinator MUST include `load_cache_date` and `load_cache_refreshed_at` in its return dict.
- **FR-003**: The plan tab in `hbc-panel.js` MUST display a cache status line showing when load history was last refreshed and what date it covers.
- **FR-004**: When no cache exists (startup), the status line MUST show an appropriate "not yet cached" indicator.

## Assumptions

- Cache metadata is lightweight (two scalar values) — no performance impact.
- The plan tab already renders a header area where the status line can be added.

## Success Criteria

- **SC-001**: User can see cache refresh timestamp and date in the plan view.
- **SC-002**: Cache metadata is available in the coordinator data dict for programmatic access.
- **SC-003**: All existing tests continue to pass.
- **SC-004**: At least one new test verifies cache metadata is exposed correctly.
