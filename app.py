"""Career Venture Lab — Stage 1 Streamlit Dashboard for Team Lucas (MKT-1 | Algebra 2)."""
from __future__ import annotations

import csv
from decimal import Decimal
import json
import math
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine import (
    compute_capacity,
    compute_fixed_cost,
    compute_unit_variable_cost,
    d,
    default_state,
    replay_fixture_rows,
    simulate_month,
    validate_and_import_snapshot,
)

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

# Header & Status Banner
st.title("📊 Career Venture Lab — Local-Business Marketing Agency (`MKT-1`)")
st.caption(
    f"**Team ID:** {state['team_id']} | **Course:** {state['course']} | "
    f"**State Version:** `v{state['state_version']}` | **Snapshot ID:** `{state['snapshot_id']}` | "
    f"**Build Stage:** Stage 1 (Deterministic Core, Ledger, Save/Load, Acceptance Tests)"
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

# Persistent Math Skills & Challenge Level Panel (Visible from Overview)
with st.expander("📐 Persistent Algebra 2 Math Skills & Challenge Level Panel", expanded=True):
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
            f"**Level: Foundation** — Hold package price $p_0 = \${p0:.2f}$ fixed. "
            f"Model $R(q) = {p0:.0f}q$ and $C(q) = {f_cost:.0f} + {v_cost:.0f}q$ on feasible domain $0 \le q \le {cap}$ packages/month."
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
                f"**Break-Even Calculation:** $q = \frac{{{f_cost:.2f}}}{{{p0:.2f} - {v_cost:.2f}}} = {be_exact:.2f}$ "
                f"→ **{be_units} whole packages/month** | Status: **{feasible_txt}**."
            )
        else:
            st.error("No positive break-even exists because unit price is less than or equal to variable cost ($p_0 \le v$) while $F > 0$.")

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
                height=380,
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.dataframe(df_math, use_container_width=True, height=340)
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
            f"**Level: Applied** — Linear demand $q(p) = \max(0, {intercept:.0f} - {slope:.4f}p)$ on price domain "
            f"$0 \le p \le \${p_max:.2f}$. Completed sales are capped at capacity: $s(p) = \min({cap}, \lfloor q(p) \rfloor)$."
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
                height=380,
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.dataframe(df_app, use_container_width=True, height=340)

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
        st.caption("**Interpretation Prompt:** Why does lowering price below the capacity breakpoint ($p = \$291.67$) stop increasing completed sales when capacity is capped at 10 packages?")

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
            f"**Inequality Check:** Fixed + Shift Cost = $\${f_cost:.2f} + {extra_hours}(\${extra_hr_rate:.2f}) = \${new_fixed:.2f} "
            f"{'\le' if budget_ok else '>'} \${shift_budget_cap:.2f}$ (**{'Feasible' if budget_ok else 'Exceeds Budget'}**). "
            f"New Capacity = ${cap} + \lfloor {extra_hours}/{hrs_pkg:.1f} \rfloor = {new_cap}$ packages."
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
            height=350,
        )
        st.plotly_chart(fig_adv, use_container_width=True)
        st.caption("**Interpretation Prompt:** At what minimum monthly demand $q$ does the Extra-Shift Plan overtake the Baseline Plan in profit, and when would extrapolating linear demand fail?")

# Main Navigation Tabs
tab_overview, tab_inputs, tab_sim, tab_snapshot, tab_tests = st.tabs([
    "1. Overview & System Map",
    "2. Inputs & Startup Funding",
    "3. Run Simulation & Ledger",
    "4. Save / Load JSON Snapshot",
    "5. Stage 1 Acceptance Tests",
])

