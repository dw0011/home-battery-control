# Specification: Config Flow Options Regression

## 1. Description
The Options flow for the House Battery Control integration has regressed. Users who have already configured the integration cannot:
1. **Skip the Control step** — the `skip_control` checkbox (Debug / Observation Mode) that exists in the initial config flow is missing from the Options flow.
2. **Clear entity selections** — once a script entity is set, there is no way to clear it back to empty. Users are stuck with previously configured scripts even after deleting them.
3. **Access missing fields** — the Options flow control panel is missing `allow_charge_entity` and `allow_export_entity` fields that exist in the initial config flow.

### User-reported impact
> *"Since creating the scripts and setting them up, I can't seem to put HBC into a 'preview mode' or 'read only' mode, even deleting the scripts, they somehow find their way back in. I'm having issues with the current buy and sell price sometimes display $0.00 and that sends my Powerwall to start charging from the grid... all it wants to do is charge and I can't stop it any other way but to disable the integration at which point I can't really troubleshoot."*

## 2. Requirements

1. **R1: Restore skip_control checkbox in Options flow** — The Options flow Control step must include the `skip_control` boolean toggle, defaulting to the current stored value (or `False`). When checked, all control scripts must be cleared from the config entry data so the executor enters observation-only mode.
2. **R2: Add missing control entities to Options flow** — `allow_charge_entity` and `allow_export_entity` must appear in the Options flow Control step with the same selectors as the initial config flow.
3. **R3: Allow clearing entity selections** — All optional entity selectors in the Options flow Control step must support clearing (setting to empty/None).
4. **R4: Update strings.json** — The Options flow control section must include labels for `skip_control`, `allow_charge_entity`, `allow_export_entity`, and `panel_admin_only`.
5. **R5: No regression** — All existing tests must pass. The initial config flow must remain unchanged.

## 3. Assumptions
- The executor already handles missing scripts gracefully (via `.get()` returning `None`).
- Clearing a script entity means removing its key from the config entry data entirely.

## 4. Success Criteria
- [ ] User can open Options → Control and see the skip/observation mode checkbox.
- [ ] User can toggle skip on, submit, and the integration stops executing scripts.
- [ ] User can clear previously configured script entities.
- [ ] User can see and configure `allow_charge_entity` and `allow_export_entity` in Options.
- [ ] All existing tests pass without modification.
