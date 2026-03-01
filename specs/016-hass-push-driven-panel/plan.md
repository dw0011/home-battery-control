# Implementation Plan: Push-Driven Panel Updates

**Branch**: `016-hass-push-driven-panel` | **Date**: 2026-03-01 | **Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/016-hass-push-driven-panel/spec.md)

## Summary

Replace `setInterval(30s)` HTTP polling with LitElement's `updated()` lifecycle reacting to `this.hass` changes. When HA pushes a new `hass` object (which happens on any entity state change), the panel checks if `sensor.hbc_state` has changed and fetches fresh data from `/hbc/api/status`. A 10-second debounce prevents redundant fetches. A 60-second fallback timer catches edge cases.

## Technical Approach

### How HA pushes data to custom panels

1. Coordinator updates data → `sensor.hbc_state` entity value changes
2. HA frontend detects entity change → calls `set hass(newHass)` on custom panel element
3. LitElement marks `hass` property as changed → triggers `updated(changedProps)`
4. Panel detects `hass` in `changedProps` → debounced fetch

### Why this survives tab backgrounding

When Chrome freezes the tab, the WebSocket disconnects. On tab refocus, HA **immediately** reconnects the WebSocket and pushes the full current `hass` state. This triggers `updated()` → data refreshes automatically. No timer needed.

## Changes

### [MODIFY] hbc-panel.js — 3 areas

#### 1. Remove `setInterval` polling (lines 35-44)

```diff
  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
-   this._interval = setInterval(() => this._fetchData(), 30000);
+   // Fallback timer: 60s catch-all for edge cases (FR-004)
+   this._fallbackInterval = setInterval(() => this._fetchData(), 60000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
-   if (this._interval) clearInterval(this._interval);
+   if (this._fallbackInterval) clearInterval(this._fallbackInterval);
  }
```

#### 2. Add `updated()` lifecycle hook (new method, after `disconnectedCallback`)

```javascript
updated(changedProps) {
  super.updated(changedProps);
  if (!changedProps.has("hass")) return;
  // Check if HBC state entity changed — triggers data refresh
  const oldHass = changedProps.get("hass");
  if (!oldHass) {
    // First hass assignment — fetch immediately
    this._fetchData();
    return;
  }
  const oldState = oldHass.states["sensor.hbc_state"];
  const newState = this.hass.states["sensor.hbc_state"];
  if (!oldState || !newState) return;
  if (oldState.state !== newState.state || oldState.last_updated !== newState.last_updated) {
    // Entity changed — debounced fetch
    this._debouncedFetch();
  }
}
```

#### 3. Add debounce helper (new method)

```javascript
_debouncedFetch() {
  const now = Date.now();
  if (this._lastFetch && (now - this._lastFetch) < 10000) return; // 10s debounce
  this._lastFetch = now;
  this._fetchData();
}
```

#### 4. Update constructor (add `_lastFetch` field)

```diff
  constructor() {
    super();
    ...
-   this._interval = null;
+   this._fallbackInterval = null;
+   this._lastFetch = 0;
  }
```

### [MODIFY] `__init__.py` — bump JS cache buster

```diff
-"module_url": "/hbc/frontend/hbc-panel.js?v=48",
+"module_url": "/hbc/frontend/hbc-panel.js?v=50",
```

## No Backend Changes

The coordinator already updates `sensor.hbc_state` on every cycle. No new events or API changes needed.

## Verification

```bash
pytest tests/ -v          # all tests must pass
ruff check custom_components/ tests/   # clean
```

Manual:
1. Open panel, confirm data loads
2. Leave tab idle 2+ hours, return — data resumes automatically
3. Trigger coordinator update (reload integration) — panel updates within seconds
