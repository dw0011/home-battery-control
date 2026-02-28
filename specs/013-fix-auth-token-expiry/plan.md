# Implementation Plan: Fix Auth Token Expiry

**Branch**: `013-fix-auth-token-expiry` | **Date**: 2026-02-28 | **Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/013-fix-auth-token-expiry/spec.md)

## Summary

The HBC dashboard panel uses `fetch()` with a manually extracted `hass.auth.data.access_token`. HA's short-lived tokens expire after ~30 minutes, causing 401 errors on the 30-second polling cycle. Fix: use HA's `this.hass.fetchWithAuth()` which auto-refreshes tokens.

## Technical Context

**Language/Version**: JavaScript (ES modules via LitElement 2.4.0)  
**Primary Dependencies**: Home Assistant Frontend SDK (`hass` object)  
**Storage**: N/A  
**Testing**: pytest (backend only — no JS unit tests exist)  
**Target Platform**: Home Assistant Frontend (Browser)  
**Project Type**: Single integration (HA custom component)  
**Constraints**: Must work with HA's built-in panel framework; no additional JS dependencies

## Research

### Decision: Use `this.hass.fetchWithAuth()`

**Rationale**: HA's `hass` object provides `fetchWithAuth(url, init)` which wraps the native `fetch()` API but automatically:
1. Attaches the current valid access token
2. Intercepts 401 responses
3. Refreshes the token using the stored refresh token
4. Retries the original request with the new token

This is the blessed pattern for custom panels accessing non-`/api/` endpoints. `hass.callApi()` cannot be used because it prepends `/api/` to all paths, but our endpoint is at `/hbc/api/status`.

**Alternatives considered**:
- `hass.callApi("GET", "hbc/api/status")` — Rejected: prepends `/api/` → hits `/api/hbc/api/status` (404)
- Manual token refresh via `hass.auth.refreshAccessToken()` — Rejected: unnecessarily complex, `fetchWithAuth` handles this internally

## Project Structure

### Files Modified

```text
custom_components/house_battery_control/frontend/
└── hbc-panel.js    # MODIFY: _fetchData() method only
```

No backend changes. No new files. No new dependencies.

## Detailed Changes

### [MODIFY] hbc-panel.js — `_fetchData()` method (lines 46-65)

**Before** (current):
```javascript
async _fetchData() {
  try {
    const token = this.hass && this.hass.auth && this.hass.auth.data
      ? this.hass.auth.data.access_token
      : null;
    const headers = token ? { "Authorization": `Bearer ${token}` } : {};
    const resp = await fetch("/hbc/api/status", { headers });
    // ...
```

**After** (proposed):
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
      this._error = "Insufficient permissions — admin access required";
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
1. Guard `this.hass` null check (FR-004)
2. Replace `fetch()` + manual token with `this.hass.fetchWithAuth()` (FR-001, FR-002)
3. Keep 401 handling for non-admin users (FR-003)
4. Simplify error handling

## Verification Plan

### Automated Tests
```bash
pytest tests/ -v          # 150 tests must pass (no regression)
ruff check custom_components/ tests/   # Linter clean
```

### Manual Verification
1. Deploy to HA via `/update-ha`
2. Open HBC panel in sidebar
3. Leave panel open for 60+ minutes without refreshing
4. Confirm data continues updating (SC-001)
5. Check HA logs — no 401 errors (SC-002)
