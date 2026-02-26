"""Tests for Linear Programming FSM implementation (lin_fsm)."""

from datetime import datetime, time, timedelta, timezone

import pytest
from custom_components.house_battery_control.fsm.base import FSMContext
from custom_components.house_battery_control.fsm.lin_fsm import (
    LinearBatteryStateMachine,
    _is_in_no_import_period,
    _parse_no_import_periods,
)


@pytest.fixture
def base_context():
    """Provides a basic valid FSMContext for testing."""

    def generate_dummy_forecast(val):
        return [{"kw": val} for _ in range(28)]  # Just 28 intervals for fast tests

    def generate_dummy_price(import_val, export_val):
        return [{"import_price": import_val, "export_price": export_val} for _ in range(28)]

    # Mock context fields
    context = FSMContext(
        soc=50.0,
        load_power=1.0,
        solar_production=0.0,
        grid_voltage=240.0,
        current_price=10.0,
        forecast_price=generate_dummy_price(10.0, 5.0),
        forecast_solar=generate_dummy_forecast(2.0),
        forecast_load=generate_dummy_forecast(1.5),
        config={
            "battery_capacity": 27.0,
            "battery_rate_max": 6.3,
            "inverter_limit": 10.0,
            "round_trip_efficiency": 0.90,
        },
    )
    context.acquisition_cost = 0.0
    return context


def test_linear_solver_basic_execution(base_context):
    """Test 1: Ensure the solver executes without raising exceptions."""
    fsm = LinearBatteryStateMachine()
    result = fsm.calculate_next_state(base_context)

    # Asserting that the solver evaluated without crashing and returned a valid state
    assert result is not None
    assert result.state in ["SELF_CONSUMPTION", "CHARGE_GRID", "DISCHARGE_GRID", "ERROR"]
    assert isinstance(result.limit_kw, float)


def test_linear_solver_target_soc_calculation(base_context):
    """Test 2: Assert solver calculates a Target SOC representing deficit on cheap import."""
    # Force the upcoming rates to be very cheap, but load is extremely high.
    # The solver should calculate that it needs to charge from grid to meet upcoming deficit.
    for i in range(28):
        base_context.forecast_price[i]["import_price"] = 0.01  # extremely cheap
        base_context.forecast_price[i]["export_price"] = 0.00
        base_context.forecast_load[i]["kw"] = 5.0  # high load
        base_context.forecast_solar[i]["kw"] = 0.0  # no solar

    base_context.current_price = 0.01
    base_context.current_export_price = 0.00

    # But later in the day, import goes back up to force it to charge now
    for i in range(14, 28):
        base_context.forecast_price[i]["import_price"] = 50.0

    base_context.soc = 10.0  # battery is almost empty

    fsm = LinearBatteryStateMachine()
    result = fsm.calculate_next_state(base_context)
    print("TEST 2 RESULT:", vars(result))

    # Ideally, it should choose to charge grid due to massive deficit and low cost
    assert result.state == "CHARGE_GRID"
    assert result.target_soc > 10.0  # Target SOC should be much higher to cover 5kW load


def test_inverter_physical_bounds_limit_kw(base_context):
    """Test 3: Assert the system physically clamps the charging/discharging limit_kw."""
    # Create an extreme scenario that mathematically suggests massive charge rate
    for i in range(28):
        base_context.forecast_price[i]["import_price"] = 0.05
        base_context.forecast_price[i]["export_price"] = 0.05
        base_context.forecast_load[i]["kw"] = 0.0
        base_context.forecast_solar[i]["kw"] = 0.0

    # Make strictly step 0 the cheapest so the LP solves deterministically
    base_context.forecast_price[0]["import_price"] = 0.01
    base_context.forecast_price[0]["export_price"] = 0.01
    base_context.current_price = 0.01
    base_context.current_export_price = 0.01

    # Must have a future positive price to make holding it worthwhile
    base_context.forecast_price[20]["import_price"] = 100.0
    base_context.forecast_load[20]["kw"] = 5.0

    # Force a load right now so grid importing is mandatory regardless of solver arbitrage scaling
    base_context.forecast_load[0]["kw"] = 5.0

    base_context.soc = 0.0
    base_context.config["battery_rate_max"] = 5.0  # strictly clamp physical battery limit

    fsm = LinearBatteryStateMachine()
    result = fsm.calculate_next_state(base_context)
    print("TEST 3 RESULT:", vars(result))

    assert result.state == "CHARGE_GRID"
    # Even if mathematical optimum requires more, it is bound by `battery_rate_max`
    assert result.limit_kw <= 5.0


