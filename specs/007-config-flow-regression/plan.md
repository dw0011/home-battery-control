# Implementation Plan: Config Flow Options Regression

**Branch**: `007-config-flow-regression` | **Date**: 2026-02-26 | **Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/007-config-flow-regression/spec.md)

## Summary

Restore the Options flow Control step with a persisted **observation mode** toggle and proper entity-clearing support. The observation mode gate is added to the executor's `apply_state()` method so that script execution is suppressed without destroying the stored script references.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: Home Assistant Core, voluptuous (schema validation)  
**Testing**: pytest  
**Target Platform**: Home Assistant custom component (HACS)

## File Changes

### 1. const.py — New constant

Add `CONF_OBSERVATION_MODE = "observation_mode"` alongside the existing control constants.

---

### 2. config_flow.py — Options flow control step

Replace `HBCOptionsFlowHandler.async_step_control` with:

- **Observation Mode toggle**: `vol.Optional(CONF_OBSERVATION_MODE, default=...)` — persisted boolean, defaults to current stored value or `False`.
- **4 script selectors**: Same as current, but using `suggested_value` pattern for clearability.
- **Panel Admin Only**: Same as current.
- **Submission handler**:
  - Store observation_mode in persistent config data.
  - For each entity selector: if value is `None` or `""`, pop the key from `self._data`. Otherwise store the value.

No changes to the initial config flow (`ConfigFlow.async_step_control`).
No changes to `async_step_manual` or `async_step_energy`.

---

### 3. execute.py — Observation mode gate

Add an early return in `apply_state()`:

```python
if self._config.get(CONF_OBSERVATION_MODE, False):
    _LOGGER.info("Observation mode — skipping command execution")
    return
```

This goes before the deduplication check so the executor does not even track state when observation mode is on. The state/limit tracking remains stale, meaning when observation mode is toggled off, the next solver run will always apply (since stored last_state won't match).

---

### 4. strings.json — Options control section

Replace `options.step.control` with labels for:
- `observation_mode`: "Observation Mode (suppress all commands)"
- `script_charge`: "Script: Charge from Grid"
- `script_charge_stop`: "Script: Stop Charging"
- `script_discharge`: "Script: Discharge to Grid"
- `script_discharge_stop`: "Script: Stop Discharging"
- `panel_admin_only`: "Panel visible to admins only"

Update description to: "Control script configuration. Enable Observation Mode to suppress commands while keeping scripts configured."

---

### 5. translations/en.json — Same labels

Mirror the `strings.json` changes into `options.step.control`.

## Verification Plan

### Automated Tests
- `pytest tests/test_config_flow.py -v`
- `pytest tests/ -v` (full suite — all 134 tests must pass)

### Manual Verification
- Deploy to HA via HACS
- Open Options → Control, verify all 6 fields with correct labels
- Toggle observation mode on, verify no scripts are called
- Toggle off, verify execution resumes
- Clear a single script entity, verify key is removed from config
