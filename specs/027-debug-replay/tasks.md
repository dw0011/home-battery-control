# Tasks: 027 — Debug Replay Snapshot

## Task 1: Add snapshot infrastructure to coordinator.__init__
- [ ] Import `collections.deque`
- [ ] Add `self._solver_snapshot: dict | None = None`
- [ ] Add `self._state_transitions: deque = deque(maxlen=10)`
- [ ] Add `self._previous_state: str | None = None`

## Task 2: Build and store snapshot in _async_update_data
**Depends on**: Task 1
- [ ] After L618 (fsm_result), build snapshot dict from `fsm_context.solver_inputs`, config, acquisition_cost, and result
- [ ] Store as `self._solver_snapshot`
- [ ] If `fsm_result.state != self._previous_state` and previous is not None, appendleft to `self._state_transitions`
- [ ] Update `self._previous_state = fsm_result.state`

## Task 3: Expose in API response
**Depends on**: Task 2
- [ ] Add `"solver_snapshot": self._solver_snapshot` to the return dict (~L663-711)
- [ ] Add `"state_transitions": list(self._state_transitions)` to the return dict

## Task 4: Add tests
**Depends on**: Task 2
- [ ] Test snapshot is populated after FSM runs
- [ ] Test ring buffer captures state transitions
- [ ] Test ring buffer evicts oldest when full (>10)
- [ ] Test no capture when state unchanged

## Task 5: Run full test suite and commit
**Depends on**: Tasks 1-4
- [ ] `pytest tests/ -q --tb=short` — all tests pass
- [ ] Commit, merge to main, push, release
