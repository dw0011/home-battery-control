# Tasks: Panel Navigation Fix (008)

**Branch**: `008-panel-navigation-fix`  
**Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/008-panel-navigation-fix/spec.md)  
**Plan**: [plan.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/008-panel-navigation-fix/plan.md)

## Phase 1: Implementation
- [ ] T001 Add `_toggleMenu()` method to HBCPanel class in `hbc-panel.js`
- [ ] T002 Add toolbar HTML to `render()` replacing the standalone h1 header
- [ ] T003 Add toolbar CSS styles
- [ ] T004 Bump cache version in `__init__.py` module_url

## Phase 2: Verification
- [ ] T005 Run `pytest tests/ -v` (full suite)
- [ ] T006 Deploy to HA, verify menu button toggles sidebar on desktop
- [ ] T007 Post response to GitHub issue #3

## Dependencies
- T002 depends on T001 (toolbar references _toggleMenu)
- T003 is independent (CSS)
- T004 is independent
- T005-T007 depend on T001-T004