def test_solver_failure_fallback(base_context):
    """Test 4: Assert solver pads short arrays and still tries to plan."""
    base_context.forecast_price = []  # length 0 implies missing data or crash context

    fsm = LinearBatteryStateMachine()
    result = fsm.calculate_next_state(base_context)

    # The user updated the solver to strictly plan 288 steps regardless.
    assert result.state is not None
    assert result.future_plan is not None
    assert isinstance(result.future_plan, list)


# ---------------------------------------------------------------------------
#  No-Import Period tests (Feature 010)
# ---------------------------------------------------------------------------


class TestParseNoImportPeriods:
    """T008: Parser tests for _parse_no_import_periods."""

    def test_parse_single_period(self):
        result = _parse_no_import_periods("15:00-21:00")
        assert len(result) == 1
        assert result[0] == (time(15, 0), time(21, 0))

    def test_parse_multiple_periods(self):
        result = _parse_no_import_periods("15:00-21:00, 06:00-09:00")
        assert len(result) == 2
        assert result[0] == (time(15, 0), time(21, 0))
        assert result[1] == (time(6, 0), time(9, 0))

    def test_parse_empty_string(self):
        assert _parse_no_import_periods("") == []
        assert _parse_no_import_periods(None) == []  # type: ignore[arg-type]
        assert _parse_no_import_periods("   ") == []

    def test_parse_invalid_format(self):
        """Invalid entries should be skipped, valid ones kept."""
        result = _parse_no_import_periods("15:00-21:00, garbage, 06:00-09:00")
        assert len(result) == 2  # garbage skipped


class TestIsInNoImportPeriod:
    """T009: Time membership tests for _is_in_no_import_period."""

    def test_within_normal_period(self):
        periods = [(time(15, 0), time(21, 0))]
        assert _is_in_no_import_period(time(16, 0), periods) is True
        assert _is_in_no_import_period(time(15, 0), periods) is True  # inclusive start

    def test_outside_normal_period(self):
        periods = [(time(15, 0), time(21, 0))]
        assert _is_in_no_import_period(time(10, 0), periods) is False
        assert _is_in_no_import_period(time(21, 0), periods) is False  # exclusive end

    def test_midnight_wrap(self):
        periods = [(time(22, 0), time(6, 0))]
        assert _is_in_no_import_period(time(23, 0), periods) is True
        assert _is_in_no_import_period(time(1, 0), periods) is True
        assert _is_in_no_import_period(time(12, 0), periods) is False

    def test_multiple_periods(self):
        periods = [(time(6, 0), time(9, 0)), (time(15, 0), time(21, 0))]
        assert _is_in_no_import_period(time(7, 0), periods) is True
        assert _is_in_no_import_period(time(16, 0), periods) is True
        assert _is_in_no_import_period(time(12, 0), periods) is False


class TestNoImportPeriodLP:
    """T010: Full LP solver integration test with no-import periods."""

    def test_no_import_period_blocks_grid_import(self):
        """LP solver must produce zero grid import during blocked steps."""
        # Build a 28-step context with timestamps
        now = datetime(2026, 2, 26, 14, 0, tzinfo=timezone(timedelta(hours=10, minutes=30)))
        forecast_price = []
        for i in range(28):
            step_time = now + timedelta(minutes=5 * i)
            forecast_price.append({
                "start": step_time,
                "import_price": 0.01,  # Very cheap — solver WANTS to import
                "export_price": 0.005,
            })

        context = FSMContext(
            soc=10.0,  # Low SoC to incentivise charging
            load_power=2.0,
            solar_production=0.0,
            grid_voltage=240.0,
            current_price=0.01,
            forecast_price=forecast_price,
            forecast_solar=[{"kw": 0.0} for _ in range(28)],
            forecast_load=[{"kw": 2.0} for _ in range(28)],
            config={
                "battery_capacity": 27.0,
                "battery_rate_max": 6.3,
                "inverter_limit": 10.0,
                "round_trip_efficiency": 0.90,
                # Block 15:00-21:00 — steps starting at 14:00 + 12*5min = 15:00 onwards
                "no_import_periods": "15:00-21:00",
            },
        )
        context.acquisition_cost = 0.0

        fsm = LinearBatteryStateMachine()
        result = fsm.calculate_next_state(context)

        # Solver should still produce a valid result
        assert result is not None
        assert result.state != "ERROR"
        assert result.future_plan is not None

        # Steps within the 15:00-21:00 window should show zero grid import
        for step in result.future_plan:
            step_time = step.get("time")
            if step_time and hasattr(step_time, "hour"):
                if 15 <= step_time.hour < 21:
                    grid_import = step.get("grid_kw", 0.0)
                    # Grid import should be zero or negative (export) during no-import window
                    assert grid_import <= 0.01, (
                        f"Grid import {grid_import} at {step_time} should be ~0 during no-import period"
                    )

