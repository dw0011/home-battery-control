# Feature Specification: User Documentation

**Feature Branch**: `03-documentation`  
**Created**: 2026-02-25  
**Status**: Draft  
**Input**: User description: "Documenting this so a new user can go from install all the way through to working. README and /docs."

## User Scenarios & Testing

### User Story 1 - New User Installs via HACS (Priority: P1)

A new user discovers HBC on GitHub or HACS. They read the README, understand the prerequisites, install via HACS, run the 3-step config flow, and see the HBC panel in their sidebar with live data.

**Why this priority**: The entire purpose of this documentation — turn a stranger into a working user.

**Independent Test**: A reader with HA + HACS can follow the README from top to bottom and have a working integration.

**Acceptance Scenarios**:

1. **Given** a user reads the README, **When** they follow the installation steps, **Then** they can add and configure the integration.
2. **Given** a user completes configuration, **When** they open the HBC panel, **Then** they see live power flow data and system status.

---

### User Story 2 - Existing User Tunes Options (Priority: P2)

A user who has installed HBC wants to adjust settings (battery capacity, temperature thresholds, panel visibility). They find the Options documentation and know how to change settings.

**Why this priority**: Users need guidance beyond initial install — the options flow has many fields.

**Independent Test**: A user can locate and follow the options reference and successfully change a setting.

**Acceptance Scenarios**:

1. **Given** an installed integration, **When** user reads /docs/configuration.md, **Then** they understand each option and its effect.

---

### User Story 3 - Curious User Explores the System Internals (Priority: P2)

A technically curious user wants to understand how HBC actually works under the hood. They want exquisite detail on the core interfaces — what goes in, what comes out, what each component does to the data as it flows through the pipeline. They do NOT need to understand linear programming or the mathematical formulation, but they need to understand the solver's *objectives and guidelines*: what it is trying to achieve, what constraints it respects, what trade-offs it makes, and how its output maps to physical battery actions.

**Why this priority**: This is the kind of documentation that builds trust and attracts contributors. Users who understand the system's decision-making can better tune their configuration and diagnose unexpected behavior.

**Independent Test**: A reader can trace the full data pipeline from "Amber publishes a new price" through to "Powerwall receives a charge command" and explain what each stage does, without needing to understand scipy.linprog.

**Acceptance Scenarios**:

1. **Given** a curious user reads /docs/how-it-works.md, **When** they look at the data flow section, **Then** they can identify every input (tariffs, PV forecast, load history, SoC, temperature) and every output (FSM state, battery command, cost estimate).
2. **Given** a curious user reads the solver objectives section, **When** they want to know why the system chose CHARGE_GRID at 3am, **Then** they understand the guidelines the solver uses (minimise daily cost, respect SoC bounds, respect charge rates) without needing to read any LP formulation.
3. **Given** a curious user reads the interface detail, **When** they examine the coordinator → solver → executor pipeline, **Then** they understand the exact data structures passed between each stage (field names, units, sample rates, array shapes).

---

### User Story 4 - User Troubleshoots an Issue (Priority: P2)

A user encounters a problem (sensors not loading, dashboard blank, FSM not acting). They find the troubleshooting docs and can diagnose common issues.

**Why this priority**: Reduces support burden and GitHub issues.

**Independent Test**: A user with a common issue can find the answer in /docs/troubleshooting.md.

**Acceptance Scenarios**:

1. **Given** a user has an issue, **When** they check troubleshooting docs, **Then** they find a relevant FAQ entry with steps.

---

### User Story 5 - Developer Contributes (Priority: P3)

A developer wants to contribute. They read the development section and can set up the dev environment, run tests, and understand the architecture.

**Why this priority**: Enables community contributions.

**Independent Test**: A developer can clone, install deps, and run `pytest` from the README alone.

---

### Edge Cases

- User installs without Amber Electric — what entities can they still use?
- User installs without Solcast — does the integration still load?
- User configures wrong entity (e.g. non-power sensor for battery power) — what happens?

## Requirements

### Functional Requirements

- **FR-001**: README.md MUST provide a complete install-to-working walkthrough including prerequisites, HACS install, config flow, and verification.
- **FR-002**: README.md MUST accurately reflect the current state of the integration (no plan table references, correct URLs, auth requirements).
- **FR-003**: /docs folder MUST contain detailed configuration reference (every config key, its type, default, and purpose).
- **FR-004**: /docs folder MUST contain a troubleshooting/FAQ guide.
- **FR-005**: README.md MUST include badges (HACS, HA version, license).
- **FR-006**: manifest.json documentation URL MUST point to the correct GitHub repo.
- **FR-007**: /docs MUST contain a "How It Works" deep-dive covering: all inputs/outputs with field names, units, and sample rates; the coordinator → solver → executor data pipeline; the solver's objectives and constraints in plain language (not LP formulation); FSM state mapping to physical Powerwall commands.

### Deliverables

| File | Purpose |
|---|---|
| `README.md` | Landing page: overview, prerequisites, install, quick-start, links to /docs |
| `docs/configuration.md` | Full config reference: every entity, option, default, and what it controls |
| `docs/how-it-works.md` | Deep-dive: data pipeline, solver objectives/constraints, I/O detail, FSM states |
| `docs/troubleshooting.md` | Common issues, FAQ, diagnostic steps |
| `docs/architecture.md` | High-level architecture for contributors (FSM, coordinator, web layer) |

### Key Entities

- **Config Keys**: ~25 configuration constants in `const.py` that map to entities and settings
- **Sensors**: The integration creates sensors that need documenting
- **Web Endpoints**: 4 API endpoints + 1 panel

## Success Criteria

### Measurable Outcomes

- **SC-001**: A user with HA + HACS + Amber + Solcast + Tesla can install and see live data by following README alone
- **SC-002**: Every CONF_ constant in const.py is documented in /docs/configuration.md
- **SC-003**: No stale references (plan table, wrong URLs, old auth model) remain
- **SC-004**: manifest.json documentation URL points to correct repo
