# Tasks for Bug 030: Solver Cumulative Cost Passthrough

## Phase 1: Context definition
- [x] Create Bug 030 specification (`specs/030-solver-cumulative-cost-passthrough/spec.md`)
- [x] Create Implementation Plan (`specs/030-solver-cumulative-cost-passthrough/plan.md`)
- [x] Raise GitHub Issue #27

## Phase 2: Implementation
- [ ] Modify `fsm/base.py` to add `cumulative_cost` to `FSMContext`.
- [ ] Modify `coordinator.py` to inject `self.cumulative_cost` into `FSMContext`.
- [ ] Modify `fsm/lin_fsm.py` to initialize `running_cum_cost = context.cumulative_cost`.

## Phase 3: Verification
- [ ] Run full test suite (`pytest tests/`).
- [ ] Manually verify API dashboard JSON to ensure `plan[0].cumulative_cost` is nonzero and matches the coordinator.
- [ ] Confirm frontend chart correctness.
