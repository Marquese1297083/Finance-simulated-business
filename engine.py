"""Deterministic simulation engine and ledger rules for Team Lucas MKT-1 (Algebra 2)."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any, Dict, List, Optional, Tuple

TWO_PLACES = Decimal("0.01")


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
            "Career Venture Lab Student Handbook (Revised Nov 2026), Pages 24, 68, 102-106."
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
                "capacity_rule": "Disabled in Stage 1 primary acceptance mode",
                "active": False,
            },
            {
                "offering_id": "OFF-03",
                "name": "Social campaign package (Optional secondary)",
                "unit": "package",
                "price": "300.00",
                "demand_rule": "Requires separate cost/capacity allocation before enabling",
                "capacity_rule": "Disabled in Stage 1 primary acceptance mode",
                "active": False,
            },
            {
                "offering_id": "OFF-04",
                "name": "Event promotion package (Optional secondary)",
                "unit": "package",
                "price": "350.00",
                "demand_rule": "Requires separate cost/capacity allocation before enabling",
                "capacity_rule": "Disabled in Stage 1 primary acceptance mode",
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
    """
    Advance simulation by one monthly step and record dated ledger entries.
    If run_id was already processed, returns state unchanged (idempotent protection).
    """
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
    """
    Validate imported snapshot JSON against required fields, team_id, non-negativity,
    and state_version rules (reject stale versions).
    """
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