with tab_overview:
    st.subheader("System Architecture & Departmental Feedback Loop")
    st.markdown(
        """
        **How Team Lucas's Operating System Works (Stage 1 Core):**
        - **Manual vs. Automatic Boundaries:** All financial math, capacity caps, and ledger totals are computed **automatically** by Python (`engine.py`). All parameter edits, AI recommendations (Stage 2), and monthly advances require **manual student approval**.
        - **Required Business Feedback Loop:**
          `Marketing Campaign` $\rightarrow$ `Requested Demand` $\rightarrow$ `Staff/Revision Capacity Check` $\rightarrow$ `Package Delivery` $\rightarrow$ `Client Satisfaction` $\rightarrow$ `Future Demand`
        """
    )
    col_sys1, col_sys2 = st.columns(2)
    with col_sys1:
        st.markdown("#### Active Stage 1 Modules")
        st.success(
            "- **Startup Capital & Cost Lines:** MKT-1 exact balances ($6,500 capital, $4,000 opening cash)\n"
            "- **Algebra 2 Math Panel:** Foundation, Applied, and Advanced interactive equations\n"
            "- **Dated Event Ledger:** Single source of truth for daily, monthly, and yearly rollups\n"
            "- **Snapshot JSON Contract:** Version-locked (`v1+`) export/import with duplicate-run protection"
        )
    with col_sys2:
        st.markdown("#### Planned Later Modules (Not Yet Active)")
        st.warning(
            "- **Stage 2 (Planned):** Departmental AI Assistant Tabs (Finance, Operations, Marketing, Reviewer), Full Report Center (CSV/PDF), Costed Marketing Studio\n"
            "- **Stage 3 (Planned):** Cross-Course Connections Panel & Snapshot-Based Practice Assessments\n"
            "- **Stage 4 (Optional Extension):** Fictional Storefront"
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
        st.caption("No transactions recorded yet. Advance a month above or run the Stage 1 fixture replay in Tab 5.")

with tab_snapshot:
    st.subheader("Durable Save / Load JSON Snapshot")
    st.markdown(
        "Browser session state is temporary. Export your JSON snapshot after every decision round, "
        "and reload it anytime to restore exact balances and version history."
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
    st.subheader("Stage 1 Fixture Replay & Acceptance Verification")
    st.warning("Fixture-Test Mode uses explicit `capacity_override` values from `sample_data/monthly_fixture.csv` ONLY for ledger verification.")

    if st.button("Run All Stage 1 Acceptance & Fixture Checks"):
        fixture_path = Path(__file__).resolve().parent / "sample_data" / "monthly_fixture.csv"
        with fixture_path.open("r", newline="", encoding="utf-8") as f:
            fixture_rows = list(csv.DictReader(f))

        base = default_state()
        _, fix_res = replay_fixture_rows(base, fixture_rows)

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

        _, zero_res = simulate_month(default_state(), month_str="2027-01", requested=0, run_id="chk-zero")
        zero_ok = zero_res["revenue"] == "0.00" and zero_res["operating_profit"] == "-900.00"
        checks.append({
            "Test Case": "Zero Sales Edge Case",
            "Expected": "Rev=$0.00, Profit=-$900.00, No crash",
            "Actual": f"Rev=${zero_res['revenue']}, Profit=${zero_res['operating_profit']}",
            "Status": "PASS" if zero_ok else "FAIL",
        })

        dup_st1, _ = simulate_month(default_state(), month_str="2027-01", requested=10, run_id="chk-dup")
        dup_st2, dup_res2 = simulate_month(dup_st1, month_str="2027-01", requested=10, run_id="chk-dup")
        dup_ok = dup_res2["status"] == "duplicate_ignored" and len(dup_st1["ledger"]) == len(dup_st2["ledger"])
        checks.append({
            "Test Case": "Duplicate Run ID / Refresh Protection",
            "Expected": "Second run ignored; ledger count unchanged",
            "Actual": f"Status={dup_res2['status']}, Ledger rows={len(dup_st2['ledger'])}",
            "Status": "PASS" if dup_ok else "FAIL",
        })

        ok_stale, _, _ = validate_and_import_snapshot(default_state(), dup_st1)
        wrong_team = default_state()
        wrong_team["state_version"] = 99
        wrong_team["team_id"] = "Wrong Team"
        ok_team, _, _ = validate_and_import_snapshot(wrong_team, dup_st1)
        val_ok = (not ok_stale) and (not ok_team)
        checks.append({
            "Test Case": "Stale Version & Wrong Team Rejection",
            "Expected": "Both rejected (False, False)",
            "Actual": f"Stale accepted={ok_stale}, Wrong team accepted={ok_team}",
            "Status": "PASS" if val_ok else "FAIL",
        })

        st.session_state.last_test_report = pd.DataFrame(checks)

    if st.session_state.last_test_report is not None:
        st.table(st.session_state.last_test_report)
