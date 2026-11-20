"""Career Venture Lab — Single-File Stage 2 Streamlit Dashboard for Team Lucas (MKT-1 | Algebra 2)."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# DETERMINISTIC SIMULATION ENGINE & ACCOUNTING RULES (EMBEDDED)
# ==============================================================================

TWO_PLACES = Decimal("0.01")

DEFAULT_FIXTURE_ROWS = [
    {"month": "2027-01", "requested": 12, "capacity_override": 10, "ad_cost": "0.00"},
    {"month": "2027-02", "requested": 10, "capacity_override": 10, "ad_cost": "100.00"},
    {"month": "2027-03", "requested": 7, "capacity_override": 10, "ad_cost": "150.00"},
]


def d(val: Any) -> Decimal:
    """Convert numeric or string input to Decimal rounded to cents."""
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def default_state() -> Dict[str, Any]:
    """Return initial post-startup state for Team Lucas (MKT-1, Algebra 2)."""
    return {
        "team_id": "Team Lucas",
        "course": "Algebra 2",
        "pathway_id": "MKT-1",
        "business_name": "Local-Business Marketing Agency",
        "snapshot_id": "snap-001",
        "state_version": 1,
        "simulation_date": "2027-01-01",
        "base_period": "monthly",
        "working_days": 22,
        "calendar_days": 30,
        "currency": "USD",
        "selected_skill": "Linear Break-Even & Profit Modeling",
        "selected_level": "Foundation",
        "level_approved": True,
        "level_by_skill": {
            "Linear Break-Even & Profit Modeling": "Foundation",
            "Piecewise Demand & Profit Composition": "Applied",
            "Systems of Inequalities & Capacity Sensitivity": "Advanced",
        },
        "assumptions": [
            "All values are fictional teaching assumptions from Career Venture Lab Student Handbook (MKT-1).",
            "Unmet monthly demand is lost demand (no backlog carried to next month).",
            "Simplified accrual model with immediate cash collection; taxes and depreciation disabled at baseline.",
            "Client pass-through media budgets are held as cash + liability until spent and never counted as agency revenue.",
        ],
        "sources": [
            "Career Venture Lab Student Handbook (Revised Nov 2026), Pages 20, 56-61, 68, 98-102."
        ],
        "offerings": [
            {
                "offering_id": "OFF-01",
                "name": "Campaign package (Primary)",
                "unit": "package",
                "price": "250.00",
                "demand_rule": "D0=12 at p0=250; Applied q(p)=max(0, 24 - 0.048*p)",
                "capacity_rule": "floor(staff_hours / (hours_per_unit + revision_hours_per_package))",
                "active": True,
            },
            {
                "offering_id": "OFF-02",
                "name": "Flyer design package (Optional secondary)",
                "unit": "package",
                "price": "150.00",
                "demand_rule": "Requires separate cost/capacity allocation before enabling",
                "capacity_rule": "Disabled in primary acceptance mode",
                "active": False,
            },
            {
                "offering_id": "OFF-03",
                "name": "Social campaign package (Optional secondary)",
                "unit": "package",
                "price": "300.00",
                "demand_rule": "Requires separate cost/capacity allocation before enabling",
                "capacity_rule": "Disabled in primary acceptance mode",
                "active": False,
            },
            {
                "offering_id": "OFF-04",
                "name": "Event promotion package (Optional secondary)",
                "unit": "package",
                "price": "350.00",
                "demand_rule": "Requires separate cost/capacity allocation before enabling",
                "capacity_rule": "Disabled in primary acceptance mode",
                "active": False,
            },
        ],
        "funding": {
            "owner_contribution": "6500.00",
            "equipment_assets": "1500.00",
            "pre_opening_expense": "1000.00",
            "opening_inventory": "0.00",
            "post_startup_cash": "4000.00",
            "retained_earnings": "-1000.00",
            "loan_balance": "0.00",
            "client_media_liability": "0.00",
        },
        "parameters": {
            "base_price": "250.00",
            "D0": 12,
            "staff_hours": "80.00",
            "hours_per_unit": "8.00",
            "revision_hours_per_package": "0.00",
            "extra_revision_hourly_cost": "5.00",
            "client_media_budget": "0.00",
            "random_seed": 2027,
        },
        "cost_lines": {
            "variable": {
                "designer_labor": "40.00",
                "licensed_assets": "10.00",
                "printing_delivery": "20.00",
                "quality_revision_allowance": "10.00",
            },
            "fixed": {
                "software": "250.00",
                "workspace": "300.00",
                "admin": "200.00",
                "hosting": "150.00",
            },
        },
        "cash": "4000.00",
        "capacity": {
            "derived_capacity": 10,
            "formula": "floor(staff_hours / (hours_per_unit + revision_hours_per_package))",
        },
        "ledger": [],
        "processed_run_ids": [],
        "campaigns": [],
        "recommendations": [],
        "decisions": [],
    }


def compute_capacity(params: Dict[str, Any]) -> int:
    """Compute monthly integer package capacity from productive staff hours."""
    staff_hours = Decimal(str(params["staff_hours"]))
    hours_per_unit = Decimal(str(params["hours_per_unit"]))
    rev_hours = Decimal(str(params.get("revision_hours_per_package", "0")))
    if staff_hours < 0 or hours_per_unit <= 0 or rev_hours < 0:
        raise ValueError("Invalid hours: staff_hours >= 0, hours_per_unit > 0, revision_hours >= 0 required.")
    total_hours_per_pkg = hours_per_unit + rev_hours
    return int(math.floor(staff_hours / total_hours_per_pkg))


def compute_unit_variable_cost(cost_lines: Dict[str, Any], params: Dict[str, Any]) -> Decimal:
    """Compute variable cost per delivered package including extra revision hours."""
    base_var = sum(d(v) for v in cost_lines["variable"].values())
    rev_hours = Decimal(str(params.get("revision_hours_per_package", "0")))
    rev_rate = d(params.get("extra_revision_hourly_cost", "5.00"))
    if any(d(v) < 0 for v in cost_lines["variable"].values()) or rev_hours < 0 or rev_rate < 0:
        raise ValueError("Cost lines and revision parameters must be non-negative.")
    return (base_var + (rev_hours * rev_rate)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def compute_fixed_cost(cost_lines: Dict[str, Any]) -> Decimal:
    """Compute total monthly fixed operating costs."""
    if any(d(v) < 0 for v in cost_lines["fixed"].values()):
        raise ValueError("Fixed cost lines must be non-negative.")
    return sum((d(v) for v in cost_lines["fixed"].values()), Decimal("0.00")).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )


def compute_campaign_cost(
    design_hours: Any,
    hourly_rate: Any,
    assets: Any,
    print_quantity: int,
    print_unit_cost: Any,
    distribution: Any,
    placement: Any,
) -> Decimal:
    """Handbook MKT formula: design_hours*hourly_rate + assets + print_quantity*print_unit_cost + distribution + placement."""
    dh = Decimal(str(design_hours))
    hr = d(hourly_rate)
    ast = d(assets)
    pq = int(print_quantity)
    puc = d(print_unit_cost)
    dist = d(distribution)
    plc = d(placement)
    if dh < 0 or hr < 0 or ast < 0 or pq < 0 or puc < 0 or dist < 0 or plc < 0:
        raise ValueError("All campaign cost inputs must be non-negative.")
    total = (dh * hr) + ast + (Decimal(pq) * puc) + dist + plc
    return total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def launch_approved_campaign(
    state: Dict[str, Any],
    *,
    campaign_id: str,
    month_str: str,
    offering_id: str,
    audience: str,
    channel: str,
    claim: str,
    variant_label: str,
    design_hours: Any,
    hourly_rate: Any,
    assets: Any,
    print_quantity: int,
    print_unit_cost: Any,
    distribution: Any,
    placement: Any,
    assumed_reach: int,
    inquiries: int,
    conversions: int,
    reviewer_approved: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Record an approved own-agency marketing campaign in the dated ledger once."""
    if not reviewer_approved:
        raise ValueError("Campaign cannot be launched without reviewer and student approval.")
    clean_id = campaign_id.strip()
    if not clean_id:
        raise ValueError("campaign_id is required.")

    new_state = deepcopy(state)
    existing_ids = {c["campaign_id"] for c in new_state.get("campaigns", [])}
    if clean_id in existing_ids or clean_id in new_state.get("processed_run_ids", []):
        return new_state, {"status": "duplicate_rejected", "campaign_id": clean_id}

    total_cost = compute_campaign_cost(
        design_hours, hourly_rate, assets, print_quantity, print_unit_cost, distribution, placement
    )
    opening_cash = d(new_state["cash"])
    closing_cash = (opening_cash - total_cost).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    next_ver = int(new_state["state_version"]) + 1
    tx_date = f"{month_str[:7]}-15" if len(month_str) >= 7 else month_str
    tx_idx = len(new_state["ledger"]) + 1

    if total_cost > Decimal("0.00"):
        new_state["ledger"].append(
            {
                "transaction_id": f"TX-{tx_idx:04d}",
                "run_id": clean_id,
                "date": tx_date,
                "month": month_str[:7],
                "event_type": "marketing_expense",
                "category": f"Own-agency campaign ({channel} - {variant_label})",
                "amount": f"{total_cost:.2f}",
                "quantity": 1,
                "unit_price": f"{total_cost:.2f}",
                "offering_id": offering_id,
                "campaign_id": clean_id,
                "financing_type": "operating",
                "state_version": next_ver,
            }
        )

    cac = f"{(total_cost / Decimal(conversions)):.2f}" if int(conversions) > 0 else "N/A"
    record = {
        "campaign_id": clean_id,
        "month": month_str[:7],
        "offering_id": offering_id,
        "audience": audience,
        "channel": channel,
        "claim": claim,
        "variant_label": variant_label,
        "total_cost": f"{total_cost:.2f}",
        "assumed_reach": int(assumed_reach),
        "inquiries": int(inquiries),
        "conversions": int(conversions),
        "cac": cac,
        "approval_status": "approved_launched",
        "state_version": next_ver,
    }
    new_state["campaigns"].append(record)
    new_state["processed_run_ids"].append(clean_id)
    new_state["cash"] = f"{closing_cash:.2f}"
    new_state["funding"]["retained_earnings"] = f"{(d(new_state['funding']['retained_earnings']) - total_cost):.2f}"
    new_state["state_version"] = next_ver
    new_state["snapshot_id"] = f"snap-{next_ver:03d}"
    return new_state, {"status": "launched", "campaign": record}


