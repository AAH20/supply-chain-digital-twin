from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict, deque
from statistics import mean
from typing import Any


def evaluate(scenario: dict[str, Any]) -> dict[str, Any]:
    _validate(scenario)
    forecast = _forecast_scorecard(scenario["demand_history"])
    disruption = scenario["disruption"]
    affected = _propagate(disruption["material"], scenario["bill_of_materials"])
    inventory = _inventory_scorecard(scenario, affected)
    actions = _actions(scenario, affected)
    feasible = [action for action in actions if not action["violations"]]
    selected = max(feasible, key=lambda item: item["modeled_net_value_usd"]) if feasible else None
    baseline_loss = inventory["modeled_contribution_at_risk_usd"] + inventory["modeled_penalties_at_risk_usd"]
    report: dict[str, Any] = {
        "schema_version": "supplytwin/v1",
        "scenario": scenario["scenario"],
        "evidence_level": "deterministic-synthetic-digital-twin",
        "forecasting": forecast,
        "disruption": {"material": disruption["material"], "delay_days": disruption["delay_days"], "affected_products": affected},
        "inventory": inventory,
        "actions": actions,
        "selected_action": selected,
        "unit_economics": {
            "modeled_do_nothing_exposure_usd": round(baseline_loss, 2),
            "modeled_selected_net_value_usd": selected["modeled_net_value_usd"] if selected else 0,
            "modeled_exposure_remaining_usd": round(max(0, baseline_loss - (selected["modeled_loss_avoided_usd"] if selected else 0)), 2),
            "cash_released_is_not_revenue": True,
        },
        "production_control": {
            "auto_execute": False,
            "required_gates": ["planner approval", "supplier confirmation", "quality approval", "finance approval", "ERP reconciliation"],
        },
        "claim_boundary": [
            "No live SAP, Oracle, Dynamics, Odoo, supplier, factory or logistics system was called",
            "Demand, inventory, lead time, costs, service levels and disruption are synthetic inputs",
            "No physical production, purchasing or safety-critical action is authorized",
            "Modeled value is not realized savings, revenue or working-capital release",
        ],
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def _forecast_scorecard(history: list[float]) -> dict[str, Any]:
    train, test = history[:-4], history[-4:]
    seasonal = train[-4:]
    moving = [mean(train[-4:])] * 4
    seasonal_mae = mean(abs(actual - predicted) for actual, predicted in zip(test, seasonal))
    moving_mae = mean(abs(actual - predicted) for actual, predicted in zip(test, moving))
    winner = "seasonal-naive" if seasonal_mae <= moving_mae else "moving-average"
    forecast = seasonal[-1] if winner == "seasonal-naive" else moving[-1]
    return {"winner": winner, "seasonal_naive_mae": round(seasonal_mae, 2), "moving_average_mae": round(moving_mae, 2), "next_period_units": round(forecast, 2), "complex_model_must_beat_baseline": True}


def _propagate(material: str, bom: list[dict[str, Any]]) -> list[str]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in bom:
        graph[edge["component"]].append(edge["product"])
    queue, visited = deque([material]), set()
    products = set()
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for child in graph[node]:
            products.add(child)
            queue.append(child)
    return sorted(products)


def _inventory_scorecard(scenario: dict[str, Any], affected: list[str]) -> dict[str, Any]:
    product_map = {item["name"]: item for item in scenario["products"]}
    revenue = contribution = penalties = 0.0
    for name in affected:
        product = product_map[name]
        shortage = max(0, product["committed_units"] - product["available_units"])
        revenue += shortage * product["price_usd"]
        contribution += shortage * product["price_usd"] * product["gross_margin_pct"]
        penalties += shortage * product["late_penalty_usd"]
    holding = sum(item["available_units"] * item["unit_cost_usd"] * scenario["annual_holding_rate"] for item in scenario["products"])
    return {"modeled_revenue_at_risk_usd": round(revenue, 2), "modeled_contribution_at_risk_usd": round(contribution, 2), "modeled_penalties_at_risk_usd": round(penalties, 2), "annual_inventory_carrying_cost_usd": round(holding, 2)}


def _actions(scenario: dict[str, Any], affected: list[str]) -> list[dict[str, Any]]:
    baseline = _inventory_scorecard(scenario, affected)
    exposure = baseline["modeled_contribution_at_risk_usd"] + baseline["modeled_penalties_at_risk_usd"]
    result = []
    for action in scenario["candidate_actions"]:
        violations = []
        if action["quality_approved"] is False:
            violations.append("quality approval absent")
        if action["cash_required_usd"] > scenario["constraints"]["max_incremental_cash_usd"]:
            violations.append("cash ceiling exceeded")
        if action["service_level_pct"] < scenario["constraints"]["min_service_level_pct"]:
            violations.append("service-level floor violated")
        avoided = exposure * action["exposure_reduction_pct"]
        net = avoided - action["incremental_cost_usd"]
        result.append({**action, "modeled_loss_avoided_usd": round(avoided, 2), "modeled_net_value_usd": round(net, 2), "violations": violations})
    return result


def _validate(scenario: dict[str, Any]) -> None:
    required = {"scenario", "demand_history", "products", "bill_of_materials", "disruption", "candidate_actions", "constraints", "annual_holding_rate"}
    missing = sorted(required - scenario.keys())
    if missing:
        raise ValueError(f"missing keys: {', '.join(missing)}")
    if len(scenario["demand_history"]) < 12 or any(value < 0 for value in scenario["demand_history"]):
        raise ValueError("demand history requires at least 12 non-negative periods")
    product_names = {item["name"] for item in scenario["products"]}
    if not product_names:
        raise ValueError("at least one product is required")
    if any(edge["product"] not in product_names for edge in scenario["bill_of_materials"]):
        raise ValueError("bill of materials references unknown product")
