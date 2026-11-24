"""
FeedMillPro USA — Linear Programming Least-Cost Ration Optimizer & Batch Economics Engine
Uses scipy.optimize.linprog to minimize ration cost per metric ton subject to nutritional constraints.
"""

import numpy as np
import pandas as pd
from scipy.optimize import linprog

DEFAULT_INGREDIENTS = [
    {"Ingredient": "Yellow Corn (Maize)", "Cost_Per_Ton_USD": 235.0, "Protein_Pct": 8.5, "Energy_Kcal_Kg": 3350.0, "Calcium_Pct": 0.02, "Phosphorus_Pct": 0.28, "Fiber_Pct": 2.2, "Min_Inclusion_Pct": 35.0, "Max_Inclusion_Pct": 68.0},
    {"Ingredient": "Soybean Meal (48% CP)", "Cost_Per_Ton_USD": 445.0, "Protein_Pct": 48.0, "Energy_Kcal_Kg": 2440.0, "Calcium_Pct": 0.27, "Phosphorus_Pct": 0.65, "Fiber_Pct": 3.5, "Min_Inclusion_Pct": 12.0, "Max_Inclusion_Pct": 38.0},
    {"Ingredient": "Wheat Middlings / Bran", "Cost_Per_Ton_USD": 185.0, "Protein_Pct": 15.5, "Energy_Kcal_Kg": 1950.0, "Calcium_Pct": 0.12, "Phosphorus_Pct": 0.95, "Fiber_Pct": 8.5, "Min_Inclusion_Pct": 0.0, "Max_Inclusion_Pct": 18.0},
    {"Ingredient": "Fishmeal (65% CP)", "Cost_Per_Ton_USD": 1380.0, "Protein_Pct": 65.0, "Energy_Kcal_Kg": 2950.0, "Calcium_Pct": 4.20, "Phosphorus_Pct": 2.60, "Fiber_Pct": 0.8, "Min_Inclusion_Pct": 0.0, "Max_Inclusion_Pct": 8.0},
    {"Ingredient": "Soybean Oil (Energy Booster)", "Cost_Per_Ton_USD": 980.0, "Protein_Pct": 0.0, "Energy_Kcal_Kg": 8800.0, "Calcium_Pct": 0.00, "Phosphorus_Pct": 0.00, "Fiber_Pct": 0.0, "Min_Inclusion_Pct": 0.0, "Max_Inclusion_Pct": 5.0},
    {"Ingredient": "Limestone (Calcium Carbonate)", "Cost_Per_Ton_USD": 65.0, "Protein_Pct": 0.0, "Energy_Kcal_Kg": 0.0, "Calcium_Pct": 38.00, "Phosphorus_Pct": 0.00, "Fiber_Pct": 0.0, "Min_Inclusion_Pct": 0.5, "Max_Inclusion_Pct": 9.5},
    {"Ingredient": "Dicalcium Phosphate (DCP)", "Cost_Per_Ton_USD": 540.0, "Protein_Pct": 0.0, "Energy_Kcal_Kg": 0.0, "Calcium_Pct": 22.00, "Phosphorus_Pct": 18.50, "Fiber_Pct": 0.0, "Min_Inclusion_Pct": 0.3, "Max_Inclusion_Pct": 3.0},
    {"Ingredient": "Vitamin-Mineral-Amino Premix", "Cost_Per_Ton_USD": 2450.0, "Protein_Pct": 12.0, "Energy_Kcal_Kg": 1200.0, "Calcium_Pct": 5.00, "Phosphorus_Pct": 1.00, "Fiber_Pct": 0.0, "Min_Inclusion_Pct": 0.5, "Max_Inclusion_Pct": 1.0},
]

RATION_SPECS = {
    "Broiler Starter (0-14 Days)": {"min_cp": 22.0, "min_me": 3000.0, "min_ca": 0.95, "min_p": 0.48, "max_fiber": 4.2},
    "Broiler Finisher (29-42 Days)": {"min_cp": 19.0, "min_me": 3150.0, "min_ca": 0.85, "min_p": 0.42, "max_fiber": 4.5},
    "Layer Peak Production (18+ Wks)": {"min_cp": 17.0, "min_me": 2780.0, "min_ca": 3.60, "min_p": 0.40, "max_fiber": 5.2},
}


def solve_least_cost_ration(ing_df: pd.DataFrame, specs: dict, batch_tons: float, overhead_per_ton: float, selling_price_per_ton: float) -> dict:
    df = ing_df.copy().reset_index(drop=True)
    n = len(df)
    c = df["Cost_Per_Ton_USD"].astype(float).values

    # Equality constraint: sum(weights) == 1.0 (100% of batch)
    A_eq = np.ones((1, n))
    b_eq = np.array([1.0])

    # Inequality constraints (A_ub * x <= b_ub)
    A_ub = np.vstack([
        -df["Protein_Pct"].astype(float).values,
        -df["Energy_Kcal_Kg"].astype(float).values,
        -df["Calcium_Pct"].astype(float).values,
        -df["Phosphorus_Pct"].astype(float).values,
        df["Fiber_Pct"].astype(float).values,
    ])
    b_ub = np.array([
        -float(specs["min_cp"]),
        -float(specs["min_me"]),
        -float(specs["min_ca"]),
        -float(specs["min_p"]),
        float(specs["max_fiber"]),
    ])

    bounds = [(float(r["Min_Inclusion_Pct"]) / 100.0, float(r["Max_Inclusion_Pct"]) / 100.0) for _, r in df.iterrows()]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if not res.success:
        raise ValueError(f"No feasible ration satisfies all nutritional constraints simultaneously ({res.message}). Relax min/max ingredient bounds or nutrient targets.")

    weights = res.x
    df["Optimal_Inclusion_Pct"] = np.round(weights * 100.0, 2)
    df["Batch_Kg"] = np.round(weights * batch_tons * 1000.0, 1)
    df["Cost_Contribution_Per_Ton_USD"] = np.round(weights * c, 2)
    df["Total_Batch_Cost_USD"] = np.round(df["Cost_Contribution_Per_Ton_USD"] * batch_tons, 2)

    raw_cost_ton = round(float(np.dot(weights, c)), 2)
    total_cost_ton = round(raw_cost_ton + overhead_per_ton, 2)
    net_margin_ton = round(selling_price_per_ton - total_cost_ton, 2)
    gross_margin_pct = round((net_margin_ton / max(selling_price_per_ton, 0.01)) * 100.0, 2)

    achieved = {
        "Crude_Protein_Pct": round(float(np.dot(weights, df["Protein_Pct"].astype(float))), 2),
        "Metabolizable_Energy_Kcal": round(float(np.dot(weights, df["Energy_Kcal_Kg"].astype(float))), 0),
        "Calcium_Pct": round(float(np.dot(weights, df["Calcium_Pct"].astype(float))), 2),
        "Phosphorus_Pct": round(float(np.dot(weights, df["Phosphorus_Pct"].astype(float))), 2),
        "Crude_Fiber_Pct": round(float(np.dot(weights, df["Fiber_Pct"].astype(float))), 2),
    }

    return {
        "df": df,
        "raw_cost_per_ton": raw_cost_ton,
        "total_cost_per_ton": total_cost_ton,
        "cost_per_50kg_bag": round(total_cost_ton / 20.0, 2),
        "net_margin_per_ton": net_margin_ton,
        "gross_margin_pct": gross_margin_pct,
        "total_batch_profit": round(net_margin_ton * batch_tons, 2),
        "achieved_nutrients": achieved,
    }
