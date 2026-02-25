# Tasks: User Documentation

**Feature Branch**: `03-documentation`  
**Plan**: [plan.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/03-documentation/plan.md)  
**Generated**: 2026-02-25

## Phase 1: Fix Manifest (no deps)

- [ ] T001 Fix `documentation` URL in manifest.json → `https://github.com/RangeyRover/home-battery-control`
- [ ] T002 Fix `issue_tracker` URL in manifest.json → `https://github.com/RangeyRover/home-battery-control/issues`

## Phase 2: README Rewrite (depends on nothing)

- [ ] T003 Rewrite README.md with: badges, prerequisites table, HACS install steps, config flow summary, verification guide, links to /docs
- [ ] T004 Remove stale references: plan table, `/hbc` URL, `24-hour plan table` mention

## Phase 3: /docs — Configuration Reference

- [ ] T005 Create `docs/configuration.md` — Step 1 (Telemetry) field reference table
- [ ] T006 Add Step 2 (Energy & Metrics) field reference table with defaults
- [ ] T007 Add Step 3 (Control Services) field reference table including `panel_admin_only`
- [ ] T008 Add Options Flow section explaining how to change settings post-install

## Phase 4: /docs — How It Works (deep-dive)

- [ ] T009 Create `docs/how-it-works.md` — Overview + data pipeline Mermaid flowchart
- [ ] T010 Write Inputs section: tariffs, solar, load, weather, battery state/config — all with field names, units, sample rates
- [ ] T011 Write Solver Objectives section: objective function, constraints, what it does NOT do
- [ ] T012 Write Outputs section: FSMResult fields, FSM states table, future_plan structure
- [ ] T013 Write Execution section: PowerwallExecutor state → script mapping table, deduplication
- [ ] T014 Write 5-Minute Cycle section: coordinator cadence, state change listeners

## Phase 5: /docs — Troubleshooting & Architecture

- [ ] T015 Create `docs/troubleshooting.md` — 7 FAQ entries with diagnostic steps
- [ ] T016 Create `docs/architecture.md` — module map table (19 files), data flow Mermaid, dev setup

## Phase 6: Verify & Commit

- [ ] T017 Run `pytest tests/ -v` — confirm no regressions (133 pass)
- [ ] T018 Commit and push to `03-documentation`
- [ ] T019 Merge to `main`, push, verify README renders on GitHub

## Parallel Opportunities
- T001 ∥ T002 (single edit in manifest.json)
- T003 ∥ T004 (single README rewrite)
- T005–T008 can be one file write
- T009–T014 can be one file write
- T015 ∥ T016 (independent files)