def import_recommendation(
    state: Dict[str, Any], rec: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate and store a departmental AI recommendation (status=pending until student approves)."""
    required = ["role", "snapshot_id", "state_version", "question", "recommendation"]
    missing = [k for k in required if k not in rec]
    if missing:
        return False, f"Recommendation rejected: missing fields {missing}.", state

    if "team_id" in rec and rec["team_id"] != state["team_id"]:
        return False, f"Recommendation rejected: team_id mismatch ('{rec['team_id']}' != '{state['team_id']}').", state

    try:
        rec_ver = int(rec["state_version"])
        cur_ver = int(state["state_version"])
    except (TypeError, ValueError):
        return False, "Recommendation rejected: invalid state_version.", state

    if rec_ver < cur_ver:
        return (
            False,
            f"Recommendation rejected: stale state_version v{rec_ver} (current business is at v{cur_ver}).",
            state,
        )

    new_state = deepcopy(state)
    entry = {
        "rec_id": f"REC-{len(new_state.get('recommendations', [])) + 1:03d}",
        "role": rec["role"],
        "snapshot_id": rec["snapshot_id"],
        "state_version": rec_ver,
        "question": rec["question"],
        "evidence": rec.get("evidence", []),
        "method": rec.get("method", ""),
        "recommendation": rec["recommendation"],
        "alternatives": rec.get("alternatives", []),
        "uncertainty": rec.get("uncertainty", ""),
        "proposed_changes": rec.get("proposed_changes", {}),
        "checks_needed": rec.get("checks_needed", []),
        "checker": rec.get("checker", ""),
        "approval_status": "pending",
    }
    new_state.setdefault("recommendations", []).append(entry)
    return True, f"Imported {entry['rec_id']} ({entry['role']}) as PENDING student review.", new_state


def generate_financial_reports(state: Dict[str, Any]) -> Dict[str, Any]:
    """Build reconciled Stage 2 financial & operational statements from the dated ledger without mutating state."""
    ledger = state.get("ledger", [])
    funding = state["funding"]
    params = state["parameters"]
    cost_lines = state["cost_lines"]

    sales_rev = Decimal("0.00")
    refunds = Decimal("0.00")
    var_exp = Decimal("0.00")
    fixed_exp = Decimal("0.00")
    mkt_exp = Decimal("0.00")
    interest_exp = Decimal("0.00")
    loan_in = Decimal("0.00")
    loan_repaid = Decimal("0.00")
    capex_out = Decimal("0.00")
    owner_in = Decimal("0.00")
    escrow_in = Decimal("0.00")
    units_sold = 0

    for tx in ledger:
        et = tx["event_type"]
        amt = d(tx["amount"])
        if et == "sales_revenue":
            sales_rev += amt
            units_sold += int(tx.get("quantity", 0))
        elif et == "refund":
            refunds += abs(amt)
        elif et == "variable_expense":
            var_exp += amt
        elif et == "fixed_expense":
            fixed_exp += amt
        elif et == "marketing_expense":
            mkt_exp += amt
        elif et == "interest_expense":
            interest_exp += amt
        elif et == "loan_proceeds":
            loan_in += amt
        elif et == "loan_principal":
            loan_repaid += amt
        elif et == "capex":
            capex_out += amt
        elif et == "owner_contribution":
            owner_in += amt
        elif et == "client_media_escrow":
            escrow_in += amt

    net_rev = sales_rev - refunds
    gross_profit = net_rev - var_exp
    operating_profit = gross_profit - fixed_exp - mkt_exp
    net_profit = operating_profit - interest_exp

    gross_margin = f"{((gross_profit / net_rev) * 100):.1f}%" if net_rev > 0 else "N/A"
    op_margin = f"{((operating_profit / net_rev) * 100):.1f}%" if net_rev > 0 else "N/A"

    open_cash = d(funding["post_startup_cash"])
    op_cash_flow = net_rev - var_exp - fixed_exp - mkt_exp - interest_exp
    inv_cash_flow = -capex_out
    fin_cash_flow = loan_in - loan_repaid + owner_in + escrow_in
    reconciled_close_cash = (open_cash + op_cash_flow + inv_cash_flow + fin_cash_flow).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    ledger_cash = d(state["cash"])

    equip_assets = d(funding["equipment_assets"])
    total_assets = (ledger_cash + equip_assets).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    loan_bal = d(funding["loan_balance"])
    escrow_bal = d(funding["client_media_liability"])
    total_liabilities = (loan_bal + escrow_bal).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    owner_eq = d(funding["owner_contribution"])
    ret_earn = d(funding["retained_earnings"])
    total_equity = (owner_eq + ret_earn).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    liab_plus_eq = (total_liabilities + total_equity).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    active_months = sorted({tx["month"] for tx in ledger})
    num_months = max(1, len(active_months))
    budget_units = int(compute_capacity(params)) * num_months
    budget_rev = d(params["base_price"]) * Decimal(budget_units)
    budget_var = compute_unit_variable_cost(cost_lines, params) * Decimal(budget_units)
    budget_fixed = compute_fixed_cost(cost_lines) * Decimal(num_months)
    budget_profit = budget_rev - budget_var - budget_fixed

    return {
        "meta": {
            "team_id": state["team_id"],
            "pathway_id": state["pathway_id"],
            "course": state["course"],
            "snapshot_id": state["snapshot_id"],
            "state_version": state["state_version"],
            "periods_recorded": num_months,
            "months": active_months if active_months else ["Pre-Round Baseline"],
            "accounting_notes": "Simplified accrual with immediate cash collection. Taxes and depreciation disabled at baseline.",
        },
        "income_statement": {
            "Gross Sales Revenue": f"{sales_rev:.2f}",
            "Less: Refunds": f"{refunds:.2f}",
            "Net Revenue": f"{net_rev:.2f}",
            "Variable Delivery Costs (COGS)": f"{var_exp:.2f}",
            "Gross Profit": f"{gross_profit:.2f}",
            "Gross Margin %": gross_margin,
            "Fixed Operating Overhead": f"{fixed_exp:.2f}",
            "Own-Agency Marketing Expense": f"{mkt_exp:.2f}",
            "Operating Profit (EBIT)": f"{operating_profit:.2f}",
            "Operating Margin %": op_margin,
            "Interest Expense": f"{interest_exp:.2f}",
            "Net Income / Profit": f"{net_profit:.2f}",
        },
        "cash_flow": {
            "Post-Startup Opening Cash": f"{open_cash:.2f}",
            "Net Operating Cash Flow": f"{op_cash_flow:.2f}",
            "Net Investing Cash Flow (Capex)": f"{inv_cash_flow:.2f}",
            "Net Financing & Escrow Cash Flow": f"{fin_cash_flow:.2f}",
            "Reconciled Closing Cash": f"{reconciled_close_cash:.2f}",
            "Current Ledger Cash": f"{ledger_cash:.2f}",
            "Cash Reconciliation Match": reconciled_close_cash == ledger_cash,
        },
        "balance_sheet": {
            "Cash & Equivalents": f"{ledger_cash:.2f}",
            "Computer & Design Equipment (Gross)": f"{equip_assets:.2f}",
            "Total Assets": f"{total_assets:.2f}",
            "Loan Debt Payable": f"{loan_bal:.2f}",
            "Client Media Escrow Liability": f"{escrow_bal:.2f}",
            "Total Liabilities": f"{total_liabilities:.2f}",
            "Owner Capital Contribution": f"{owner_eq:.2f}",
            "Retained Earnings (incl. -$1,000 setup)": f"{ret_earn:.2f}",
            "Total Equity": f"{total_equity:.2f}",
            "Total Liabilities + Equity": f"{liab_plus_eq:.2f}",
            "Balance Sheet Reconciled (A = L + E)": total_assets == liab_plus_eq,
        },
        "budget_variance": [
            {
                "Line Item": "Completed Packages (Units)",
                "Budget": f"{budget_units}",
                "Actual": f"{units_sold}",
                "Variance ($ / Units)": f"{units_sold - budget_units:+d}",
                "Variance %": f"{((units_sold - budget_units)/budget_units*100):+.1f}%" if budget_units > 0 else "N/A",
            },
            {
                "Line Item": "Net Revenue ($)",
                "Budget": f"{budget_rev:.2f}",
                "Actual": f"{net_rev:.2f}",
                "Variance ($ / Units)": f"{(net_rev - budget_rev):+.2f}",
                "Variance %": f"{((net_rev - budget_rev)/budget_rev*100):+.1f}%" if budget_rev > 0 else "N/A",
            },
            {
                "Line Item": "Variable Delivery Cost ($)",
                "Budget": f"{budget_var:.2f}",
                "Actual": f"{var_exp:.2f}",
                "Variance ($ / Units)": f"{(var_exp - budget_var):+.2f}",
                "Variance %": f"{((var_exp - budget_var)/budget_var*100):+.1f}%" if budget_var > 0 else "N/A",
            },
            {
                "Line Item": "Fixed Overhead ($)",
                "Budget": f"{budget_fixed:.2f}",
                "Actual": f"{fixed_exp:.2f}",
                "Variance ($ / Units)": f"{(fixed_exp - budget_fixed):+.2f}",
                "Variance %": f"{((fixed_exp - budget_fixed)/budget_fixed*100):+.1f}%" if budget_fixed > 0 else "N/A",
            },
            {
                "Line Item": "Own-Agency Marketing ($)",
                "Budget": "0.00",
                "Actual": f"{mkt_exp:.2f}",
                "Variance ($ / Units)": f"{mkt_exp:+.2f}",
                "Variance %": "N/A",
            },
            {
                "Line Item": "Operating Profit ($)",
                "Budget": f"{budget_profit:.2f}",
                "Actual": f"{operating_profit:.2f}",
                "Variance ($ / Units)": f"{(operating_profit - budget_profit):+.2f}",
                "Variance %": f"{((operating_profit - budget_profit)/abs(budget_profit)*100):+.1f}%" if budget_profit != 0 else "N/A",
            },
        ],
    }


def simulate_month(
    state: Dict[str, Any],
    *,
    month_str: str,
    requested: int,
    run_id: str,
    ad_cost: Any = "0.00",
    capacity_override: Optional[int] = None,
    price_override: Optional[Any] = None,
    loan_received: Any = "0.00",
    loan_principal_repaid: Any = "0.00",
    interest_expense: Any = "0.00",
    additional_capex: Any = "0.00",
    new_owner_cash: Any = "0.00",
    refund_amount: Any = "0.00",
    client_media_inflow: Any = "0.00",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Advance simulation by one monthly step and record dated ledger entries."""
    new_state = deepcopy(state)
    if run_id in new_state.get("processed_run_ids", []):
        return new_state, {"status": "duplicate_ignored", "run_id": run_id}

    if requested < 0:
        raise ValueError("Requested demand cannot be negative.")
    if capacity_override is not None and capacity_override < 0:
        raise ValueError("Capacity override cannot be negative.")

    params = new_state["parameters"]
    cost_lines = new_state["cost_lines"]

    price = d(price_override if price_override is not None else params["base_price"])
    if price <= 0:
        raise ValueError("Package price must be greater than 0.")

    ad_expense = d(ad_cost)
    loan_in = d(loan_received)
    principal_out = d(loan_principal_repaid)
    interest_out = d(interest_expense)
    capex_out = d(additional_capex)
    owner_in = d(new_owner_cash)
    refunds_out = d(refund_amount)
    pass_through_in = d(client_media_inflow)

    for amt in (ad_expense, loan_in, principal_out, interest_out, capex_out, owner_in, refunds_out, pass_through_in):
        if amt < 0:
            raise ValueError("Financial transaction amounts cannot be negative.")

    derived_cap = compute_capacity(params)
    effective_cap = int(capacity_override) if capacity_override is not None else derived_cap
    sold = min(int(requested), effective_cap)
    unserved = max(0, int(requested) - sold)

    unit_var = compute_unit_variable_cost(cost_lines, params)
    fixed_exp = compute_fixed_cost(cost_lines)

    gross_revenue = (price * Decimal(sold)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    net_revenue = (gross_revenue - refunds_out).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    var_exp = (unit_var * Decimal(sold)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    total_operating_expense = (var_exp + fixed_exp + ad_expense).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    operating_profit = (net_revenue - total_operating_expense).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    net_profit = (operating_profit - interest_out).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    opening_cash = d(new_state["cash"])
    closing_cash = (
        opening_cash
        + net_revenue
        - var_exp
        - fixed_exp
        - ad_expense
        - interest_out
        - principal_out
        - capex_out
        + owner_in
        + loan_in
        + pass_through_in
    ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    next_ver = int(new_state["state_version"]) + 1
    tx_date = f"{month_str}-28" if len(month_str) == 7 else month_str
    base_tx_idx = len(new_state["ledger"]) + 1

    def add_tx(
        event_type: str,
        category: str,
        amount: Decimal,
        qty: int = 0,
        u_price: Decimal = Decimal("0.00"),
        fin_type: str = "operating",
    ):
        nonlocal base_tx_idx
        if amount == Decimal("0.00") and event_type not in ("sales_revenue", "fixed_expense"):
            return
        new_state["ledger"].append(
            {
                "transaction_id": f"TX-{base_tx_idx:04d}",
                "run_id": run_id,
                "date": tx_date,
                "month": month_str[:7],
                "event_type": event_type,
                "category": category,
                "amount": f"{amount:.2f}",
                "quantity": qty,
                "unit_price": f"{u_price:.2f}",
                "offering_id": "OFF-01",
                "campaign_id": f"CMP-{run_id}" if event_type == "marketing_expense" else "",
                "financing_type": fin_type,
                "state_version": next_ver,
            }
        )
        base_tx_idx += 1

    add_tx("sales_revenue", "Campaign package sales", gross_revenue, qty=sold, u_price=price, fin_type="operating")
    if refunds_out > 0:
        add_tx("refund", "Customer refunds", -refunds_out, qty=0, u_price=Decimal("0.00"), fin_type="operating")
    if var_exp > 0:
        add_tx("variable_expense", "Package delivery variable costs", var_exp, qty=sold, u_price=unit_var, fin_type="operating")
    add_tx("fixed_expense", "Monthly fixed overhead", fixed_exp, qty=1, u_price=fixed_exp, fin_type="operating")
    if ad_expense > 0:
        add_tx("marketing_expense", "Own-agency advertising", ad_expense, qty=1, u_price=ad_expense, fin_type="operating")
    if loan_in > 0:
        add_tx("loan_proceeds", "Simulated loan received", loan_in, fin_type="financing")
    if principal_out > 0:
        add_tx("loan_principal", "Loan principal repayment", principal_out, fin_type="financing")
    if interest_out > 0:
        add_tx("interest_expense", "Loan interest expense", interest_out, fin_type="financing")
    if capex_out > 0:
        add_tx("capex", "Equipment capital purchase", capex_out, fin_type="investing")
    if owner_in > 0:
        add_tx("owner_contribution", "Owner equity injection", owner_in, fin_type="financing")
    if pass_through_in > 0:
        add_tx("client_media_escrow", "Client pass-through media funds (liability)", pass_through_in, fin_type="escrow_liability")

    new_state["cash"] = f"{closing_cash:.2f}"
    new_state["state_version"] = next_ver
    new_state["snapshot_id"] = f"snap-{next_ver:03d}"
    new_state["simulation_date"] = tx_date
    new_state["capacity"]["derived_capacity"] = derived_cap
    new_state["processed_run_ids"].append(run_id)

    funding = new_state["funding"]
    funding["loan_balance"] = f"{(d(funding['loan_balance']) + loan_in - principal_out):.2f}"
    funding["equipment_assets"] = f"{(d(funding['equipment_assets']) + capex_out):.2f}"
    funding["owner_contribution"] = f"{(d(funding['owner_contribution']) + owner_in):.2f}"
    funding["retained_earnings"] = f"{(d(funding['retained_earnings']) + net_profit):.2f}"
    funding["client_media_liability"] = f"{(d(funding['client_media_liability']) + pass_through_in):.2f}"

    summary = {
        "status": "committed",
        "run_id": run_id,
        "month": month_str[:7],
        "mode": "fixture_override" if capacity_override is not None else "normal_derived",
        "requested": int(requested),
        "capacity": effective_cap,
        "sold": sold,
        "unserved_demand": unserved,
        "unit_price": f"{price:.2f}",
        "unit_variable_cost": f"{unit_var:.2f}",
        "revenue": f"{net_revenue:.2f}",
        "variable_expense": f"{var_exp:.2f}",
        "fixed_expense": f"{fixed_exp:.2f}",
        "marketing_expense": f"{ad_expense:.2f}",
        "total_expense": f"{total_operating_expense:.2f}",
        "operating_profit": f"{operating_profit:.2f}",
        "net_profit": f"{net_profit:.2f}",
        "opening_cash": f"{opening_cash:.2f}",
        "closing_cash": f"{closing_cash:.2f}",
        "state_version": next_ver,
    }
    return new_state, summary


def replay_fixture_rows(
    base_state: Dict[str, Any], rows: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Reset to opening post-startup cash and replay fixture rows sequentially."""
    state = deepcopy(base_state)
    state["cash"] = state["funding"]["post_startup_cash"]
    state["funding"]["retained_earnings"] = f"-{state['funding']['pre_opening_expense']}"
    state["ledger"] = []
    state["processed_run_ids"] = []
    state["state_version"] = 1

    results = []
    for idx, row in enumerate(rows, start=1):
        cap_ov = row.get("capacity_override")
        cap_val = int(cap_ov) if cap_ov not in (None, "", "None") else None
        state, res = simulate_month(
            state,
            month_str=str(row["month"]),
            requested=int(row["requested"]),
            capacity_override=cap_val,
            ad_cost=row.get("ad_cost", 0),
            run_id=f"fixture-{row['month']}-{idx}",
        )
        results.append(res)
    return state, results


def validate_and_import_snapshot(
    imported: Dict[str, Any], current_state: Dict[str, Any]
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate imported snapshot JSON against required fields, team_id, non-negativity, and state_version."""
    required_keys = [
        "team_id",
        "course",
        "pathway_id",
        "snapshot_id",
        "state_version",
        "simulation_date",
        "base_period",
        "working_days",
        "currency",
        "level_by_skill",
        "assumptions",
        "sources",
        "offerings",
        "funding",
        "cost_lines",
        "capacity",
        "ledger",
        "campaigns",
        "decisions",
        "parameters",
        "cash",
    ]
    missing = [k for k in required_keys if k not in imported]
    if missing:
        return False, f"Import rejected: missing required contract fields {missing}.", None

    if imported["team_id"] != current_state["team_id"]:
        return (
            False,
            f"Import rejected: team_id mismatch ('{imported['team_id']}' != '{current_state['team_id']}').",
            None,
        )

    if imported["pathway_id"] != current_state["pathway_id"]:
        return (
            False,
            f"Import rejected: pathway_id mismatch ('{imported['pathway_id']}' != '{current_state['pathway_id']}').",
            None,
        )

    try:
        imp_ver = int(imported["state_version"])
        cur_ver = int(current_state["state_version"])
    except (TypeError, ValueError):
        return False, "Import rejected: invalid state_version format.", None

    if imp_ver < cur_ver:
        return (
            False,
            f"Import rejected: stale state_version v{imp_ver} cannot overwrite current v{cur_ver}.",
            None,
        )

    try:
        if d(imported["cash"]) < 0 or d(imported["parameters"]["base_price"]) <= 0:
            return False, "Import rejected: negative cash or non-positive base price.", None
        if int(imported["parameters"]["D0"]) < 0 or Decimal(str(imported["parameters"]["staff_hours"])) < 0:
            return False, "Import rejected: negative demand or staff hours.", None
    except Exception as exc:
        return False, f"Import rejected: numeric validation failed ({exc}).", None

    return True, f"Snapshot '{imported['snapshot_id']}' (v{imp_ver}) validated and restored.", deepcopy(imported)


# ==============================================================================
# STREAMLIT USER INTERFACE (STAGE 1 + STAGE 2)
# ==============================================================================

st.set_page_config(
    page_title="Career Venture Lab | Team Lucas (MKT-1)",
    page_icon="📊",
    layout="wide",
)

if "sim_state" not in st.session_state:
    st.session_state.sim_state = default_state()
if "round_history" not in st.session_state:
    st.session_state.round_history = []
if "last_test_report" not in st.session_state:
    st.session_state.last_test_report = None

state: Dict[str, Any] = st.session_state.sim_state
params = state["parameters"]
cost_lines = state["cost_lines"]

st.title("📊 Career Venture Lab — Local-Business Marketing Agency (`MKT-1`)")
st.caption(
    f"**Team ID:** {state['team_id']} | **Course:** {state['course']} | "
    f"**State Version:** `v{state['state_version']}` | **Snapshot ID:** `{state['snapshot_id']}` | "
    f"**Build Stage:** Stage 2 (Core Engine + Departmental AI Tabs + Report Center + Costed Marketing Studio)"
)

derived_cap = compute_capacity(params)
unit_var = compute_unit_variable_cost(cost_lines, params)
fixed_mo = compute_fixed_cost(cost_lines)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Current Cash", f"${d(state['cash']):,.2f}")
m2.metric("Package Price (p₀)", f"${d(params['base_price']):,.2f}")
m3.metric(
    "Monthly Capacity",
    f"{derived_cap} pkgs",
    f"{params['staff_hours']}h / {Decimal(params['hours_per_unit']) + Decimal(params['revision_hours_per_package'])}h",
)
m4.metric("Variable Cost / Pkg", f"${unit_var:,.2f}")
m5.metric("Fixed Cost / Month", f"${fixed_mo:,.2f}")

st.divider()

# Persistent Math Skills & Challenge Level Panel
with st.expander("📐 Persistent Algebra 2 Math Skills & Challenge Level Panel", expanded=False):
    c_ctrl1, c_ctrl2, c_ctrl3 = st.columns([2, 2, 2])
    skill_options = list(state["level_by_skill"].keys())
    selected_skill = c_ctrl1.selectbox(
        "Algebra 2 Skill",
        skill_options,
        index=skill_options.index(state["selected_skill"]),
    )
    level_options = ["Foundation", "Applied", "Advanced"]
    chosen_level = c_ctrl2.radio(
        "Challenge Level (Teacher-Approved)",
        level_options,
        index=level_options.index(state["selected_level"]),
        horizontal=True,
    )
    teacher_approved = c_ctrl3.checkbox(
        "Teacher approved this skill & level",
        value=state["level_approved"],
    )
    if chosen_level != state["selected_level"] or selected_skill != state["selected_skill"]:
        if teacher_approved:
            state["selected_level"] = chosen_level
            state["selected_skill"] = selected_skill
            state["level_by_skill"][selected_skill] = chosen_level
            state["level_approved"] = True
        else:
            st.warning("Check 'Teacher approved this skill & level' before switching active challenge levels.")

    active_level = state["selected_level"]
    p0 = float(params["base_price"])
    d0 = int(params["D0"])
    v_cost = float(unit_var)
    f_cost = float(fixed_mo)
    cap = derived_cap

    if active_level == "Foundation":
        st.markdown(
            f"**Level: Foundation** — Hold package price $p_0 = \\${p0:.2f}$ fixed. "
            f"Model $R(q) = {p0:.0f}q$ and $C(q) = {f_cost:.0f} + {v_cost:.0f}q$ on feasible domain $0 \\le q \\le {cap}$ packages/month."
        )
        q_vals = np.arange(0, cap + 1)
        rev_vals = p0 * q_vals
        cost_vals = f_cost + v_cost * q_vals
        prof_vals = rev_vals - cost_vals

        if p0 > v_cost:
            be_exact = f_cost / (p0 - v_cost)
            be_units = math.ceil(be_exact)
            feasible_txt = "Feasible (within capacity)" if be_units <= cap else "Infeasible (exceeds monthly capacity)"
            st.info(
                f"**Break-Even Calculation:** $q = \\frac{{{f_cost:.2f}}}{{{p0:.2f} - {v_cost:.2f}}} = {be_exact:.2f}$ "
                f"→ **{be_units} whole packages/month** | Status: **{feasible_txt}**."
            )
        else:
            st.error("No positive break-even exists because unit price is less than or equal to variable cost ($p_0 \\le v$) while $F > 0$.")

        df_math = pd.DataFrame({
            "Quantity q (pkgs)": q_vals,
            "Revenue R(q) ($)": rev_vals,
            "Total Cost C(q) ($)": cost_vals,
            "Operating Profit P(q) ($)": prof_vals,
        })

        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=q_vals, y=rev_vals, mode="lines+markers", name="Revenue R(q)", line=dict(dash="solid", width=3)))
            fig.add_trace(go.Scatter(x=q_vals, y=cost_vals, mode="lines+markers", name="Total Cost C(q)", line=dict(dash="dash", width=3)))
            fig.add_trace(go.Scatter(x=q_vals, y=prof_vals, mode="lines+markers", name="Profit P(q)", line=dict(dash="dot", width=3)))
            fig.add_hline(y=0, line_color="gray", annotation_text="Zero Profit Line ($0)")
            fig.add_vline(x=cap, line_color="orange", line_dash="dashdot", annotation_text=f"Capacity Limit ({cap})")
            fig.update_layout(
                title=f"Foundation Model (Snapshot {state['snapshot_id']} | v{state['state_version']} | Forecast)",
                xaxis_title="Completed Packages q (units/month)",
                yaxis_title="Monthly Dollars (USD)",
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.dataframe(df_math, use_container_width=True, height=320)
            st.download_button(
                "Download Graph Data + Metadata (CSV)",
                data=(
                    f"# Team: {state['team_id']} | Pathway: {state['pathway_id']} | Level: Foundation | "
                    f"Equation: R(q)={p0}q, C(q)={f_cost}+{v_cost}q | Domain: 0<=q<={cap} | Label: Forecast\n"
                    + df_math.to_csv(index=False)
                ),
                file_name=f"foundation_model_v{state['state_version']}.csv",
                mime="text/csv",
            )
        st.caption("**Interpretation Prompt:** What is the minimum whole number of campaign packages needed to cover the $900 fixed overhead, and how many packages of safety margin remain before hitting capacity?")

    elif active_level == "Applied":
        slope = d0 / p0 if p0 > 0 else 0.0
        intercept = 2 * d0
        p_max = 2 * p0
        st.markdown(
            f"**Level: Applied** — Linear demand $q(p) = \\max(0, {intercept:.0f} - {slope:.4f}p)$ on price domain "
            f"$0 \\le p \\le \\${p_max:.2f}$. Completed sales are capped at capacity: $s(p) = \\min({cap}, \\lfloor q(p) \\rfloor)$."
        )
        p_grid = np.linspace(50, p_max, 25)
        q_cont = np.maximum(0.0, intercept - slope * p_grid)
        s_cont = np.minimum(float(cap), q_cont)
        s_int = np.minimum(cap, np.floor(q_cont)).astype(int)
        prof_cont = (p_grid - v_cost) * s_cont - f_cost
        prof_int = (p_grid - v_cost) * s_int - f_cost

        df_app = pd.DataFrame({
            "Price p ($)": np.round(p_grid, 2),
            "Demand q(p)": np.round(q_cont, 2),
            "Capped Sales s (int)": s_int,
            "Continuous Profit ($)": np.round(prof_cont, 2),
            "Whole-Unit Profit ($)": np.round(prof_int, 2),
        })

        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=p_grid, y=prof_cont, mode="lines", name="Continuous Piecewise Profit", line=dict(dash="dash")))
            fig.add_trace(go.Scatter(x=p_grid, y=prof_int, mode="lines+markers", name="Floored Whole-Unit Profit", line=dict(width=3)))
            fig.add_hline(y=0, line_color="gray", annotation_text="Break-Even ($0)")
            fig.update_layout(
                title=f"Applied Piecewise Profit vs. Price (Snapshot {state['snapshot_id']} | Forecast)",
                xaxis_title="Package Price p (USD)",
                yaxis_title="Monthly Operating Profit (USD)",
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.dataframe(df_app, use_container_width=True, height=320)

        st.markdown("**Compare Three Feasible Prices:**")
        pc1, pc2, pc3 = st.columns(3)
        p_choices = [
            pc1.number_input("Option A Price ($)", min_value=10.0, max_value=float(p_max), value=200.0, step=10.0),
            pc2.number_input("Option B Price ($)", min_value=10.0, max_value=float(p_max), value=250.0, step=10.0),
            pc3.number_input("Option C Price ($)", min_value=10.0, max_value=float(p_max), value=300.0, step=10.0),
        ]
        comp_rows = []
        for idx_opt, pr in enumerate(p_choices, start=1):
            qd = max(0.0, intercept - slope * pr)
            sd = min(cap, int(math.floor(qd)))
            rev_d = pr * sd
            cost_d = f_cost + v_cost * sd
            comp_rows.append({
                "Option": f"Price {idx_opt} (${pr:.2f})",
                "Requested q(p)": round(qd, 2),
                "Completed Sales s": sd,
                "Revenue ($)": round(rev_d, 2),
                "Total Cost ($)": round(cost_d, 2),
                "Operating Profit ($)": round(rev_d - cost_d, 2),
            })
        st.table(pd.DataFrame(comp_rows))
        st.caption("**Interpretation Prompt:** Why does lowering price below the capacity breakpoint ($p = \\$291.67$) stop increasing completed sales when capacity is capped at 10 packages?")

    else:  # Advanced
        st.markdown(
            "**Level: Advanced** — Compare baseline capacity against an **Extra-Shift Plan** using systems of inequalities "
            "for budget and staff-hour constraints, plus price-sensitivity checks."
        )
        ac1, ac2, ac3 = st.columns(3)
        extra_hours = ac1.slider("Extra Shift Hours / Month", min_value=0, max_value=80, value=24, step=8)
        extra_hr_rate = ac2.number_input("Extra Shift Hourly Overhead ($/hr)", min_value=0.0, max_value=100.0, value=15.0, step=1.0)
        shift_budget_cap = ac3.number_input("Monthly Fixed + Shift Budget Limit ($)", min_value=900.0, max_value=5000.0, value=1400.0, step=50.0)

        hrs_pkg = float(Decimal(params["hours_per_unit"]) + Decimal(params["revision_hours_per_package"]))
        added_units = int(math.floor(extra_hours / hrs_pkg))
        new_cap = cap + added_units
        shift_added_cost = extra_hours * extra_hr_rate
        new_fixed = f_cost + shift_added_cost
        budget_ok = new_fixed <= shift_budget_cap

        st.info(
            f"**Inequality Check:** Fixed + Shift Cost = $\\${f_cost:.2f} + {extra_hours}(\\${extra_hr_rate:.2f}) = \\${new_fixed:.2f} "
            f"{'\\le' if budget_ok else '>'} \\${shift_budget_cap:.2f}$ (**{'Feasible' if budget_ok else 'Exceeds Budget'}**). "
            f"New Capacity = ${cap} + \\lfloor {extra_hours}/{hrs_pkg:.1f} \\rfloor = {new_cap}$ packages."
        )

        q_adv = np.arange(0, new_cap + 1)
        prof_base = (p0 - v_cost) * np.minimum(q_adv, cap) - f_cost
        prof_shift = (p0 - v_cost) * q_adv - new_fixed
        fig_adv = go.Figure()
        fig_adv.add_trace(go.Scatter(x=q_adv, y=prof_base, mode="lines+markers", name=f"Baseline Plan (Cap {cap})"))
        fig_adv.add_trace(go.Scatter(x=q_adv, y=prof_shift, mode="lines+markers", name=f"Extra-Shift Plan (Cap {new_cap})", line=dict(dash="dash")))
        fig_adv.add_hline(y=0, line_color="gray")
        fig_adv.update_layout(
            title="Advanced Capacity Expansion & Constraint Comparison (Forecast)",
            xaxis_title="Requested Demand q (packages/month)",
            yaxis_title="Operating Profit (USD)",
            height=340,
        )
        st.plotly_chart(fig_adv, use_container_width=True)
        st.caption("**Interpretation Prompt:** At what minimum monthly demand $q$ does the Extra-Shift Plan overtake the Baseline Plan in profit, and when would extrapolating linear demand fail?")

# Main Navigation Tabs (Stage 1 + Stage 2)
tab_overview, tab_inputs, tab_sim, tab_depts, tab_reports, tab_mkt, tab_snapshot, tab_tests = st.tabs([
    "1. Overview & System Map",
    "2. Inputs & Funding",
    "3. Run Simulation & Ledger",
    "4. Departmental AI Tabs",
    "5. Report Center & Memos",
    "6. Costed Marketing Studio",
    "7. Save / Load Snapshot",
    "8. Acceptance Tests",
])

with tab_overview:
    st.subheader("System Architecture & Stage 2 Departmental Workflow")
    st.markdown(
        """
        **How Team Lucas's Operating System Works (Stage 2 Complete):**
        - **Manual vs. Automatic Boundaries:** All financial statements, cash reconciliations, capacity caps, and campaign costs are computed **automatically** by the deterministic engine. All parameter edits, departmental AI proposals, ad launches, and monthly advances require **manual student approval**.
        - **Required Business Feedback Loop:**
          `Marketing Campaign` $\\rightarrow$ `Requested Demand` $\\rightarrow$ `Staff/Revision Capacity Check` $\\rightarrow$ `Package Delivery` $\\rightarrow$ `Client Satisfaction` $\\rightarrow$ `Future Demand`
        """
    )
    col_sys1, col_sys2 = st.columns(2)
    with col_sys1:
        st.markdown("#### Active Stage 1 & Stage 2 Modules")
        st.success(
            "- **Stage 1 Core:** Startup Capital ($6,500), Opening Cash ($4,000), Algebra 2 Math Panel, Dated Event Ledger, Save/Load JSON\n"
            "- **Stage 2 Departmental AI Tabs:** Copy-ready prompts + manual recommendation import & approval gate (Finance, Operations, Marketing, Reviewer)\n"
            "- **Stage 2 Report Center:** Reconciled Income Statement, Cash-Flow, Balance Sheet, Budget Variance, Scenarios & 2-Report Decision Memos\n"
            "- **Stage 2 Costed Marketing Studio:** Itemized ad budgeting, equal-budget A/B comparison, duplicate campaign protection & approval gate"
        )
    with col_sys2:
        st.markdown("#### Planned Later Modules (Not Yet Active)")
        st.warning(
            "- **Stage 3 (Planned):** Cross-Course Connections Panel & Snapshot-Based Practice Assessment Generator\n"
            "- **Stage 4 (Optional Extension):** Fictional Client Storefront"
        )

with tab_inputs:
    st.subheader("Startup Financing & Editable Monthly Parameters")
    st.info("Changes saved here update baseline assumptions for future simulation rounds without rewriting historical ledger transactions.")

    c_fund, c_ops = st.columns(2)
    with c_fund:
        st.markdown("#### Startup Balances (Read-Only Baseline Ledger)")
        fund_df = pd.DataFrame([
            {"Item": "Owner Contribution (Starting Capital)", "Amount ($)": state["funding"]["owner_contribution"], "Accounting Treatment": "Equity (Not Sales Revenue)"},
            {"Item": "Computer & Design Equipment Assets", "Amount ($)": state["funding"]["equipment_assets"], "Accounting Treatment": "Capital Asset (Not Operating Expense)"},
            {"Item": "Pre-Opening Software & Setup Expense", "Amount ($)": state["funding"]["pre_opening_expense"], "Accounting Treatment": "Opening Retained Earnings (-$1,000)"},
            {"Item": "Post-Startup Opening Cash", "Amount ($)": state["funding"]["post_startup_cash"], "Accounting Treatment": "Opening Spendable Cash"},
            {"Item": "Current Loan Debt Balance", "Amount ($)": state["funding"]["loan_balance"], "Accounting Treatment": "Liability"},
            {"Item": "Client Pass-Through Media Liability", "Amount ($)": state["funding"]["client_media_liability"], "Accounting Treatment": "Escrow Liability (Not Revenue)"},
        ])
        st.table(fund_df)

    with c_ops:
        st.markdown("#### Edit Operating & Cost Parameters")
        with st.form("edit_params_form"):
            new_price = st.number_input("Base Package Price p₀ ($)", min_value=1.0, value=float(params["base_price"]), step=5.0)
            new_d0 = st.number_input("Baseline Monthly Demand D₀ (packages)", min_value=0, value=int(params["D0"]), step=1)
            new_staff_hrs = st.number_input("Productive Staff Hours / Month", min_value=0.0, value=float(params["staff_hours"]), step=4.0)
            new_hrs_unit = st.number_input("Base Hours per Package", min_value=0.5, value=float(params["hours_per_unit"]), step=0.5)
            new_rev_hrs = st.number_input("Extra Revision Hours / Package", min_value=0.0, value=float(params["revision_hours_per_package"]), step=0.5)
            new_rev_rate = st.number_input("Extra Revision Hourly Cost ($/hr)", min_value=0.0, value=float(params["extra_revision_hourly_cost"]), step=1.0)

            st.markdown("**Variable Cost Lines ($/package):**")
            vc1, vc2 = st.columns(2)
            v_des = vc1.number_input("Designer Labor ($)", min_value=0.0, value=float(cost_lines["variable"]["designer_labor"]), step=1.0)
            v_ass = vc2.number_input("Licensed Assets ($)", min_value=0.0, value=float(cost_lines["variable"]["licensed_assets"]), step=1.0)
            v_prt = vc1.number_input("Printing & Delivery ($)", min_value=0.0, value=float(cost_lines["variable"]["printing_delivery"]), step=1.0)
            v_rev = vc2.number_input("Quality/Revision Allowance ($)", min_value=0.0, value=float(cost_lines["variable"]["quality_revision_allowance"]), step=1.0)

            st.markdown("**Fixed Monthly Overhead ($/month):**")
            fc1, fc2 = st.columns(2)
            f_sof = fc1.number_input("Software ($/mo)", min_value=0.0, value=float(cost_lines["fixed"]["software"]), step=10.0)
            f_wrk = fc2.number_input("Workspace ($/mo)", min_value=0.0, value=float(cost_lines["fixed"]["workspace"]), step=10.0)
            f_adm = fc1.number_input("Admin ($/mo)", min_value=0.0, value=float(cost_lines["fixed"]["admin"]), step=10.0)
            f_hst = fc2.number_input("Hosting ($/mo)", min_value=0.0, value=float(cost_lines["fixed"]["hosting"]), step=10.0)

            if st.form_submit_button("Approve & Save Parameter Changes"):
                params["base_price"] = f"{new_price:.2f}"
                params["D0"] = int(new_d0)
                params["staff_hours"] = f"{new_staff_hrs:.2f}"
                params["hours_per_unit"] = f"{new_hrs_unit:.2f}"
                params["revision_hours_per_package"] = f"{new_rev_hrs:.2f}"
                params["extra_revision_hourly_cost"] = f"{new_rev_rate:.2f}"
                cost_lines["variable"] = {
                    "designer_labor": f"{v_des:.2f}",
                    "licensed_assets": f"{v_ass:.2f}",
                    "printing_delivery": f"{v_prt:.2f}",
                    "quality_revision_allowance": f"{v_rev:.2f}",
                }
                cost_lines["fixed"] = {
                    "software": f"{f_sof:.2f}",
                    "workspace": f"{f_wrk:.2f}",
                    "admin": f"{f_adm:.2f}",
                    "hosting": f"{f_hst:.2f}",
                }
                state["capacity"]["derived_capacity"] = compute_capacity(params)
                st.success("Parameters updated and validated.")
                st.rerun()

with tab_sim:
    st.subheader("Advance Simulation Month & Inspect Dated Event Ledger")
    with st.form("run_month_form"):
        sc1, sc2, sc3, sc4 = st.columns(4)
        sim_month = sc1.text_input("Simulation Month (YYYY-MM)", value=f"2027-{len(st.session_state.round_history)+1:02d}")
        req_units = sc2.number_input("Requested Packages", min_value=0, value=int(params["D0"]), step=1)
        ad_spend = sc3.number_input("Own-Agency Ad Expense ($)", min_value=0.0, value=0.0, step=25.0)
        run_tag = sc4.text_input("Unique Run ID", value=f"round-{len(st.session_state.round_history)+1:02d}")

        with st.expander("Optional Financing / Capex / Pass-Through Events"):
            fc1, fc2, fc3, fc4 = st.columns(4)
            loan_in = fc1.number_input("Loan Received ($)", min_value=0.0, value=0.0, step=100.0)
            prin_out = fc2.number_input("Loan Principal Repaid ($)", min_value=0.0, value=0.0, step=50.0)
            int_out = fc3.number_input("Loan Interest Expense ($)", min_value=0.0, value=0.0, step=10.0)
            capex_out = fc4.number_input("New Equipment Capex ($)", min_value=0.0, value=0.0, step=100.0)

        if st.form_submit_button("Approve & Advance Simulation One Month"):
            try:
                updated_state, round_res = simulate_month(
                    state,
                    month_str=sim_month,
                    requested=int(req_units),
                    ad_cost=ad_spend,
                    run_id=run_tag.strip(),
                    loan_received=loan_in,
                    loan_principal_repaid=prin_out,
                    interest_expense=int_out,
                    additional_capex=capex_out,
                )
                if round_res["status"] == "duplicate_ignored":
                    st.warning(f"Duplicate Run ID `{run_tag}` ignored — no duplicate transactions were recorded.")
                else:
                    st.session_state.sim_state = updated_state
                    st.session_state.round_history.append(round_res)
                    st.success(
                        f"Committed `{sim_month}` (`v{updated_state['state_version']}`): "
                        f"Sold {round_res['sold']}/{round_res['requested']} pkgs | "
                        f"Revenue ${round_res['revenue']} | Operating Profit ${round_res['operating_profit']} | "
                        f"Closing Cash ${round_res['closing_cash']}"
                    )
                    st.rerun()
            except ValueError as err:
                st.error(str(err))

    if st.session_state.round_history:
        st.markdown("#### Committed Monthly Rounds")
        st.dataframe(pd.DataFrame(st.session_state.round_history), use_container_width=True)

    st.markdown("#### Dated Event Ledger & Time Horizon View")
    horizon = st.radio(
        "Aggregation Horizon (Derived from One Underlying Dated Ledger)",
        ["Monthly (Actual Ledger)", "Yearly Rollup", "Daily Modeled Allocation (Working Days = 22)"],
        horizontal=True,
    )
    if state["ledger"]:
        df_led = pd.DataFrame(state["ledger"])
        df_led["amount_num"] = df_led["amount"].astype(float)
        if horizon == "Monthly (Actual Ledger)":
            st.dataframe(df_led.drop(columns=["amount_num"]), use_container_width=True)
        elif horizon == "Yearly Rollup":
            df_led["year"] = df_led["month"].str.slice(0, 4)
            yr_df = df_led.groupby(["year", "event_type"], as_index=False)["amount_num"].sum()
            yr_df.rename(columns={"amount_num": "total_amount ($)"}, inplace=True)
            st.dataframe(yr_df, use_container_width=True)
        else:
            st.info("Modeled Daily Allocation: Monthly totals divided by 22 working days (modeled allocation, not observed daily transactions).")
            day_df = df_led.groupby(["month", "event_type"], as_index=False)["amount_num"].sum()
            day_df["modeled_per_working_day ($)"] = (day_df["amount_num"] / 22.0).round(2)
            st.dataframe(day_df, use_container_width=True)

        st.download_button(
            "Export Ledger CSV",
            data=df_led.drop(columns=["amount_num"]).to_csv(index=False),
            file_name=f"team_lucas_mkt1_ledger_v{state['state_version']}.csv",
            mime="text/csv",
        )
    else:
        st.caption("No transactions recorded yet. Advance a month above or run the fixture replay in Tab 8.")

with tab_depts:
    st.subheader("Departmental AI Workspaces & Manual Recommendation Gate")
    st.info(
        "**Manual Handoff Workflow:** This dashboard makes no external paid API calls. Copy the assembled prompt + current JSON snapshot into your external Gemini Gem / Skill, then log or import the proposal below for student verification and approval."
    )

    dept_choice = st.selectbox(
        "Select Department Role",
        ["Finance", "Operations", "Market and Marketing", "Independent Reviewer"],
    )

    common_block = (
        "You support Career Venture Lab, a fictional student business simulation. Read the selected course-career card, "
        "business brief, data dictionary and current snapshot. Identify team_id, course, pathway_id, snapshot_id, "
        "state_version, simulation date and period. If critical inputs are missing, ask for them; do not invent evidence. "
        "Use only this version; reject mismatched or stale records. Label supplied, researched, estimated and simulated values. "
        "Explain the named course skill, level, equations, variables, units, domains and assumptions. Distinguish demand "
        "from completed sales, profit from cash, revenue from financing, and principal from interest. Show calculations and "
        "uncertainty. Do not commit changes, advance time, launch ads, send messages, or publish. Return: role; snapshot/version; "
        "question; evidence; method/calculation; recommendation; two alternatives; uncertainty; cross-department effects; "
        "proposed_changes; checks_needed; approval_status=pending."
    )

    dept_blocks = {
        "Finance": (
            "You are the Local-business marketing agency finance analyst. Use MKT-1 cost rows ($80/unit variable, $900/month fixed) "
            "and accounting rules. Reconcile revenue, variable expense, fixed expense, marketing, cash and equity. Separate startup "
            "assets ($1,500) and pre-opening expenses ($1,000) from current-period costs. Compare a price change and a capacity change "
            "using the Algebra 2 adapter. Flag cash below $800. Return calculation, report IDs, alternatives and proposed_changes only."
        ),
        "Operations": (
            "You are the Local-business marketing agency operations planner. Apply exactly: "
            "capacity=floor(staff_hours/(hours_per_unit+revision_hours_per_package)); sold=min(requested,capacity); "
            "variable_per_unit=sum(vlines)+revision_hours_per_package*extra_revision_hourly_cost. Identify bottleneck and lost demand. "
            "Compare one extra-resource scenario with a lower-demand scenario. Show hours and units. Do not invent capacity or change rules silently."
        ),
        "Market and Marketing": (
            "You are the Local-business marketing agency market/marketing specialist. Offerings: Flyer design package; social campaign "
            "package; event promotion package. Use approved evidence and the Algebra 2 demand model q(p)=max(0, 24 - 0.048*p). Draft a flyer "
            "or ad with itemized cost: design_hours*hourly_rate+assets+print_quantity*print_unit_cost+distribution+placement. No automatic "
            "demand lift. Compare two variants and propose a measurable experiment. Return draft and pending campaign_id; never launch."
        ),
        "Independent Reviewer": (
            "You review the Local-business marketing agency system. Verify the current snapshot and independently recompute one report, "
            "one capacity result, and the MKT-1 revision shock test (extra revisions=2 hrs/pkg -> cap=8, unit var=$90, rev=$2,000, var=$720, "
            "profit=$380). Baseline client budgets=0; pass-through funds are cash + liability, never agency fee revenue. Return verified "
            "evidence, corrections, unresolved questions and pass/revise test results; student approves."
        ),
    }

    algebra2_adapter = (
        f"Course Adapter: Algebra 2 | Active Skill: {state['selected_skill']} | Approved Level: {state['selected_level']}. "
        f"Foundation: R(q)=p0*q, C(q)=F+v*q on 0<=q<=capacity; break-even=F/(p0-v). "
        f"Applied: q(p)=max(0, 2*D0 - (D0/p0)*p), s=min(capacity, floor(q(p))). "
        f"Advanced: extra shift adds floor(extra_hours/hours_per_unit) units and extra_hours*hourly_rate to fixed costs."
    )

    assembled_prompt = (
        f"=== 1. COMMON OPERATING INSTRUCTIONS ===\n{common_block}\n\n"
        f"=== 2. DEPARTMENT BLOCK ({dept_choice.upper()}) ===\n{dept_blocks[dept_choice]}\n\n"
        f"=== 3. COURSE ADAPTER (ALGEBRA 2) ===\n{algebra2_adapter}\n\n"
        f"=== 4. APPROVED SNAPSHOT ({state['snapshot_id']} | v{state['state_version']}) ===\n"
        f"{json.dumps(state, indent=2)}"
    )

    st.text_area("Copy-Ready Assembled Prompt (Handbook Order)", value=assembled_prompt, height=240)

    st.markdown("#### Log or Import Departmental Recommendation (Human Approval Gate)")
    with st.form("log_rec_form"):
        rc1, rc2, rc3 = st.columns(3)
        rec_role = rc1.selectbox(
            "Role",
            ["Finance", "Operations", "Market and Marketing", "Independent Reviewer"],
            index=["Finance", "Operations", "Market and Marketing", "Independent Reviewer"].index(dept_choice),
        )
        rec_ver = rc2.number_input("Snapshot Version Referenced", min_value=1, value=int(state["state_version"]), step=1)
        rec_checker = rc3.text_input("Independent Student Checker Name", value="")
        rec_question = st.text_input(
            "Decision Question Asked",
            value="Compare baseline price $250 with a 10% increase ($275) on snapshot v" + str(state["state_version"]),
        )
        rec_summary = st.text_area("AI Recommendation & Calculation Summary", value="")
        rec_uncert = st.text_input(
            "Uncertainty / Assumptions Flagged",
            value="Assumes linear demand q(p)=24-0.048p holds locally; unmet demand is lost.",
        )

        if st.form_submit_button("Import Recommendation as PENDING"):
            ok, msg, new_st = import_recommendation(
                state,
                {
                    "team_id": state["team_id"],
                    "role": rec_role,
                    "snapshot_id": f"snap-{int(rec_ver):03d}",
                    "state_version": int(rec_ver),
                    "question": rec_question,
                    "recommendation": rec_summary,
                    "uncertainty": rec_uncert,
                    "checker": rec_checker,
                },
            )
            if ok:
                st.session_state.sim_state = new_st
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    if state.get("recommendations"):
        st.markdown("#### Recorded Departmental Proposals")
        for idx, rec in enumerate(state["recommendations"]):
            with st.container(border=True):
                st.markdown(
                    f"**{rec['rec_id']} — {rec['role']}** | Snapshot `{rec['snapshot_id']}` (`v{rec['state_version']}`) | "
                    f"Status: **`{rec['approval_status'].upper()}`** | Checker: `{rec['checker'] or 'Unassigned'}`"
                )
                st.write(f"**Question:** {rec['question']}")
                st.write(f"**Proposal:** {rec['recommendation']}")
                st.caption(f"**Uncertainty:** {rec['uncertainty']}")
                b1, b2 = st.columns([1, 5])
                if rec["approval_status"] == "pending":
                    if b1.button("Approve Proposal", key=f"app_rec_{idx}"):
                        rec["approval_status"] = "approved"
                        st.rerun()
                    if b2.button("Reject Proposal", key=f"rej_rec_{idx}"):
                        rec["approval_status"] = "rejected"
                        st.rerun()

with tab_reports:
    st.subheader("Report Center & Two-Report Decision Memos")
    st.caption(
        f"Generated from underlying dated ledger without mutating simulation state | "
        f"Team: **{state['team_id']}** | Snapshot: **`{state['snapshot_id']}` (`v{state['state_version']}`)** | "
        f"Status: **{'ACTUAL LEDGER' if state['ledger'] else 'PRE-ROUND BASELINE'}**"
    )

    rep = generate_financial_reports(state)

    r_col1, r_col2, r_col3 = st.columns(3)
    with r_col1:
        st.markdown("#### 1. Income Statement")
        st.table(pd.DataFrame(list(rep["income_statement"].items()), columns=["Line Item", "Value"]))
    with r_col2:
        st.markdown("#### 2. Cash-Flow Statement")
        st.table(pd.DataFrame(list(rep["cash_flow"].items()), columns=["Cash Flow Item", "Value"]))
    with r_col3:
        st.markdown("#### 3. Simplified Balance Sheet")
        st.table(pd.DataFrame(list(rep["balance_sheet"].items()), columns=["Balance Sheet Item", "Value"]))

    st.markdown("#### 4. Budget vs. Actual Variance Report")
    st.table(pd.DataFrame(rep["budget_variance"]))

    st.markdown("#### 5. Forecast Scenarios (Baseline 1.00x / Upside 1.10x / Downside 0.90x — Projected Only)")
    base_d = int(params["D0"])
    cap_now = compute_capacity(params)
    p_now = float(params["base_price"])
    v_now = float(unit_var)
    f_now = float(fixed_mo)
    scen_rows = []
    for label, mult in [("Downside (0.90x)", 0.90), ("Baseline (1.00x)", 1.00), ("Upside (1.10x)", 1.10)]:
        req_s = int(math.floor(base_d * mult))
        sold_s = min(req_s, cap_now)
        rev_s = p_now * sold_s
        exp_s = f_now + (v_now * sold_s)
        scen_rows.append({
            "Scenario (Assumed Multiplier)": label,
            "Projected Demand": req_s,
            "Capacity Cap": cap_now,
            "Projected Completed Sales": sold_s,
            "Projected Revenue ($)": f"{rev_s:.2f}",
            "Projected Total Cost ($)": f"{exp_s:.2f}",
            "Projected Operating Profit ($)": f"{(rev_s - exp_s):.2f}",
        })
    st.table(pd.DataFrame(scen_rows))
    st.caption(rep["meta"]["accounting_notes"])

    ex1, ex2 = st.columns(2)
    report_csv = (
        f"# Team: {state['team_id']} | Pathway: {state['pathway_id']} | Snapshot: {state['snapshot_id']} | Version: v{state['state_version']}\n"
        + pd.DataFrame(rep["budget_variance"]).to_csv(index=False)
    )
    ex1.download_button(
        "Download Financial Report Packet (CSV)",
        data=report_csv,
        file_name=f"team_lucas_reports_v{state['state_version']}.csv",
        mime="text/csv",
    )
    printable_html = f"""
    <html><head><title>Career Venture Lab Report - {state['team_id']}</title></head>
    <body style="font-family: Arial, sans-serif; margin: 24px;">
    <h2>Career Venture Lab — Financial & Operating Report</h2>
    <p><strong>Team:</strong> {state['team_id']} | <strong>Pathway:</strong> {state['pathway_id']} ({state['course']}) |
    <strong>Snapshot:</strong> {state['snapshot_id']} (v{state['state_version']}) | <strong>Skill/Level:</strong> {state['selected_skill']} ({state['selected_level']})</p>
    <h3>Income Statement</h3><pre>{json.dumps(rep['income_statement'], indent=2)}</pre>
    <h3>Cash-Flow Reconciliation</h3><pre>{json.dumps(rep['cash_flow'], indent=2)}</pre>
    <h3>Simplified Balance Sheet</h3><pre>{json.dumps(rep['balance_sheet'], indent=2)}</pre>
    <p><em>{rep['meta']['accounting_notes']}</em></p>
    </body></html>
    """
    ex2.download_button(
        "Download Print-Ready Report (HTML -> Print to PDF)",
        data=printable_html,
        file_name=f"team_lucas_printable_report_v{state['state_version']}.html",
        mime="text/html",
    )

    st.divider()
    st.markdown("#### Two-Report Decision Memo Log (Required After Every Business Round)")
    with st.form("decision_memo_form"):
        dm1, dm2 = st.columns(2)
        dm_question = dm1.text_input("Decision Question", value="Should we keep package price at $250 or adjust staffing/pricing for next month?")
        dm_reports = dm2.multiselect(
            "Cite at Least Two Reports",
            ["Income Statement", "Cash-Flow Statement", "Budget Variance", "Operations Capacity", "Forecast Scenarios", "Balance Sheet"],
            default=["Income Statement", "Cash-Flow Statement"],
        )
        dm_alts = st.text_area("Baseline vs. Two Alternatives Compared", value="Baseline ($250, 10 cap) vs. Alt 1 ($275 price) vs. Alt 2 (+16 hrs extra shift).")
        dm_choice = dm1.text_input("Chosen Action & Predicted Outcome", value="Hold $250 price; test low-cost flyer campaign; predict 10 sold packages and +$800 operating profit.")
        dm_owner = dm2.text_input("Decision Owner & Student Checker", value="Owner: Team Lead | Checker: Math Lead")
        if st.form_submit_button("Save Decision Memo to Snapshot"):
            if len(dm_reports) < 2:
                st.error("Handbook rule: cite at least TWO reports in every decision memo.")
            else:
                state["decisions"].append({
                    "decision_id": f"DEC-{len(state['decisions']) + 1:03d}",
                    "snapshot_id": state["snapshot_id"],
                    "state_version": state["state_version"],
                    "question": dm_question,
                    "report_ids": dm_reports,
                    "alternatives": dm_alts,
                    "chosen_action": dm_choice,
                    "owner_checker": dm_owner,
                })
                st.success("Decision memo saved to snapshot.")
                st.rerun()

    if state["decisions"]:
        st.dataframe(pd.DataFrame(state["decisions"]), use_container_width=True)

with tab_mkt:
    st.subheader("Costed Marketing Studio (Own-Agency Promotion)")
    st.info(
        "**Handbook Rule:** Advertising costs money and never creates automatic sales lift. "
        "Client pass-through media budgets ($0 at baseline) are tracked as cash + liability, separate from own-agency ad spend."
    )

    mc_left, mc_right = st.columns(2)
    with mc_left:
        st.markdown("#### Draft & Cost an Agency Campaign")
        camp_id = st.text_input("Unique Campaign ID", value=f"CMP-2027-{len(state['campaigns']) + 1:02d}")
        camp_month = st.text_input("Campaign Month (YYYY-MM)", value="2027-02")
        camp_offering = st.selectbox("Target Offering", ["OFF-01: Campaign package ($250)", "OFF-02: Flyer design package ($150)", "OFF-03: Social campaign package ($300)"])
        camp_channel = st.selectbox("Channel", ["Printed Local Flyer", "Local Business Email", "Social Media Post", "Digital Search Ad"])
        camp_audience = st.text_input("Target Local Audience", value="Independent cafes and retail shops within 5 miles")
        camp_claim = st.text_input("Truthful, Verified Ad Claim", value="Complete local campaign package delivered on schedule with transparent revision tracking.")
        camp_variant = st.selectbox("A/B Test Variant Label", ["Variant A (Control)", "Variant B (Treatment)"])

        cc1, cc2, cc3 = st.columns(3)
        d_hrs = cc1.number_input("Design Labor Hours", min_value=0.0, value=2.0, step=0.5)
        d_rate = cc2.number_input("Design Hourly Rate ($/hr)", min_value=0.0, value=20.0, step=5.0)
        ast_cost = cc3.number_input("Licensed Assets ($)", min_value=0.0, value=10.0, step=5.0)
        p_qty = cc1.number_input("Print Quantity (units)", min_value=0, value=100, step=25)
        p_unit = cc2.number_input("Print Unit Cost ($/unit)", min_value=0.0, value=0.25, step=0.05)
        dist_cost = cc3.number_input("Distribution Cost ($)", min_value=0.0, value=15.0, step=5.0)
        place_cost = st.number_input("Ad Placement Fee ($)", min_value=0.0, value=10.0, step=5.0)

        total_camp_cost = compute_campaign_cost(d_hrs, d_rate, ast_cost, int(p_qty), p_unit, dist_cost, place_cost)
        st.metric("Calculated Total Campaign Cost", f"${total_camp_cost:,.2f}")

    with mc_right:
        st.markdown("#### Printable Flyer / Ad Copy Preview & Experiment Tracker")
        ad_copy = (
            f"[{camp_variant}] {camp_offering}\n"
            f"Audience: {camp_audience}\n"
            f"Headline: Grow Your Local Reach with Team Lucas Marketing Agency\n"
            f"Verified Offer: {camp_claim}\n"
            f"Contact: demo@teamlucas-mkt1.example (Fictional School Simulation — No Real Purchases)"
        )
        st.text_area("Copyable & Printable Draft Text", value=ad_copy, height=150)

        ec1, ec2, ec3 = st.columns(3)
        est_reach = ec1.number_input("Assumed Reach / Impressions", min_value=0, value=250, step=50)
        obs_inq = ec2.number_input("Observed Inquiries", min_value=0, value=8, step=1)
        obs_conv = ec3.number_input("Attributed Conversions (Bookings)", min_value=0, value=0, step=1)
        cac_preview = f"${(total_camp_cost / Decimal(obs_conv)):.2f}" if obs_conv > 0 else "N/A (0 conversions)"
        st.write(f"**Customer Acquisition Cost (CAC):** `{cac_preview}` *(Note: Correlation in sales logs is not causal proof without random assignment.)*")

        rev_ok = st.checkbox("Fact-checked & approved by Independent Reviewer and Student Owner")
        if st.button("Approve & Launch Campaign into Dated Ledger"):
            try:
                new_st, c_res = launch_approved_campaign(
                    state,
                    campaign_id=camp_id,
                    month_str=camp_month,
                    offering_id=camp_offering.split(":")[0],
                    audience=camp_audience,
                    channel=camp_channel,
                    claim=camp_claim,
                    variant_label=camp_variant,
                    design_hours=d_hrs,
                    hourly_rate=d_rate,
                    assets=ast_cost,
                    print_quantity=int(p_qty),
                    print_unit_cost=p_unit,
                    distribution=dist_cost,
                    placement=place_cost,
                    assumed_reach=int(est_reach),
                    inquiries=int(obs_inq),
                    conversions=int(obs_conv),
                    reviewer_approved=rev_ok,
                )
                if c_res["status"] == "duplicate_rejected":
                    st.error(f"Duplicate Campaign ID `{camp_id}` rejected — second launch blocked.")
                else:
                    st.session_state.sim_state = new_st
                    st.success(f"Campaign `{camp_id}` launched and recorded once (${total_camp_cost:.2f}).")
                    st.rerun()
            except ValueError as err:
                st.error(str(err))

    if state.get("campaigns"):
        st.markdown("#### Launched Campaigns Log")
        st.dataframe(pd.DataFrame(state["campaigns"]), use_container_width=True)

with tab_snapshot:
    st.subheader("Durable Save / Load JSON Snapshot")
    st.markdown(
        "Export your JSON snapshot after every decision round or campaign approval, "
        "and reload it anytime to restore exact balances, reports, and version history."
    )
    snap_json = json.dumps(state, indent=2)
    st.download_button(
        f"Download Snapshot JSON (`{state['snapshot_id']}` | `v{state['state_version']}`)",
        data=snap_json,
        file_name=f"team_lucas_mkt1_{state['snapshot_id']}_v{state['state_version']}.json",
        mime="application/json",
    )

    uploaded_snap = st.file_uploader("Restore / Import Snapshot JSON", type=["json"])
    if uploaded_snap is not None:
        try:
            parsed = json.loads(uploaded_snap.read().decode("utf-8"))
            ok, msg, restored_state = validate_and_import_snapshot(parsed, state)
            if ok and restored_state is not None:
                st.session_state.sim_state = restored_state
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        except Exception as exc:
            st.error(f"Import rejected: invalid JSON file ({exc}).")

    if st.button("Reset Simulation to Post-Startup Baseline (v1)"):
        st.session_state.sim_state = default_state()
        st.session_state.round_history = []
        st.success("Reset to Team Lucas MKT-1 post-startup baseline ($4,000 cash, v1).")
        st.rerun()

with tab_tests:
    st.subheader("Stage 1 & Stage 2 Acceptance Verification")
    st.warning("Fixture-Test Mode uses explicit `capacity_override` values ONLY for ledger verification.")

    if st.button("Run All Stage 1 & Stage 2 Acceptance Checks"):
        base = default_state()
        fix_state, fix_res = replay_fixture_rows(base, DEFAULT_FIXTURE_ROWS)

        checks = []
        exp_fix = [
            ("2027-01", 10, "2500.00", "1700.00", "800.00", "4800.00"),
            ("2027-02", 10, "2500.00", "1800.00", "700.00", "5500.00"),
            ("2027-03", 7, "1750.00", "1460.00", "290.00", "5790.00"),
        ]
        for got, (mo, s_exp, r_exp, e_exp, p_exp, c_exp) in zip(fix_res, exp_fix):
            passed = (
                got["sold"] == s_exp
                and got["revenue"] == r_exp
                and got["total_expense"] == e_exp
                and got["operating_profit"] == p_exp
                and got["closing_cash"] == c_exp
            )
            checks.append({
                "Test Case": f"Fixture {mo}",
                "Expected": f"Sold={s_exp}, Rev=${r_exp}, Exp=${e_exp}, Profit=${p_exp}, Cash=${c_exp}",
                "Actual": f"Sold={got['sold']}, Rev=${got['revenue']}, Exp=${got['total_expense']}, Profit=${got['operating_profit']}, Cash=${got['closing_cash']}",
                "Status": "PASS" if passed else "FAIL",
            })

        rep_chk = generate_financial_reports(fix_state)
        rep_ok = (
            rep_chk["cash_flow"]["Cash Reconciliation Match"] is True
            and rep_chk["balance_sheet"]["Balance Sheet Reconciled (A = L + E)"] is True
            and rep_chk["income_statement"]["Net Income / Profit"] == "1790.00"
        )
        checks.append({
            "Test Case": "Stage 2 Report Center Reconciliation",
            "Expected": "Cash Match=True, Balance Sheet (A=L+E)=True, 3-Mo Profit=$1790.00",
            "Actual": f"Cash Match={rep_chk['cash_flow']['Cash Reconciliation Match']}, Balance Match={rep_chk['balance_sheet']['Balance Sheet Reconciled (A = L + E)']}, Profit=${rep_chk['income_statement']['Net Income / Profit']}",
            "Status": "PASS" if rep_ok else "FAIL",
        })

        c_st1, c_res1 = launch_approved_campaign(
            default_state(),
            campaign_id="CMP-TEST-01",
            month_str="2027-02",
            offering_id="OFF-01",
            audience="Local shops",
            channel="Flyer",
            claim="Verified package",
            variant_label="Variant A",
            design_hours=2,
            hourly_rate=20,
            assets=10,
            print_quantity=100,
            print_unit_cost=0.25,
            distribution=15,
            placement=10,
            assumed_reach=200,
            inquiries=5,
            conversions=0,
            reviewer_approved=True,
        )
        _, c_res2 = launch_approved_campaign(
            c_st1,
            campaign_id="CMP-TEST-01",
            month_str="2027-02",
            offering_id="OFF-01",
            audience="Local shops",
            channel="Flyer",
            claim="Verified package",
            variant_label="Variant A",
            design_hours=2,
            hourly_rate=20,
            assets=10,
            print_quantity=100,
            print_unit_cost=0.25,
            distribution=15,
            placement=10,
            assumed_reach=200,
            inquiries=5,
            conversions=0,
            reviewer_approved=True,
        )
        camp_ok = (
            c_res1["status"] == "launched"
            and c_res1["campaign"]["total_cost"] == "100.00"
            and c_res1["campaign"]["cac"] == "N/A"
            and c_res2["status"] == "duplicate_rejected"
        )
        checks.append({
            "Test Case": "Stage 2 Campaign Cost ($100), CAC=N/A & Duplicate Block",
            "Expected": "Cost=$100.00, CAC=N/A, 2nd launch=duplicate_rejected",
            "Actual": f"Cost=${c_res1['campaign']['total_cost']}, CAC={c_res1['campaign']['cac']}, 2nd={c_res2['status']}",
            "Status": "PASS" if camp_ok else "FAIL",
        })

        shock_st = default_state()
        shock_st["parameters"]["revision_hours_per_package"] = "2.00"
        _, shock_res = simulate_month(shock_st, month_str="2027-01", requested=12, run_id="chk-shock")
        shock_ok = (
            shock_res["capacity"] == 8
            and shock_res["unit_variable_cost"] == "90.00"
            and shock_res["revenue"] == "2000.00"
            and shock_res["variable_expense"] == "720.00"
            and shock_res["operating_profit"] == "380.00"
        )
        checks.append({
            "Test Case": "MKT Extra Revisions Shock (+2 hrs/pkg)",
            "Expected": "Cap=8, UnitVar=$90.00, Rev=$2000.00, Var=$720.00, Profit=$380.00",
            "Actual": f"Cap={shock_res['capacity']}, UnitVar=${shock_res['unit_variable_cost']}, Rev=${shock_res['revenue']}, Var=${shock_res['variable_expense']}, Profit=${shock_res['operating_profit']}",
            "Status": "PASS" if shock_ok else "FAIL",
        })

        st.session_state.last_test_report = pd.DataFrame(checks)

    if st.session_state.last_test_report is not None:
        st.table(st.session_state.last_test_report)