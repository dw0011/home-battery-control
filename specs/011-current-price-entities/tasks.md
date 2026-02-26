# Feature Tasks: Current Price Entity Configuration

**Feature Branch**: `011-current-price-entities`  
**Specification**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)  

## Dependencies

- Phase 2 must complete before Phase 3.

## Phase 1: Setup

- [x] [T001] Verify no unstaged changes check out the `011-current-price-entities` branch. (c:\Users\markn\OneDrive - IXL Signalling\0-01 AI Programming\AI Coding\House Battery Control)

## Phase 2: Foundational Elements (Configuration Strings)

- [x] [T002] [P] Modify `custom_components/house_battery_control/const.py` to add `CONF_CURRENT_IMPORT_PRICE_ENTITY` and `CONF_CURRENT_EXPORT_PRICE_ENTITY`.
- [x] [T003] [P] Modify `custom_components/house_battery_control/translations/en.json` and `strings.json` to define labels and descriptions for these new current price entities and rename existing ones to "Import Price Forecast Entity".

## Phase 3: User Story 1 - Configure Current Price Entities

**Goal**: Expose new current price entities in configuration options.
**Independent Test**: Config flow UI shows the new entity selectors and creates valid config entry.

- [x] [T004] [US1] Update `async_step_energy` in `config_flow.py` for both `ConfigFlow` and `HBCOptionsFlowHandler` to request the new current price entity options.

## Phase 4: User Story 2 - Real-Time Dashboard Accuracy

**Goal**: Force `t=0` calculations and the dashboard `current_price` to bind exclusively to the real-time sensor states.
**Independent Test**: API response `/hbc/api/status` reflects actual instantaneous status and LP `g[0]` logic runs natively on it.

- [x] [T005] [US2] Update `coordinator.py` -> `_async_update_data` to fetch `current_price` and `current_export_price` natively from the respective current price entity states.
- [x] [T006] [US2] Fallback if entity is undefined or unavailable exactly as implemented prior (`rates.get_import_price_at(now)`).
- [x] [T007] [US2] Pass these extracted states into `FSMContext` cleanly.
- [x] [T008] [US2] Update `lin_fsm.py` -> `calculate_next_state` to explicitly override `price_buy[0]` and `price_sell[0]` with `context.current_price` and `context.current_export_price`.

## Phase 5: Polish & Cross-Cutting Concerns

- [x] [T009] Ensure all 146 tests fully pass and resolve mock/regression issues via `pytest tests/`.
- [x] [T010] Verify the changes inside `hbc-panel.js` natively receive the correct instantaneous `current_price`.
