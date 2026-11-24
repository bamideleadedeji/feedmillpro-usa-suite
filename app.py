"""
FeedMillPro USA — Commercial Least-Cost Feed Formulation & Batch Economics Suite (v2.0)
SciPy Linear Programming Ration Optimizer + Mill Unit Economics + 3-Sheet Excel Workbook Export
"""

import io
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import plotly.express as px
from feed_formulation_engine import DEFAULT_INGREDIENTS, RATION_SPECS, solve_least_cost_ration

st.set_page_config(page_title="FeedMillPro USA — Least-Cost Formulation & Economics", page_icon="🌾", layout="wide")
st.title("🌾 FeedMillPro USA — Commercial Feed Formulation & Batch Economics Suite")
st.caption("Linear Programming Least-Cost Ration Solver (SciPy HiGHS) • Guaranteed Nutritional Specs • Mill Unit Economics • Excel Batch Sheet")
st.divider()

ration_name = st.sidebar.selectbox("Select Target Animal Ration Spec", list(RATION_SPECS.keys()))
specs = RATION_SPECS[ration_name].copy()
specs["min_cp"] = st.sidebar.number_input("Min Crude Protein (%)", 10.0, 35.0, float(specs["min_cp"]), 0.5)
specs["min_me"] = st.sidebar.number_input("Min Metabolizable Energy (kcal/kg)", 2000.0, 3600.0, float(specs["min_me"]), 25.0)
specs["min_ca"] = st.sidebar.number_input("Min Calcium (%)", 0.2, 5.0, float(specs["min_ca"]), 0.05)

st.sidebar.divider()
batch_tons = st.sidebar.number_input("Production Batch Size (Metric Tons)", 1.0, 500.0, 25.0, 1.0)
overhead_ton = st.sidebar.number_input("Mill Processing & Bagging Overhead ($/Ton)", 0.0, 200.0, 28.0, 2.0)
selling_ton = st.sidebar.number_input("Wholesale Selling Price ($/Ton)", 100.0, 1500.0, 445.0, 5.0)

uploaded = st.sidebar.file_uploader("Upload Custom Ingredient Price Matrix (.csv or .xlsx)", type=["csv", "xlsx"])
base_df = (pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)) if uploaded else pd.DataFrame(DEFAULT_INGREDIENTS)

st.subheader("Interactive Raw Material Cost & Nutritional Matrix")
st.caption("Edit any ingredient market price ($/ton) or inclusion limit below to re-solve the optimal least-cost formula instantaneously.")
edited_ing = st.data_editor(base_df, width="stretch", num_rows="dynamic")

try:
    res = solve_least_cost_ration(edited_ing, specs, batch_tons=batch_tons, overhead_per_ton=overhead_ton, selling_price_per_ton=selling_ton)
except Exception as exc:
    st.error(f"Formulation Solver Alert: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Optimal Formula Cost / Ton", f"${res['raw_cost_per_ton']:,.2f}", delta=f"Full Cost w/ Overhead: ${res['total_cost_per_ton']:,.2f}/t")
c2.metric("Finished Cost / 50kg Bag", f"${res['cost_per_50kg_bag']:,.2f}", delta=f"Wholesale: ${selling_ton/20.0:,.2f}/bag")
c3.metric("Net Batch Margin", f"{res['gross_margin_pct']:.1f}%", delta=f"${res['net_margin_per_ton']:,.2f} / Ton")
c4.metric(f"Batch Profit ({batch_tons:.0f} Tons)", f"${res['total_batch_profit']:,.2f}", delta=f"CP: {res['achieved_nutrients']['Crude_Protein_Pct']}% | ME: {res['achieved_nutrients']['Metabolizable_Energy_Kcal']:.0f}")

tab1, tab2, tab3 = st.tabs(["⚖️ Optimal Batch Mixing Sheet", "📊 Cost & Inclusion Breakdown", "📥 3-Sheet Excel Mill Workbook"])

with tab1:
    st.dataframe(res["df"][["Ingredient", "Optimal_Inclusion_Pct", "Batch_Kg", "Cost_Per_Ton_USD", "Cost_Contribution_Per_Ton_USD", "Total_Batch_Cost_USD"]], width="stretch")
    st.info(f"Guaranteed Achieved Analysis: Crude Protein **{res['achieved_nutrients']['Crude_Protein_Pct']}%** | Energy **{res['achieved_nutrients']['Metabolizable_Energy_Kcal']:.0f} kcal/kg** | Calcium **{res['achieved_nutrients']['Calcium_Pct']}%** | Phosphorus **{res['achieved_nutrients']['Phosphorus_Pct']}%** | Fiber **{res['achieved_nutrients']['Crude_Fiber_Pct']}%**")

with tab2:
    col1, col2 = st.columns(2)
    col1.plotly_chart(px.pie(res["df"][res["df"]["Optimal_Inclusion_Pct"] > 0], names="Ingredient", values="Optimal_Inclusion_Pct", title="Optimal Formula Inclusion (%)"), width="stretch")
    col2.plotly_chart(px.bar(res["df"][res["df"]["Total_Batch_Cost_USD"] > 0], x="Ingredient", y="Total_Batch_Cost_USD", title=f"Batch Ingredient Cost Breakdown ({batch_tons:.0f} Tons)"), width="stretch")

with tab3:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([
            {"Metric": "Formulation Timestamp (UTC)", "Value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")},
            {"Metric": "Ration Specification", "Value": ration_name},
            {"Metric": "Raw Ingredient Cost ($/Ton)", "Value": f"${res['raw_cost_per_ton']:,.2f}"},
            {"Metric": "Total Loaded Cost ($/Ton)", "Value": f"${res['total_cost_per_ton']:,.2f}"},
            {"Metric": "Cost per 50kg Bag ($)", "Value": f"${res['cost_per_50kg_bag']:,.2f}"},
            {"Metric": "Net Profit per Ton ($)", "Value": f"${res['net_margin_per_ton']:,.2f} ({res['gross_margin_pct']:.1f}%)"},
            {"Metric": f"Total Batch Profit ({batch_tons:.0f} Tons)", "Value": f"${res['total_batch_profit']:,.2f}"},
        ]).to_excel(writer, sheet_name="01_Batch_Economics", index=False)
        res["df"].to_excel(writer, sheet_name="02_Optimal_Mixing_Sheet", index=False)
        pd.DataFrame([res["achieved_nutrients"]]).to_excel(writer, sheet_name="03_Guaranteed_Analysis", index=False)

    st.download_button("📊 Download 3-Sheet FeedMillPro Batch Workbook (.xlsx)", buf.getvalue(), "FeedMillPro_USA_LeastCost_Batch_Suite.xlsx")
