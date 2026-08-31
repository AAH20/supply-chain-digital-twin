import json
from pathlib import Path

import pytest

from supplytwin.engine import evaluate

ROOT = Path(__file__).parents[1]


@pytest.fixture
def scenario():
    return json.loads((ROOT / "examples/global-manufacturer/disruption.json").read_text())


def test_disruption_propagates_to_dependent_products(scenario):
    report = evaluate(scenario)
    assert report["disruption"]["affected_products"] == ["edge-gateway", "industrial-controller"]


def test_selects_highest_value_feasible_action(scenario):
    assert evaluate(scenario)["selected_action"]["name"] == "approved-alternate-plus-reallocation"


def test_unapproved_substitution_is_blocked(scenario):
    actions = {item["name"]: item for item in evaluate(scenario)["actions"]}
    assert "quality approval absent" in actions["unapproved-component-substitution"]["violations"]


def test_cash_and_revenue_are_not_conflated(scenario):
    assert evaluate(scenario)["unit_economics"]["cash_released_is_not_revenue"]


def test_never_auto_executes(scenario):
    assert not evaluate(scenario)["production_control"]["auto_execute"]


def test_receipt_is_deterministic(scenario):
    assert evaluate(scenario)["receipt_sha256"] == evaluate(scenario)["receipt_sha256"]


def test_invalid_history_fails_closed(scenario):
    scenario["demand_history"] = [1, 2]
    with pytest.raises(ValueError):
        evaluate(scenario)
