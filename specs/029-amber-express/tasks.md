# Task Tracking: Amber Express Support

**Feature Branch**: `029-amber-express`
**Status**: In Progress

## Tasks

### 1. Configuration UI Updates
- [ ] In `const.py`, add `CONF_USE_AMBER_EXPRESS` ("use_amber_express") and a default of `False`.
- [ ] In `config_flow.py`, `async_step_energy`, append `vol.Optional(CONF_USE_AMBER_EXPRESS, default=False): BooleanSelector()` below the Price Entities.

### 2. Core Architecture Support
- [ ] In `coordinator.py::__init__`, inject the `CONF_USE_AMBER_EXPRESS` boolean into the `RatesManager` constructor.
- [ ] In `rates.py::__init__`, accept the `use_amber_express: bool = False` argument.
- [ ] In `rates.py::_parse_entity`, intercept `raw_data`. If `use_amber_express` is True, load the `forecasts` string directly from the state attributes.
- [ ] In `rates.py::_parse_entity` duration loop, extract `renewables`, `high`, and `predicted` keys from `advanced_price_predicted`.
- [ ] Implement the `price = predicted + (ratio * (high - predicted))` blending logic if renewables falls between 25.0 and 35.0. 
- [ ] Ensure `rates.py` continues properly parsing the prices into the native 5-minute ticks.

### 3. Verification & Testing
- [ ] Create or modify tests to supply an Amber Express mock dictionary to the `RatesManager`.
- [ ] Assert it accurately spawns 5-minute tickets for the solver.
- [ ] Run `pytest tests/` recursively.
- [ ] Commit `029-amber-express` branch.
