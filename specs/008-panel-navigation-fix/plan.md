# Implementation Plan: Panel Navigation Fix (iOS)

**Branch**: `008-panel-navigation-fix` | **Date**: 2026-02-26 | **Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/008-panel-navigation-fix/spec.md)

## Summary

The HBC custom panel fills the entire viewport without a standard HA toolbar. On iOS mobile, where the sidebar is hidden by default, users have no way to navigate away. Fix by adding a top toolbar with a menu/back button that fires HA's `hass-toggle-menu` event.

## Technical Context

**Language/Version**: JavaScript (ES Modules, LitElement 2.4.0)  
**Primary Dependencies**: LitElement, Home Assistant frontend API  
**Testing**: Manual (iOS HA app), automated (existing pytest suite)  
**Target Platform**: Home Assistant custom panel (HACS)

## File Changes

### 1. hbc-panel.js — Add toolbar with menu button

**Location**: `custom_components/house_battery_control/frontend/hbc-panel.js`

**Changes**:

a) Add a `_toggleMenu()` method:
```javascript
_toggleMenu() {
  this.dispatchEvent(new Event("hass-toggle-menu", {
    bubbles: true,
    composed: true,
  }));
}
```

b) Update `render()` to add a toolbar above the existing content:
```html
<div class="toolbar">
  <button class="menu-btn" @click=${this._toggleMenu}>
    <ha-icon icon="mdi:menu"></ha-icon>
  </button>
  <div class="toolbar-title">House Battery Control</div>
  <div class="tabs">...</div>
</div>
```
The existing h1 header is replaced by the toolbar title. The Dashboard/Plan tabs move into the toolbar.

c) Add CSS for the toolbar:
- Fixed at top, full width
- `ha-icon` for the menu icon (HA's standard icon component)
- Responsive — on narrow layouts the title may shrink

**Fallback**: If `ha-icon` is not available (older HA versions), use the Unicode hamburger character `☰` as text fallback.

d) Bump the cache-bust version query param in `__init__.py`:
```python
"module_url": "/hbc/frontend/hbc-panel.js?v=46",
```

## Verification Plan

### Automated Tests
- `pytest tests/ -v` (full suite, 134 tests — no backend changes so should all pass)

### Manual Verification
- Deploy to HA via HACS
- Open HBC panel on desktop browser — verify menu button toggles sidebar
- User confirms iOS HA app behavior — menu button reveals sidebar
