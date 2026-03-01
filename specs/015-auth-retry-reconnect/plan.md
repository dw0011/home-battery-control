# Implementation Plan: Auth Retry on Reconnect

**Branch**: `015-auth-retry-reconnect` | **Date**: 2026-02-28 | **Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/015-auth-retry-reconnect/spec.md)

## Summary

When Chrome backgrounds the HBC tab, the WebSocket drops and `this.hass` auth state goes stale. `fetchWithAuth` can't refresh the token → 401. Fix: on 401, wait 3 seconds (HA reconnects WebSocket when tab regains focus), retry once.

## Technical Context

**File**: `custom_components/house_battery_control/frontend/hbc-panel.js`  
**Method**: `_fetchData()` (line 46)  
**Root cause**: Browser suspends WebSocket → `this.hass.auth` stale → `fetchWithAuth` returns 401

## Changes

### [MODIFY] hbc-panel.js — `_fetchData()` (lines 46-67)

Replace the immediate 401→error with a single retry after 3-second delay:

```javascript
async _fetchData() {
  try {
    if (!this.hass) {
      this._error = "Home Assistant connection not available";
      this._loading = false;
      return;
    }
    const resp = await this.hass.fetchWithAuth("/hbc/api/status");
    if (resp.status === 401) {
      // Tab may have been idle — wait for HA to reconnect, retry once
      await new Promise(r => setTimeout(r, 3000));
      const retry = await this.hass.fetchWithAuth("/hbc/api/status");
      if (retry.status === 401) {
        this._error = "Insufficient permissions — admin access required";
        this._loading = false;
        return;
      }
      if (!retry.ok) throw new Error(`HTTP ${retry.status}`);
      this._data = await retry.json();
      this._error = "";
      this._loading = false;
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    this._data = await resp.json();
    this._error = "";
  } catch (e) {
    this._error = e.message || String(e);
  }
  this._loading = false;
}
```

**Key changes**:
1. On first 401: wait 3 seconds for HA WebSocket to reconnect
2. Retry `fetchWithAuth` once with fresh auth state
3. Only show permissions error if BOTH attempts fail
4. Network errors still caught by try/catch — no false permission messages

### [MODIFY] `__init__.py` — bump JS cache buster

```diff
-"module_url": "/hbc/frontend/hbc-panel.js?v=48",
+"module_url": "/hbc/frontend/hbc-panel.js?v=49",
```

## No Backend Changes

Endpoint `requires_auth = True` is correct. The problem is client-side auth state, not server-side.

## Verification

```bash
pytest tests/ -v          # 150 tests must pass
ruff check custom_components/ tests/   # clean
```

Manual: Open panel, switch to another tab for 2+ hours, return — data should resume within 5 seconds.
