# Implementation Plan: Configurable Panel Visibility

**Feature Branch**: `02-panel-visibility`  
**Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/02-panel-visibility/spec.md)  
**Created**: 2026-02-25

## Technical Context

| Item | Current State |
|---|---|
| `__init__.py` line 81 | `require_admin=True` hardcoded |
| `const.py` | No panel visibility constant |
| `config_flow.py` | Options flow has `async_step_control` as final step — uses `BooleanSelector` pattern |
| `en.json` | No panel visibility translation key |

## Proposed Changes

### Component 1: Config Constant

#### [MODIFY] [const.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/const.py)

Add constant after line 42 (Scripts section):
```python
# Panel
CONF_PANEL_ADMIN_ONLY = "panel_admin_only"
```
Add default after line 48:
```python
DEFAULT_PANEL_ADMIN_ONLY = True
```

---

### Component 2: Options Flow

#### [MODIFY] [config_flow.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/config_flow.py)

1. Import `CONF_PANEL_ADMIN_ONLY` and `DEFAULT_PANEL_ADMIN_ONLY` from const.
2. Add a `BooleanSelector` field to `async_step_control` schema:
```python
vol.Optional(
    CONF_PANEL_ADMIN_ONLY,
    default=self._data.get(CONF_PANEL_ADMIN_ONLY, DEFAULT_PANEL_ADMIN_ONLY),
): BooleanSelector(),
```

---

### Component 3: Panel Registration

#### [MODIFY] [\_\_init\_\_.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/__init__.py)

1. Import `CONF_PANEL_ADMIN_ONLY` and `DEFAULT_PANEL_ADMIN_ONLY`.
2. Replace hardcoded `require_admin=True` (line 81) with:
```python
require_admin=config_data.get(CONF_PANEL_ADMIN_ONLY, DEFAULT_PANEL_ADMIN_ONLY),
```

---

### Component 4: Translations

#### [MODIFY] [en.json](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/translations/en.json)

Add `panel_admin_only` to the `options.step.control.data` section:
```json
"panel_admin_only": "Panel Visible to Admins Only"
```

---

### Component 5: Tests

#### [MODIFY] [test_init.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_init.py)

Add test: `test_panel_admin_only_constant_exists` — verify the constant is importable.

#### [MODIFY] [test_config_flow.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_config_flow.py)

Add test: `test_options_control_has_panel_visibility` — verify `CONF_PANEL_ADMIN_ONLY` appears in the control step schema.

## Verification Plan

### Automated Tests
```bash
pytest tests/ -v
```

### Manual Verification
1. Deploy to HA, open Options → Control step → see "Panel Visible to Admins Only" toggle
2. Toggle OFF, save, reload → non-admin user sees sidebar entry
3. Toggle ON, save, reload → non-admin user does NOT see sidebar entry

## Execution Order

1. `const.py` — add constant + default
2. `config_flow.py` — add to options schema
3. `__init__.py` — use config value for `require_admin`
4. `en.json` — add translation
5. Tests — add coverage
6. Run tests → commit → deploy
