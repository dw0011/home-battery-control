# Feature Specification: Recorder Executor Fix

**Feature Branch**: `021-recorder-executor-fix`
**Created**: 2026-03-03
**Status**: Draft
**Input**: HA log warning — `Detected code that accesses the database without the database executor`

## Problem Statement

The `LoadPredictor` module fetches historical data from the Home Assistant recorder using the generic event loop executor (`hass.async_add_executor_job()`). HA expects recorder database operations to use the recorder's dedicated thread pool executor (`recorder.get_instance(hass).async_add_executor_job()`). Using the wrong executor generates a warning in the HA logs on every recorder call, even after the Feature 020 caching fix reduced the frequency from ~288/day to ~1/day.

## Core Mechanism

Replace the executor dispatch at all recorder call sites in `load.py` so that `history.get_significant_states` runs on the recorder's own executor rather than the general-purpose executor.

## User Scenarios & Testing

### User Story 1 — No Database Executor Warnings (Priority: P1)

As a user, I want zero `database without the database executor` warnings from this integration in my HA logs.

**Acceptance Scenarios**:

1. **Given** the integration starts fresh, **When** the daily history fetch runs, **Then** no `database without the database executor` warning appears in HA logs.
2. **Given** the integration restarts mid-day, **When** the startup fetch runs, **Then** no warning appears.

### Edge Cases

- What if `recorder.get_instance()` is unavailable (older HA)? Fall back to `hass.async_add_executor_job()` and log a one-time info message.

## Requirements

### Functional Requirements

- **FR-001**: Load history fetch MUST use `recorder.get_instance(hass).async_add_executor_job()` instead of `hass.async_add_executor_job()`.
- **FR-002**: Temperature history fetch MUST use the same recorder executor.
- **FR-003**: If `recorder.get_instance()` raises an exception (e.g. older HA), the code MUST fall back to `hass.async_add_executor_job()` and log a one-time info message.

## Assumptions

- The target HA version (2024.1.0+, per `manifest.json`) supports `recorder.get_instance()`.
- No behavioural change — same data fetched, same caching, just dispatched to the correct executor.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After deploying, zero `database without the database executor` warnings from this integration in HA logs.
- **SC-002**: Load forecast quality is unchanged.
- **SC-003**: All existing tests continue to pass.
