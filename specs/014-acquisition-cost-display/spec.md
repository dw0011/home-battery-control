# Feature Specification: Acquisition Cost Display

**Feature Branch**: `014-acquisition-cost-display`  
**Created**: 2026-02-28  
**Status**: Draft  
**Input**: User description: "24 Hr forecast summary should have acquisition cost next to average cost — interesting to see if we managed to beat the average in our acquisitions, cosmetic change only (GitHub Issue #9)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Acquisition Cost in Forecast Summary (Priority: P1)

As an HBC user viewing the 24-hour forecast plan on my dashboard, I want to see my current battery acquisition cost displayed alongside the average forecast buy price, so I can quickly judge whether the optimizer is charging at better-than-average prices.

**Why this priority**: This is the entire feature — a single cosmetic addition to the existing plan summary that gives the user immediate feedback on optimizer performance.

**Independent Test**: Open the HBC panel Plan tab, confirm acquisition cost is visible next to the average buy price in the summary stats area.

**Acceptance Scenarios**:

1. **Given** the HBC panel Plan tab is open, **When** plan data is loaded, **Then** the summary section displays both "Avg Buy c/kWh" and "Acq Cost c/kWh" side by side.
2. **Given** the acquisition cost is lower than the average buy price, **When** viewing the summary, **Then** the user can visually compare the two values to confirm the optimizer is performing well.
3. **Given** no plan data is available yet (initial load), **When** viewing the summary, **Then** acquisition cost shows a sensible default (e.g., "—" or "0.0") without errors.

---

### Edge Cases

- What happens when acquisition cost is 0.0 (no stored energy)? Display "0.0" or "—".
- What happens when plan data has no entries? Summary section should handle empty gracefully.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Plan tab summary MUST display the current live acquisition cost (c/kWh) — the real-time weighted average cost of energy in the battery right now — alongside the average forecast buy price.
- **FR-002**: The acquisition cost value MUST come from the coordinator data (`acquisition_cost` field already present in API response).
- **FR-003**: The display MUST be cosmetic only — no changes to data flow, FSM logic, or coordinator behavior.

### Key Entities

- **acquisition_cost**: The weighted average cost of energy currently stored in the battery (c/kWh). Already computed by the coordinator and included in `/hbc/api/status` response.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Acquisition cost is visible on the Plan tab summary when plan data is present.
- **SC-002**: No regression — all 150 existing tests pass.
- **SC-003**: Change is purely cosmetic — no backend, FSM, or coordinator modifications.
