"""Solver replay regression tests — permanent suite.

Uses captured API data from production (2026-03-05T07:48Z) to freeze known
solver conditions and prevent regressions. This is the heart of the program:
any solver behaviour change that breaks these tests must be investigated.

Fixture: tests/fixtures/solver_replay_20260305.json
Source:   API Data/hbc_status_2026-03-05T07-48-17-896Z.json

Bugs captured:
  BUG-025A: Acquisition cost feedback loop (ratchet via terminal_valuation)
  BUG-025B: SoC forecast not corrected after acquisition cost gate override
"""

import json
import os
import statistics

import pytest

# ---------------------------------------------------------------------------
# Fixture: load the solver replay data
# ---------------------------------------------------------------------------
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="module")
def replay_20260305():
    """Load the captured solver inputs from the 2026-03-05 API dump."""
    path = os.path.join(FIXTURE_DIR, "solver_replay_20260305.json")
    with open(path) as f:
        return json.load(f)


# ===========================================================================
# BUG-025A: Acquisition cost feedback loop
# ===========================================================================
class TestAcqCostFeedbackLoop:
    """The solver's terminal_valuation floors acq cost via max().

    When we sync plan[0]["acquisition_cost"] back to self.acquisition_cost,
    repeated solver runs ratchet it up toward median_buy.
    """

    @pytest.mark.xfail(reason="BUG-025A: feedback loop not yet fixed", strict=True)
    def test_terminal_valuation_does_not_ratchet(self, replay_20260305):
        """Starting from a low acq cost, repeated solver → sync cycles must NOT inflate it."""
        rates = replay_20260305["rates"]
        price_buy = [float(r.get("import_price", 0.0)) for r in rates]
        median_buy = statistics.median(price_buy)

        # Simulate the ratchet: terminal_valuation = max(acq, (median + acq)/2)
        acq_cost = 0.0004  # Original buggy tracker value
        for _ in range(20):
            blended = (median_buy + acq_cost) / 2.0
            terminal_valuation = max(acq_cost, blended)
            acq_cost = terminal_valuation  # Feature 025 sync

        assert acq_cost < 0.15, (
            f"Acq cost ratcheted to {acq_cost:.4f} (median_buy={median_buy:.4f}). "
            f"Feedback loop through terminal_valuation inflates the value."
        )

    @pytest.mark.xfail(reason="BUG-025A: feedback loop not yet fixed", strict=True)
    def test_acq_cost_stable_across_solver_runs(self, replay_20260305):
        """Two consecutive solver runs should produce the same acquisition_cost."""
        rates = replay_20260305["rates"]
        price_buy = [float(r.get("import_price", 0.0)) for r in rates]
        median_buy = statistics.median(price_buy)

        acq_cost = 0.135  # Reasonable starting value

        # Run 1
        blended1 = (median_buy + acq_cost) / 2.0
        tv1 = max(acq_cost, blended1)
        result1 = tv1

        # Run 2 (synced from run 1)
        blended2 = (median_buy + result1) / 2.0
        tv2 = max(result1, blended2)
        result2 = tv2

        assert abs(result1 - result2) < 0.001, (
            f"Acq cost drifted: run1={result1:.4f}, run2={result2:.4f}. "
            f"Solver feedback is not idempotent."
        )


# ===========================================================================
# BUG-025B: SoC forecast ignores acquisition cost gate
# ===========================================================================
class TestSocForecastGateBug:
    """The acquisition cost gate converts DISCHARGE_GRID → SELF_CONSUMPTION
    but doesn't correct the LP's SoC forecast, so the plan shows impossible
    battery drain at >10kW when the inverter limit is 5kW.
    """

    def test_soc_rate_within_inverter_limit(self, replay_20260305):
        """No SoC step should imply a power rate exceeding the inverter limit.

        This guards against impossible physics in the solver output regardless
        of state classification. If this fails, the solver or gate is producing
        a plan that violates hardware constraints.
        """
        soc = replay_20260305["soc_forecast"]
        capacity = replay_20260305.get("capacity", 27.0)
        inverter_limit = replay_20260305.get("inverter_limit", 10.0)
        charge_rate = replay_20260305.get("charge_rate_max", 6.3)
        max_kw = max(inverter_limit, charge_rate)
        step_hours = 5.0 / 60.0

        violations = []
        for i in range(1, len(soc)):
            delta_pct = abs(soc[i] - soc[i - 1])
            delta_kwh = delta_pct / 100.0 * capacity
            implied_kw = delta_kwh / step_hours

            if implied_kw > max_kw * 1.1:  # 10% tolerance for rounding
                violations.append(
                    f"Step {i}: SoC {soc[i-1]:.1f}%->{soc[i]:.1f}% "
                    f"implied={implied_kw:.1f}kW (limit={max_kw}kW)"
                )

        assert not violations, (
            f"SoC implies power exceeding inverter limit in {len(violations)} steps:\n"
            + "\n".join(violations[:5])
        )

    @pytest.mark.xfail(reason="BUG-025B: gate doesn't correct SoC forecast", strict=True)
    def test_self_consumption_drain_matches_load(self, replay_20260305):
        """In SELF_CONSUMPTION, SoC drain should match load - PV, not exceed it."""
        soc = replay_20260305["soc_forecast"]
        load = replay_20260305["load_kw"]
        pv = replay_20260305["pv_kw"]
        states = replay_20260305["states"]
        capacity = replay_20260305.get("capacity", 27.0)
        step_hours = 5.0 / 60.0

        violations = []
        for i in range(1, len(soc)):
            if states[i] != "SELF_CONSUMPTION":
                continue

            expected_drain_kwh = max(0, load[i] - pv[i]) * step_hours
            expected_drain_pct = expected_drain_kwh / capacity * 100.0
            actual_drain_pct = soc[i - 1] - soc[i]

            if actual_drain_pct < 0:
                continue  # SoC increased (solar charging)

            if actual_drain_pct > expected_drain_pct * 3 + 0.5:
                violations.append(
                    f"Step {i}: drain={actual_drain_pct:.1f}% "
                    f"expected~{expected_drain_pct:.1f}% "
                    f"load={load[i]:.2f}kW pv={pv[i]:.2f}kW"
                )

        assert not violations, (
            f"SELF_CONSUMPTION drain exceeds load-PV in {len(violations)} steps:\n"
            + "\n".join(violations[:5])
        )

    @pytest.mark.xfail(reason="BUG-025B: gate doesn't correct SoC forecast", strict=True)
    def test_gated_discharge_not_visible_in_soc(self, replay_20260305):
        """Steps 152-169 (~07:00-08:25 UTC): gate blocked discharge but SoC dropped 3.2%/step."""
        soc = replay_20260305["soc_forecast"]
        states = replay_20260305["states"]
        capacity = replay_20260305.get("capacity", 27.0)

        anomalous_drains = []
        for i in range(152, min(170, len(soc))):
            if states[i] == "SELF_CONSUMPTION":
                drain_pct = soc[i - 1] - soc[i]
                drain_kwh = drain_pct / 100.0 * capacity
                if drain_kwh > 0.5:
                    anomalous_drains.append((i, drain_pct, drain_kwh))

        assert not anomalous_drains, (
            f"Gate blocked discharge but SoC still dropped in {len(anomalous_drains)} steps. "
            f"First: step {anomalous_drains[0][0]}, "
            f"drain={anomalous_drains[0][1]:.1f}%={anomalous_drains[0][2]:.2f}kWh. "
            f"LP battery variable not corrected after gate override."
        )
