# Tasks: 001-fix-cost-persistence

**Input**: Design documents from `/specs/001-fix-cost-persistence/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T000 [P] Review `tests/test_coordinator.py` to understand existing initialization and patching patterns to support testing HA `Store`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T001 Implement `Store` instantiation and the `async_load_stored_costs` method in `custom_components/house_battery_control/coordinator.py`.
- [ ] T002 Modify `custom_components/house_battery_control/__init__.py` to await the coordinator's `async_load_stored_costs` before triggering the first refresh.

**Checkpoint**: Foundation ready - the state loads from disk on boot.

---

## Phase 3: User Story 1 - Restarting Home Assistant Retains Costs (Priority: P1) 🎯 MVP

**Goal**: Cumulative cost and acquisition cost metrics persist across system restarts.

**Independent Test**: Can be tested by verifying values in the UI, restarting the Home Assistant core, and confirming the exact same values are restored upon restart.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T003 [US1] Write an isolation unit test in `tests/test_coordinator.py` validating that an empty/corrupted `Store` initializes with `0.00` cumulative and `10` c/kWh acquisition.
- [ ] T004 [US1] Write an isolation unit test in `tests/test_coordinator.py` validating that a valid `Store` accurately restores to exact memory equivalents.
- [ ] T005 [US1] Write an isolation unit test in `tests/test_coordinator.py` asserting that only the first interval (`future_plan[0]`) calculates/mutates the acquisition cost, and that changes are pushed to `Store.async_delay_save`.

### Implementation for User Story 1

- [ ] T006 [US1] Update `_async_update_data` in `custom_components/house_battery_control/coordinator.py` to use `self.acquisition_cost` instead of the hardcoded `0.06`.
- [ ] T007 [US1] Implement math logic in `_async_update_data` within `coordinator.py` to calculate the realized interval costs for the `future_plan[0]` timeslice, add to `self.cumulative_cost`, and compute the new weighted `self.acquisition_cost`.
- [ ] T008 [US1] Add a call to `self.store.async_delay_save(...)` at the end of `_async_update_data` if `self.cumulative_cost` or `self.acquisition_cost` changes.
- [ ] T009 [US1] Expose `self.cumulative_cost` natively to the UI state output dictionary rather than computing it mid-flight.

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T010 Run `pytest tests/test_coordinator.py` locally to confirm all tests pass cleanly.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T003, T004, and T005 test implementations can be handled in parallel.
- Once Foundational phase completes, User Story 1 can start directly.
